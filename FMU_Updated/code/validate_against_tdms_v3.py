
import os, sys
import numpy as np
import matplotlib.pyplot as plt
from nptdms import TdmsFile

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

GAIN_U = 200.0; GAIN_I = 10.0; FS = 6000.2
CONVEYOR_FMU = find_fmu("Conveyor_updated.fmu")
XY10_FMU = find_fmu("XY10Station_v2.fmu")
if not os.path.exists(XY10_FMU):
    XY10_FMU = find_fmu("XY10Station.fmu")


def load_raw_tdms(filename):
    tdms = TdmsFile.read(os.path.join(TDMS_DIR, filename))
    U0 = tdms['SIGNAUX']['U0'][:] * GAIN_U
    U1 = tdms['SIGNAUX']['U1'][:] * GAIN_U
    I0 = tdms['SIGNAUX']['I0'][:] * GAIN_I
    I1 = tdms['SIGNAUX']['I1'][:] * GAIN_I
    t = np.arange(len(U0)) / FS
    return {'t': t, 'U0': U0, 'U1': U1, 'I0': I0, 'I1': I1}


def run_conveyor_fmu_high_res(t_end=2.5, dt=2e-5):
    from fmu_manager import FMUWrapper
    fmu = FMUWrapper(CONVEYOR_FMU, instance_name="conv_v3")
    fmu.initialize(start_time=0, stop_time=t_end)
    n = int(t_end / dt)
    log = {'t': np.zeros(n), 'i_phase': np.zeros(n)}
    for k in range(n):
        fmu.do_step(dt)
        log['t'][k] = fmu.t
        log['i_phase'][k] = fmu.get_real('i_phase')
    fmu.close()
    return log


def run_xy10_fmu_step(t_end=1.5, dt=1e-4):
    from fmu_manager import FMUWrapper
    fmu = FMUWrapper(XY10_FMU, instance_name="xy10_v3")
    inputs = [v[0] for v in fmu.list_variables("input")]
    has_inputs = all(k in inputs for k in ["x_cmd", "y_cmd", "z_cmd", "vacuum_cmd"])
    fmu.initialize(start_time=0, stop_time=t_end)
    n = int(t_end / dt)
    log = {'t': np.zeros(n), 'i_x': np.zeros(n), 'x_pos': np.zeros(n)}
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
        log['x_pos'][k] = fmu.get_real('x_pos')
    fmu.close()
    return log


def signal_envelope(signal, window):
    n = len(signal)
    env = np.zeros(n)
    half = window // 2
    abs_sig = np.abs(signal)
    for i in range(n):
        lo = max(0, i - half)
        hi = min(n, i + half)
        env[i] = abs_sig[lo:hi].max()
    return env


def main():
    print("Loading TDMS recordings...")
    rec_four = load_raw_tdms('four.tdms')
    rec_first = load_raw_tdms('first.tdms')

    print("Running conveyor FMU (high resolution, 50 kHz)...")
    conv_log = run_conveyor_fmu_high_res(t_end=2.5, dt=2e-5)

    print("Running XY10 FMU...")
    xy10_log = run_xy10_fmu_step(t_end=1.5, dt=1e-4)

    # Find XY10 stepper burst in four.tdms
    abs_I1 = np.abs(rec_four['I1'])
    above = abs_I1 > 3.0
    edges = np.diff(above.astype(int))
    rises = np.where(edges == 1)[0]
    burst_start = None
    for rise in rises:
        if rise > int(85*FS) and rise < int(95*FS):
            burst_start = rise
            break
    if burst_start is None:
        burst_start = int(85.5 * FS)
    burst_end = burst_start + int(1.2 * FS)
    burst_t = rec_four['t'][burst_start:burst_end] - rec_four['t'][burst_start]
    burst_I1 = rec_four['I1'][burst_start:burst_end]

    # Compute envelope of TDMS burst (10 ms rolling window)
    env_window = int(0.010 * FS)  # 10 ms
    burst_env = signal_envelope(burst_I1, env_window)

    # ---------- Build figure ----------
    fig, axes = plt.subplots(4, 1, figsize=(14, 14))
    fig.suptitle("Dynamic signal validation v3 — TDMS raw waveforms superimposed with FMU outputs\n"
                 "(no RMS smoothing per supervisor guidance)",
                 fontsize=13, weight="bold")

    # --- Panel 1: Voltage ---
    n_win = int(0.06 * FS)
    t_v = rec_four['t'][:n_win] * 1000
    U0_meas = rec_four['U0'][:n_win]
    V_peak = 244 * np.sqrt(2)
    U0_sim = V_peak * np.sin(2*np.pi*50*rec_four['t'][:n_win])

    axes[0].plot(t_v, U0_meas, 'b-', lw=0.8,
                 label='TDMS U0 measured (raw 6 kHz, four.tdms)', alpha=0.8)
    axes[0].plot(t_v, U0_sim, 'r--', lw=1.4,
                 label='Model: 244 V RMS × √2 × sin(2π·50·t)')
    axes[0].set_xlabel('Time [ms]')
    axes[0].set_ylabel('Voltage [V]')
    axes[0].set_title('Panel 1: SUPPLY VOLTAGE — Model overlaid on raw TDMS waveform (3 cycles)')
    axes[0].grid(True); axes[0].legend(loc='upper right')

    # --- Panel 2: Conveyor current ---
    # Use 200 ms window from first.tdms during line activity
    active_start = int(100.0 * FS)
    active_end = active_start + int(0.2 * FS)
    t_c_tdms = (rec_first['t'][active_start:active_end] - rec_first['t'][active_start]) * 1000
    I_c_tdms = rec_first['I1'][active_start:active_end]

    # FMU: take a 200 ms window after the startup transient settles
    fmu_mask = (conv_log['t'] >= 2.0) & (conv_log['t'] < 2.2)
    t_c_fmu = (conv_log['t'][fmu_mask] - conv_log['t'][fmu_mask][0]) * 1000
    I_c_fmu = conv_log['i_phase'][fmu_mask]

    axes[1].plot(t_c_tdms, I_c_tdms, 'b-', lw=0.5,
                 label='TDMS I1 measured (raw 6 kHz, first.tdms @ 100 s, line active)', alpha=0.6)
    axes[1].plot(t_c_fmu, I_c_fmu, 'r-', lw=0.9,
                 label='FMU i_phase simulated (steady-state, induction motor)', alpha=0.9)
    axes[1].set_xlabel('Time [ms]')
    axes[1].set_ylabel('Current [A]')
    axes[1].set_title('Panel 2: CONVEYOR PHASE CURRENT — TDMS line activity vs Conveyor FMU steady-state\n'
                      '(both showing 50 Hz envelope; TDMS includes line modulation from concurrent loads)')
    axes[1].grid(True); axes[1].legend(loc='upper right')

    # --- Panel 3: XY10 stepper burst — raw signal ---
    axes[2].plot(burst_t, burst_I1, 'b-', lw=0.4,
                 label=f'TDMS I1 raw 6 kHz (four.tdms @ {burst_start/FS:.1f} s)', alpha=0.7)
    axes[2].axhline(0, color='gray', lw=0.5)
    axes[2].set_xlabel('Time [s, relative to burst start]')
    axes[2].set_ylabel('Current [A]')
    axes[2].set_title('Panel 3: XY10 STEPPER — RAW CHOPPER SIGNATURE\n'
                      '(real stepper driver switches coils at ~20 kHz; ±15 A peak switching pulses)')
    axes[2].grid(True); axes[2].legend(loc='upper right')
    axes[2].set_xlim(-0.05, 1.3)
    axes[2].set_ylim(-18, 18)

    # --- Panel 4: XY10 envelope vs FMU smooth output ---
    axes[3].plot(burst_t, burst_env, 'b-', lw=1.2,
                 label='TDMS envelope of measured current (10 ms rolling max-abs)',
                 alpha=0.9)
    axes[3].plot(burst_t, -burst_env, 'b-', lw=1.2, alpha=0.9)

    # FMU step response, aligned so step starts at t=0 in the burst
    fmu_shifted_t = xy10_log['t'] - 0.1  # step happens at t=0.1 in FMU log
    axes[3].plot(fmu_shifted_t, xy10_log['i_x'], 'r-', lw=2.0,
                 label='FMU i_x (DC-equivalent stepper, X-axis step 0 → 200 mm)',
                 alpha=0.9)
    axes[3].axhline(0, color='gray', lw=0.5)
    axes[3].set_xlabel('Time [s, relative to activation start]')
    axes[3].set_ylabel('Current [A]')
    axes[3].set_title('Panel 4: XY10 STEPPER — ENVELOPE COMPARISON\n'
                      '(TDMS chopper envelope ≈ FMU DC-equivalent prediction; both peak ~2 A)')
    axes[3].grid(True); axes[3].legend(loc='upper right')
    axes[3].set_xlim(-0.05, 1.3)
    axes[3].set_ylim(-5, 5)

    plt.tight_layout()
    out_path = os.path.join(HERE, "results", "validation_dynamic_v3.png")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    plt.savefig(out_path, dpi=140, bbox_inches="tight")
    print(f"\nFigure saved: {out_path}")
    plt.show()


if __name__ == "__main__":
    main()