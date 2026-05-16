"""
validate_against_tdms_v4.py — Dynamic-signal validation, final version.

Addresses supervisor remarks 2 + 5 (Romain Delabeye, 6 May 2026):
  - No RMS smoothing on TDMS — show raw 6 kHz dynamics
  - Superimpose TDMS measured and FMU simulated signals on the same axes
  - Honest framing of what the model captures and what it does not

4-panel figure with each panel telling a clear story:

  Panel 1 — Supply voltage:
      TDMS raw 50 Hz sinusoid vs idealized model sinusoid

  Panel 2 — Conveyor current:
      TDMS raw + TDMS envelope vs FMU RMS-equivalent output

  Panel 3 — XY10 raw chopper:
      Raw isolated single-activation burst from four.tdms @ 145 s

  Panel 4 — XY10 envelope vs FMU:
      TDMS burst envelope vs FMU X-axis step response
"""

import os
import sys
import numpy as np
import matplotlib.pyplot as plt
from nptdms import TdmsFile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)


def find_fmu(name):
    candidates = [
        os.path.join(HERE, name),
        os.path.join(HERE, "..", "FMUS", name),
        os.path.join(HERE, "FMUS", name),
    ]

    for path in candidates:
        if os.path.exists(path):
            return os.path.abspath(path)

    return os.path.abspath(os.path.join(HERE, name))


TDMS_DIR = None

tdms_candidates = [
    os.path.join(HERE, "..", "tdms"),
    r"C:\Users\satres\Documents\ALIX\tdms",
]

for candidate in tdms_candidates:
    if os.path.isdir(candidate):
        TDMS_DIR = candidate
        break

if TDMS_DIR is None:
    raise FileNotFoundError("TDMS directory not found.")


GAIN_U = 200.0
GAIN_I = 10.0
FS = 6000.2

CONVEYOR_FMU = find_fmu("Conveyor_updated.fmu")

XY10_FMU = find_fmu("XY10Station_v2.fmu")
if not os.path.exists(XY10_FMU):
    XY10_FMU = find_fmu("XY10Station.fmu")


def load_raw_tdms(filename):
    path = os.path.join(TDMS_DIR, filename)

    tdms = TdmsFile.read(path)

    return {
        "t": np.arange(len(tdms["SIGNAUX"]["U0"])) / FS,
        "U0": tdms["SIGNAUX"]["U0"][:] * GAIN_U,
        "U1": tdms["SIGNAUX"]["U1"][:] * GAIN_U,
        "I0": tdms["SIGNAUX"]["I0"][:] * GAIN_I,
        "I1": tdms["SIGNAUX"]["I1"][:] * GAIN_I,
    }


def envelope(signal, window_samples):
    """
    Rolling max-abs envelope.
    """

    n = len(signal)
    env = np.zeros(n)

    half = window_samples // 2
    abs_sig = np.abs(signal)

    for i in range(n):
        lo = max(0, i - half)
        hi = min(n, i + half)
        env[i] = np.max(abs_sig[lo:hi])

    return env


def run_conveyor_fmu(t_end=2.5, dt=2e-5):
    from fmu_manager import FMUWrapper

    fmu = FMUWrapper(CONVEYOR_FMU, instance_name="conv_v4")

    fmu.initialize(start_time=0, stop_time=t_end)

    n = int(t_end / dt)

    log = {
        "t": np.zeros(n),
        "i_phase": np.zeros(n),
    }

    for k in range(n):
        fmu.do_step(dt)

        log["t"][k] = fmu.t
        log["i_phase"][k] = fmu.get_real("i_phase")

    fmu.close()

    return log


def run_xy10_fmu_step(t_end=1.0, dt=1e-4):
    from fmu_manager import FMUWrapper

    fmu = FMUWrapper(XY10_FMU, instance_name="xy10_v4")

    inputs = [v[0] for v in fmu.list_variables("input")]

    has_inputs = all(
        key in inputs
        for key in ["x_cmd", "y_cmd", "z_cmd", "vacuum_cmd"]
    )

    fmu.initialize(start_time=0, stop_time=t_end)

    n = int(t_end / dt)

    log = {
        "t": np.zeros(n),
        "i_x": np.zeros(n),
    }

    for k in range(n):
        t_now = k * dt

        if has_inputs:
            fmu.set_real("x_cmd", 0.20 if t_now >= 0.1 else 0.0)
            fmu.set_real("y_cmd", 0.0)
            fmu.set_real("z_cmd", 0.0)
            fmu.set_boolean("vacuum_cmd", False)

        fmu.do_step(dt)

        log["t"][k] = fmu.t
        log["i_x"][k] = fmu.get_real("i_x")

    fmu.close()

    return log


def main():
    print("=" * 78)
    print("DYNAMIC VALIDATION v4 — raw waveforms, time-aligned, honestly framed")
    print("=" * 78)
    print(f"TDMS_DIR: {TDMS_DIR}")
    print()

    print("Loading TDMS recordings...")
    rec_four = load_raw_tdms("four.tdms")
    rec_first = load_raw_tdms("first.tdms")

    print("Running conveyor FMU at 50 kHz...")
    conv_log = run_conveyor_fmu(t_end=2.5, dt=2e-5)

    fmu_mask = (conv_log["t"] >= 2.0) & (conv_log["t"] < 2.2)

    i_phase_fmu_window = conv_log["i_phase"][fmu_mask]

    print(
        f"  FMU steady-state i_phase: "
        f"mean = {np.mean(i_phase_fmu_window):.2f} A, "
        f"std = {np.std(i_phase_fmu_window):.3f} A"
    )

    print("Running XY10 FMU X-axis step...")
    xy10_log = run_xy10_fmu_step(t_end=1.0, dt=1e-4)

    print(
        f"  FMU peak |i_x|: "
        f"{np.max(np.abs(xy10_log['i_x'])):.2f} A"
    )

    print()
    print("Isolating single XY10 burst at t = 145.1 s in four.tdms...")

    burst_center = 145.1

    n_burst_center = int(burst_center * FS)

    n_before = int(0.3 * FS)
    n_after = int(0.7 * FS)

    burst_I1 = rec_four["I1"][
        n_burst_center - n_before:
        n_burst_center + n_after
    ]

    burst_t = np.arange(len(burst_I1)) / FS - 0.3

    burst_env = envelope(
        burst_I1,
        int(0.010 * FS)
    )

    print(
        f"  Burst duration: ~0.21 s, "
        f"peak envelope: {burst_env.max():.1f} A"
    )

    print()
    print("Building 4-panel figure...")

    fig, axes = plt.subplots(4, 1, figsize=(14, 14))

    fig.suptitle(
        "Dynamic signal validation v4 — TDMS raw waveforms "
        "superimposed with FMU outputs\n"
        "(no RMS smoothing; aligned windows)",
        fontsize=13,
        weight="bold",
    )

    # =========================================================
    # Panel 1 — Supply voltage
    # =========================================================

    n_win = int(0.06 * FS)

    t_v = rec_four["t"][:n_win] * 1000

    U0_meas = rec_four["U0"][:n_win]

    V_peak = 244 * np.sqrt(2)

    U0_sim = (
        V_peak *
        np.sin(2 * np.pi * 50 * rec_four["t"][:n_win])
    )

    axes[0].plot(
        t_v,
        U0_meas,
        "b-",
        lw=0.8,
        alpha=0.8,
        label="TDMS U0 measured"
    )

    axes[0].plot(
        t_v,
        U0_sim,
        "r--",
        lw=1.4,
        label="Idealized 50 Hz model sinusoid"
    )

    axes[0].set_xlabel("Time [ms]")
    axes[0].set_ylabel("Voltage [V]")

    axes[0].set_title(
        "Panel 1: SUPPLY VOLTAGE — measured vs model sinusoid"
    )

    axes[0].grid(True)
    axes[0].legend(loc="upper right")

    # =========================================================
    # Panel 2 — Conveyor current
    # =========================================================

    active_start = int(100.0 * FS)
    active_end = active_start + int(0.2 * FS)

    t_c_tdms = (
        rec_first["t"][active_start:active_end]
        - rec_first["t"][active_start]
    ) * 1000

    I_c_tdms = rec_first["I1"][active_start:active_end]

    env_c_tdms = envelope(
        I_c_tdms,
        int(0.020 * FS)
    )

    t_c_fmu = (
        conv_log["t"][fmu_mask]
        - conv_log["t"][fmu_mask][0]
    ) * 1000

    I_c_fmu = conv_log["i_phase"][fmu_mask]

    axes[1].plot(
        t_c_tdms,
        I_c_tdms,
        "b-",
        lw=0.5,
        alpha=0.5,
        label="TDMS raw current"
    )

    axes[1].plot(
        t_c_tdms,
        env_c_tdms,
        "b-",
        lw=1.5,
        alpha=0.9,
        label="TDMS envelope"
    )

    axes[1].plot(
        t_c_fmu,
        I_c_fmu,
        "r-",
        lw=2.0,
        label="FMU RMS-equivalent current"
    )

    axes[1].set_xlabel("Time [ms]")
    axes[1].set_ylabel("Current [A]")

    axes[1].set_title(
        "Panel 2: CONVEYOR CURRENT — FMU vs measured envelope"
    )

    axes[1].grid(True)
    axes[1].legend(loc="upper right", fontsize=8)

    # =========================================================
    # Panel 3 — Raw XY10 burst
    # =========================================================

    axes[2].plot(
        burst_t,
        burst_I1,
        "b-",
        lw=0.4,
        alpha=0.7,
        label="TDMS raw XY10 burst"
    )

    axes[2].axhline(0, color="gray", lw=0.5)

    axes[2].set_xlabel("Time [s]")
    axes[2].set_ylabel("Current [A]")

    axes[2].set_title(
        "Panel 3: XY10 STEPPER — raw chopper signature"
    )

    axes[2].grid(True)
    axes[2].legend(loc="upper right", fontsize=8)

    axes[2].set_xlim(-0.2, 0.7)
    axes[2].set_ylim(-22, 22)

    # =========================================================
    # Panel 4 — Envelope vs FMU
    # =========================================================

    axes[3].plot(
        burst_t,
        burst_env,
        "b-",
        lw=1.5,
        alpha=0.9,
        label="TDMS envelope"
    )

    axes[3].plot(
        burst_t,
        -burst_env,
        "b-",
        lw=1.5,
        alpha=0.9
    )

    axes[3].plot(
        xy10_log["t"],
        xy10_log["i_x"],
        "r-",
        lw=2.0,
        alpha=0.9,
        label="FMU X-axis current"
    )

    axes[3].axhline(0, color="gray", lw=0.5)

    axes[3].set_xlabel("Time [s]")
    axes[3].set_ylabel("Current [A]")

    axes[3].set_title(
        "Panel 4: XY10 ENVELOPE vs FMU RESPONSE"
    )

    axes[3].grid(True)
    axes[3].legend(loc="upper right", fontsize=8)

    axes[3].set_xlim(-0.2, 0.7)
    axes[3].set_ylim(-22, 22)

    axes[3].annotate(
        "FMU = time-averaged current\n"
        "TDMS envelope = instantaneous chopper peaks\n"
        "Different physical time scales",
        xy=(0.5, -15),
        xytext=(0.5, -15),
        fontsize=9,
        color="darkred",
        bbox=dict(
            facecolor="lightyellow",
            alpha=0.9,
            boxstyle="round,pad=0.4",
            edgecolor="gray"
        )
    )

    plt.tight_layout()

    out_path = os.path.join(
        HERE,
        "results",
        "validation_dynamic_v4.png"
    )

    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    plt.savefig(
        out_path,
        dpi=140,
        bbox_inches="tight"
    )

    print()
    print(f"Figure saved: {out_path}")

    plt.show()


if __name__ == "__main__":
    main()