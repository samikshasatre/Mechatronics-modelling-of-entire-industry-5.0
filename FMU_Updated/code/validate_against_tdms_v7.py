"""
validate_against_tdms_v7.py — Final dynamic validation (corrected v7.1).

Changes from v7:
  - Capture 200 ms TDMS window, then crop 30 ms each end after band-pass
  - This removes the filtfilt edge transient that made the TDMS fundamental
    artificially decay near the end of Panel 2b
  - All panels now show clean signals throughout their displayed window
"""

import os, sys
import numpy as np
import matplotlib.pyplot as plt
from nptdms import TdmsFile
from scipy.signal import butter, filtfilt

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)


def find_fmu(name):
    for p in [os.path.join(HERE, name),
              os.path.join(HERE, "..", "FMUS", name),
              os.path.join(HERE, "FMUS", name)]:
        if os.path.exists(p):
            return os.path.abspath(p)
    return os.path.join(HERE, name)


TDMS_DIR = None
for c in [os.path.join(HERE, "..", "tdms"),
          r"C:\Users\satres\Documents\ALIX\tdms"]:
    if os.path.isdir(c):
        TDMS_DIR = c; break

GAIN_U = 200.0
GAIN_I = 10.0
FS = 6000.2
CONVEYOR_FMU = find_fmu("Conveyor_updated_v2.fmu")
XY10_FMU = find_fmu("XY10Station_v2.fmu")
if not os.path.exists(XY10_FMU):
    XY10_FMU = find_fmu("XY10Station.fmu")


def load_raw_tdms(filename):
    tdms = TdmsFile.read(os.path.join(TDMS_DIR, filename))
    return {
        't':  np.arange(len(tdms['SIGNAUX']['U0'])) / FS,
        'U0': tdms['SIGNAUX']['U0'][:] * GAIN_U,
        'U1': tdms['SIGNAUX']['U1'][:] * GAIN_U,
        'I0': tdms['SIGNAUX']['I0'][:] * GAIN_I,
        'I1': tdms['SIGNAUX']['I1'][:] * GAIN_I,
    }


def envelope(signal, window_samples):
    n = len(signal)
    env = np.zeros(n)
    half = window_samples // 2
    abs_sig = np.abs(signal)
    for i in range(n):
        lo = max(0, i - half)
        hi = min(n, i + half)
        env[i] = abs_sig[lo:hi].max()
    return env


def bandpass_50hz(signal, fs, lowcut=40, highcut=60, order=4):
    nyq = fs / 2
    low = lowcut / nyq
    high = highcut / nyq
    b, a = butter(order, [low, high], btype='band')
    return filtfilt(b, a, signal)


def run_conveyor_fmu(t_end=2.5, dt=2e-5):
    from fmu_manager import FMUWrapper
    fmu = FMUWrapper(CONVEYOR_FMU, instance_name="conv_v7_1")
    fmu.initialize(start_time=0, stop_time=t_end)
    n = int(t_end / dt)
    log = {
        't': np.zeros(n),
        'i_phase': np.zeros(n),
        'i_phase_inst': np.zeros(n),
    }
    for k in range(n):
        fmu.do_step(dt)
        log['t'][k] = fmu.t
        log['i_phase'][k] = fmu.get_real('i_phase')
        log['i_phase_inst'][k] = fmu.get_real('i_phase_inst')
    fmu.close()
    return log


def run_xy10_fmu_step(t_end=1.0, dt=1e-4):
    from fmu_manager import FMUWrapper
    fmu = FMUWrapper(XY10_FMU, instance_name="xy10_v7_1")
    inputs = [v[0] for v in fmu.list_variables("input")]
    has_inputs = all(k in inputs for k in ["x_cmd", "y_cmd", "z_cmd", "vacuum_cmd"])
    fmu.initialize(start_time=0, stop_time=t_end)
    n = int(t_end / dt)
    log = {'t': np.zeros(n), 'i_x': np.zeros(n)}
    for k in range(n):
        t_now = k * dt
        if has_inputs:
            fmu.set_real("x_cmd", 0.20 if t_now >= 0.1 else 0.0)
            fmu.set_real("y_cmd", 0.0)
            fmu.set_real("z_cmd", 0.0)
            fmu.set_boolean("vacuum_cmd", False)
        fmu.do_step(dt)
        log['t'][k] = fmu.t
        log['i_x'][k] = fmu.get_real('i_x')
    fmu.close()
    return log


def align_phase(ref_signal, target_signal, max_shift_ms=20, fs=6000):
    max_shift = int(max_shift_ms * 1e-3 * fs)
    n = min(len(ref_signal), len(target_signal))
    ref_s = ref_signal[:n] - np.mean(ref_signal[:n])
    tgt_s = target_signal[:n] - np.mean(target_signal[:n])
    best_shift = 0
    best_corr = -np.inf
    for shift in range(-max_shift, max_shift + 1):
        if shift >= 0:
            corr = np.dot(ref_s[shift:], tgt_s[:n-shift])
        else:
            corr = np.dot(ref_s[:n+shift], tgt_s[-shift:])
        if corr > best_corr:
            best_corr = corr
            best_shift = shift
    return best_shift


def main():
    print("=" * 78)
    print("DYNAMIC VALIDATION v7.1 — Edge-cropped band-pass for clean Panel 2b")
    print("=" * 78)
    print()

    print("Loading TDMS recordings...")
    rec_four = load_raw_tdms('four.tdms')
    rec_first = load_raw_tdms('first.tdms')

    print("Running conveyor FMU at 50 kHz...")
    # Need 250 ms of FMU data (200 ms window + buffer for downsampling)
    conv_log = run_conveyor_fmu(t_end=2.5, dt=2e-5)
    print()

    print("Running XY10 FMU X-axis step...")
    xy10_log = run_xy10_fmu_step(t_end=1.0, dt=1e-4)

    print("Isolating XY10 stepper burst at t=145.1 s in four.tdms...")
    burst_center = 145.1
    n_burst_center = int(burst_center * FS)
    n_before = int(0.3 * FS)
    n_after = int(0.7 * FS)
    burst_I1 = rec_four['I1'][n_burst_center - n_before : n_burst_center + n_after]
    burst_t = np.arange(len(burst_I1)) / FS - 0.3
    burst_env = envelope(burst_I1, int(0.010 * FS))
    print()

    # ===============================================================
    # Build figure
    # ===============================================================
    print("Building figure (v7.1)...")
    fig = plt.figure(figsize=(14, 18))
    gs = fig.add_gridspec(5, 1, hspace=0.7, height_ratios=[2, 2, 2.5, 2, 2.5])
    fig.suptitle("Dynamic signal validation v7.1 — Final\n"
                 "Conveyor: FMU AC current overlaid with TDMS 50 Hz fundamental (edge-cropped)",
                 fontsize=13, weight="bold", y=0.995)

    # ----- Panel 1: Voltage -----
    ax1 = fig.add_subplot(gs[0])
    n_win = int(0.06 * FS)
    t_v = rec_four['t'][:n_win] * 1000
    U0_meas = rec_four['U0'][:n_win]
    V_peak = 244 * np.sqrt(2)
    U0_sim = V_peak * np.sin(2*np.pi*50*rec_four['t'][:n_win])
    ax1.plot(t_v, U0_meas, 'b-', lw=0.8,
             label='TDMS U0 measured (raw 6 kHz)', alpha=0.8)
    ax1.plot(t_v, U0_sim, 'r--', lw=1.4,
             label='Model: 244 V RMS × √2 × sin(2π · 50 · t)')
    ax1.set_xlabel('Time [ms]')
    ax1.set_ylabel('Voltage [V]')
    ax1.set_title('Panel 1: SUPPLY VOLTAGE — TDMS measurement overlaid with model sinusoid')
    ax1.grid(True); ax1.legend(loc='upper right')

    # ----- Panels 2a + 2b: Conveyor current -----
    # Capture 200 ms TDMS, then crop 30 ms each end after filtering
    s_idx = int(50.0 * FS)
    e_idx = s_idx + int(0.2 * FS)  # 200 ms full window
    I0_raw_full = rec_first['I0'][s_idx:e_idx]
    t_full = np.arange(len(I0_raw_full)) / FS * 1000  # ms

    # Band-pass filter then crop the edges (30 ms each side)
    I0_centered = I0_raw_full - np.mean(I0_raw_full)
    I0_fund_full = bandpass_50hz(I0_centered, FS)

    crop_samples = int(0.03 * FS)  # 30 ms each end
    t_crop = t_full[crop_samples:-crop_samples]
    t_crop = t_crop - t_crop[0]  # re-zero
    I0_raw_crop = I0_raw_full[crop_samples:-crop_samples]
    I0_fund_crop = I0_fund_full[crop_samples:-crop_samples]

    # FMU steady-state window matching the cropped TDMS length
    fmu_ss_start = int(2.0 / 2e-5)
    fmu_ss_n = int(0.2 / 2e-5)
    i_c_fmu_full = conv_log['i_phase_inst'][fmu_ss_start:fmu_ss_start+fmu_ss_n]
    fmu_rate = 1 / 2e-5
    decimate = int(fmu_rate / FS)
    i_c_fmu_ds = i_c_fmu_full[::decimate]
    # Crop FMU to match TDMS cropped length
    i_c_fmu_crop = i_c_fmu_ds[crop_samples:crop_samples + len(I0_fund_crop)]
    # Pad with zeros if necessary
    if len(i_c_fmu_crop) < len(I0_fund_crop):
        i_c_fmu_crop = np.concatenate([i_c_fmu_crop, np.zeros(len(I0_fund_crop) - len(i_c_fmu_crop))])

    # Phase alignment using cropped signals
    shift = align_phase(I0_fund_crop, i_c_fmu_crop, max_shift_ms=20, fs=FS)
    if shift >= 0:
        i_fmu_aligned = np.concatenate([np.zeros(shift), i_c_fmu_crop[:len(I0_fund_crop)-shift]])
    else:
        i_fmu_aligned = np.concatenate([i_c_fmu_crop[-shift:], np.zeros(-shift)])[:len(I0_fund_crop)]

    print(f"Panel 2: TDMS 50 Hz fundamental peak = {np.max(np.abs(I0_fund_crop)):.2f} A")
    print(f"Panel 2: FMU i_phase_inst peak       = {np.max(np.abs(i_fmu_aligned)):.2f} A")
    print(f"Panel 2: Phase alignment shift       = {shift/FS*1000:.2f} ms")

    # Panel 2a: Raw TDMS (now showing 140 ms cropped window)
    ax2a = fig.add_subplot(gs[1])
    ax2a.plot(t_crop, I0_raw_crop, 'b-', lw=0.7, alpha=0.7,
              label=f'TDMS I0 raw (first.tdms @ 50 s, peak-peak={np.ptp(I0_raw_crop):.2f} A)')
    ax2a.axhline(np.mean(I0_raw_crop), color='gray', ls='--', lw=0.5,
                 label=f'mean = {np.mean(I0_raw_crop):.2f} A (sensor DC offset)')
    ax2a.set_xlabel('Time [ms]')
    ax2a.set_ylabel('Current [A]')
    ax2a.set_title('Panel 2a: MEASURED LINE-SIDE CURRENT (raw) — controller rectifier harmonics visible\n'
                   '50 Hz fundamental + diode-bridge harmonics + PWM switching ripple')
    ax2a.grid(True); ax2a.legend(loc='upper right', fontsize=8)

    # Panel 2b: Filtered TDMS overlaid with FMU AC (edges cropped)
    ax2b = fig.add_subplot(gs[2])
    ax2b.plot(t_crop, I0_fund_crop, 'b-', lw=2.0,
              label=f'TDMS I0 — 50 Hz fundamental after band-pass (peak={np.max(np.abs(I0_fund_crop)):.2f} A)',
              alpha=0.85)
    ax2b.plot(t_crop, i_fmu_aligned, 'r-', lw=1.5,
              label=f'FMU i_phase_inst — modelled motor terminal current (peak={np.max(np.abs(i_fmu_aligned)):.2f} A)',
              alpha=0.85)
    ax2b.axhline(0, color='gray', lw=0.5)
    ax2b.set_xlabel('Time [ms]')
    ax2b.set_ylabel('Current [A]')
    ax2b.set_title('Panel 2b: 50 Hz FUNDAMENTAL — TDMS band-passed vs FMU simulated\n'
                   'Both real 50 Hz sinusoids overlaid, edge-cropped, phase-aligned via cross-correlation')
    ax2b.grid(True); ax2b.legend(loc='upper right', fontsize=8)

    annotation = (
        "Scope note: FMU models the motor as directly grid-connected (no rectifier/inverter).\n"
        "TDMS measures line-side current after the motor controller's diode bridge.\n"
        "The 50 Hz components agree (FMU 2.30 A vs TDMS 1.99 A peak); higher harmonics in the raw\n"
        "measurement (Panel 2a) reflect power electronics not in the current model scope."
    )
    ax2b.text(2, -2.0, annotation, fontsize=7, color='dimgray', style='italic',
              bbox=dict(facecolor='lightyellow', alpha=0.9,
                       edgecolor='gray', boxstyle='round,pad=0.4'),
              ha='left', va='top')

    # ----- Panel 3: Raw chopper signature -----
    ax3 = fig.add_subplot(gs[3])
    ax3.plot(burst_t, burst_I1, 'b-', lw=0.4,
             label=f'TDMS I1 raw 6 kHz (four.tdms @ t={burst_center} s)',
             alpha=0.7)
    ax3.axhline(0, color='gray', lw=0.5)
    ax3.set_xlabel('Time [s, aligned to burst start at t=0.1]')
    ax3.set_ylabel('Current [A]')
    ax3.set_title('Panel 3: XY10 STEPPER — RAW CHOPPER SIGNATURE (single isolated burst)')
    ax3.grid(True); ax3.legend(loc='upper right', fontsize=8)
    ax3.set_xlim(-0.05, 0.7)
    ax3.set_ylim(-22, 22)

    # ----- Panel 4: XY10 envelope vs FMU step -----
    ax4 = fig.add_subplot(gs[4])
    ax4_right = ax4.twinx()
    line_tdms_pos = ax4.plot(burst_t, burst_env, 'b-', lw=1.5,
                              label='TDMS envelope (10 ms rolling max-abs)',
                              alpha=0.9)
    ax4.plot(burst_t, -burst_env, 'b-', lw=1.5, alpha=0.9)
    ax4.set_ylabel('TDMS measured current [A]', color='b')
    ax4.tick_params(axis='y', labelcolor='b')
    ax4.set_ylim(-25, 25)
    ax4.set_xlabel('Time [s]')

    line_fmu = ax4_right.plot(xy10_log['t'], xy10_log['i_x'], 'r-', lw=2.0,
                               label='FMU i_x — DC-equivalent driving lead-screw',
                               alpha=0.9)
    ax4_right.set_ylabel('FMU simulated current [A]', color='r')
    ax4_right.tick_params(axis='y', labelcolor='r')
    ax4_right.set_ylim(-3, 3)

    lines = line_tdms_pos + line_fmu
    labels = [l.get_label() for l in lines]
    ax4.legend(lines, labels, loc='upper right', fontsize=8, framealpha=0.9)

    ax4.set_title(
        'Panel 4: XY10 STEPPER — TDMS ENVELOPE vs FMU STEP RESPONSE\n'
        'TDMS = chopper instantaneous peaks · FMU = time-averaged DC-equivalent'
    )
    ax4.grid(True, alpha=0.3)
    ax4.set_xlim(-0.05, 0.7)
    ax4.axhline(0, color='gray', lw=0.5)

    fig.subplots_adjust(top=0.96, bottom=0.04)
    out_path = os.path.join(HERE, "results", "validation_dynamic_v7.png")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    plt.savefig(out_path, dpi=140, bbox_inches="tight")
    print(f"\nFigure saved: {out_path}")
    print()
    print("=" * 78)
    print("v7.1 KEY DIFFERENCE: Panel 2b is now edge-cropped — no filter decay artifact")
    print("=" * 78)
    plt.show()


if __name__ == "__main__":
    main()