"""
measure_all_subsystems.py
==========================
Honest measurement audit of subsystem energy consumption from TDMS data.

Processes both first.tdms (conveyor steady state) and four.tdms (XY10 burst)
to produce measured energy values for every subsystem we can actually isolate.

Output: a single report + slide-ready plots showing what was measured,
what was estimated, and what remains unknown.
"""

import numpy as np
import matplotlib.pyplot as plt
from nptdms import TdmsFile
import os

# ============================================================
# CONFIGURATION — edit only this block
# ============================================================
FIRST_TDMS = "first.tdms"      # conveyor steady-state recording
FOUR_TDMS  = "four.tdms"       # XY10 burst recording

GAIN_U = 200.0
GAIN_I = 10.0

# Assumed power factor for VA → W conversion (industry-typical for drives)
PF_ASSUMED = 0.8

# Window choices (adjust after seeing the overview plots)
# These windows are filled in iteratively — first pass uses these defaults
FIRST_BASELINE_WINDOW = (5.0, 30.0)     # conveyor steady, no XY10/CR5 bursts (TBD)
FOUR_IDLE_WINDOW      = (50.0, 60.0)    # idle line, no XY10 burst (already validated)
FOUR_XY10_WINDOW      = (85.0, 100.0)   # XY10 burst (already validated)

# Cycle length used for normalising to "energy per 30 s cycle"
CYCLE_DURATION = 30.0


# ============================================================
# UTILITY FUNCTIONS
# ============================================================
def load_tdms(path):
    """Load TDMS file, return time + scaled voltages + currents."""
    tdms = TdmsFile.read(path)
    group = tdms.groups()[0]

    u0 = np.asarray(group["U0"][:]) * GAIN_U
    u1 = np.asarray(group["U1"][:]) * GAIN_U
    u2 = np.asarray(group["U2"][:]) * GAIN_U
    i0 = np.asarray(group["I0"][:]) * GAIN_I
    i1 = np.asarray(group["I1"][:]) * GAIN_I
    i2 = np.asarray(group["I2"][:]) * GAIN_I

    n = min(len(u0), len(u1), len(u2), len(i0), len(i1), len(i2))
    u0, u1, u2 = u0[:n], u1[:n], u2[:n]
    i0, i1, i2 = i0[:n], i1[:n], i2[:n]

    try:
        dt = group["U0"].properties["wf_increment"]
    except KeyError:
        dt = 1.0 / 6000.2
    t = np.arange(n) * dt
    fs = 1.0 / dt

    return t, u0, u1, u2, i0, i1, i2, fs


def apparent_power_envelope(u0, u1, u2, i0, i1, i2, fs):
    """RMS-based apparent power per phase, summed. Always positive."""
    cycle_samples = max(1, int(0.020 * fs))   # 20 ms = one 50 Hz cycle

    def rms(x, win):
        return np.sqrt(np.convolve(x ** 2, np.ones(win) / win, mode="same"))

    S0 = rms(u0, cycle_samples) * rms(i0, cycle_samples)
    S1 = rms(u1, cycle_samples) * rms(i1, cycle_samples)
    S2 = rms(u2, cycle_samples) * rms(i2, cycle_samples)
    return S0 + S1 + S2


def measure_window(t, S, t_start, t_end, label):
    """Compute mean apparent power and energy in a window."""
    mask = (t >= t_start) & (t <= t_end)
    n_samples = int(np.sum(mask))
    if n_samples == 0:
        return None
    S_mean = float(np.mean(S[mask]))
    duration = float(t_end - t_start)
    energy_VAs = S_mean * duration
    return {
        "label": label,
        "t_start": t_start,
        "t_end": t_end,
        "n_samples": n_samples,
        "S_mean_VA": S_mean,
        "P_mean_W": S_mean * PF_ASSUMED,
        "duration_s": duration,
        "energy_VAs": energy_VAs,
        "energy_J": energy_VAs * PF_ASSUMED,
    }


def print_window(result):
    print(f"\n  {result['label']}:")
    print(f"     Window:           {result['t_start']:.1f} – {result['t_end']:.1f} s")
    print(f"     Samples:          {result['n_samples']}")
    print(f"     Apparent power:   {result['S_mean_VA']:.1f} VA")
    print(f"     Active power:     {result['P_mean_W']:.1f} W   (PF = {PF_ASSUMED})")
    print(f"     Duration:         {result['duration_s']:.1f} s")
    print(f"     Energy:           {result['energy_J']:.1f} J")


# ============================================================
# STEP 1 — Process first.tdms (conveyor steady-state)
# ============================================================
print("=" * 70)
print("FIRST.TDMS — conveyor steady-state recording")
print("=" * 70)

if not os.path.exists(FIRST_TDMS):
    print(f"WARNING: {FIRST_TDMS} not found. Skipping conveyor measurement.")
    conveyor_total = None
else:
    t1, u01, u11, u21, i01, i11, i21, fs1 = load_tdms(FIRST_TDMS)
    print(f"  Loaded {len(t1)} samples = {t1[-1]:.1f} s at {fs1:.0f} Hz")
    S1 = apparent_power_envelope(u01, u11, u21, i01, i11, i21, fs1)
    print(f"  Mean apparent power over whole recording: {np.mean(S1):.1f} VA")
    print(f"  Peak apparent power:                       {np.max(S1):.1f} VA")

    # ---- Save overview plot ----
    fig, ax = plt.subplots(figsize=(12, 4))
    ax.plot(t1, S1, color="#2E75B6", lw=0.8, label="Apparent power (smoothed)")
    ax.axvspan(FIRST_BASELINE_WINDOW[0], FIRST_BASELINE_WINDOW[1],
               alpha=0.20, color="green", label="Conveyor measurement window")
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Apparent power (VA)")
    ax.set_title(f"first.tdms — conveyor recording   "
                 f"(measurement window {FIRST_BASELINE_WINDOW[0]:.0f}–{FIRST_BASELINE_WINDOW[1]:.0f} s)")
    ax.legend()
    ax.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig("conveyor_overview.png", dpi=150)
    plt.close()
    print(f"  Plot saved: conveyor_overview.png")

    # ---- Extract conveyor measurement ----
    conveyor_total = measure_window(
        t1, S1, *FIRST_BASELINE_WINDOW, "Conveyor (full line during steady state)"
    )
    print_window(conveyor_total)


# ============================================================
# STEP 2 — Process four.tdms (idle baseline + XY10 burst)
# ============================================================
print("\n" + "=" * 70)
print("FOUR.TDMS — XY10 burst recording")
print("=" * 70)

if not os.path.exists(FOUR_TDMS):
    print(f"WARNING: {FOUR_TDMS} not found. Skipping XY10 measurement.")
    idle_line = None
    xy10_total = None
else:
    t4, u04, u14, u24, i04, i14, i24, fs4 = load_tdms(FOUR_TDMS)
    print(f"  Loaded {len(t4)} samples = {t4[-1]:.1f} s at {fs4:.0f} Hz")
    S4 = apparent_power_envelope(u04, u14, u24, i04, i14, i24, fs4)
    print(f"  Mean apparent power: {np.mean(S4):.1f} VA")
    print(f"  Peak apparent power: {np.max(S4):.1f} VA")

    # ---- Save overview plot ----
    fig, ax = plt.subplots(figsize=(12, 4))
    ax.plot(t4, S4, color="#2E75B6", lw=0.8)
    ax.axvspan(FOUR_IDLE_WINDOW[0], FOUR_IDLE_WINDOW[1],
               alpha=0.20, color="green", label="Idle baseline")
    ax.axvspan(FOUR_XY10_WINDOW[0], FOUR_XY10_WINDOW[1],
               alpha=0.20, color="orange", label="XY10 burst")
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Apparent power (VA)")
    ax.set_title(f"four.tdms — XY10 burst recording")
    ax.legend()
    ax.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig("xy10_overview.png", dpi=150)
    plt.close()
    print(f"  Plot saved: xy10_overview.png")

    # ---- Extract idle-line measurement ----
    idle_line = measure_window(
        t4, S4, *FOUR_IDLE_WINDOW, "Idle line (sensors + PLC + controllers + idle drives)"
    )
    print_window(idle_line)

    # ---- Extract XY10 burst measurement ----
    xy10_burst = measure_window(
        t4, S4, *FOUR_XY10_WINDOW, "XY10 burst (idle baseline + XY10 activity)"
    )
    print_window(xy10_burst)

    # ---- Subtract idle line from XY10 burst to get pure XY10 ----
    if idle_line is not None:
        xy10_delta_VA = xy10_burst["S_mean_VA"] - idle_line["S_mean_VA"]
        xy10_total = {
            "label": "XY10 (idle-baseline subtracted)",
            "t_start": xy10_burst["t_start"],
            "t_end": xy10_burst["t_end"],
            "S_mean_VA": xy10_delta_VA,
            "P_mean_W": xy10_delta_VA * PF_ASSUMED,
            "duration_s": xy10_burst["duration_s"],
            "energy_VAs": xy10_delta_VA * xy10_burst["duration_s"],
            "energy_J": xy10_delta_VA * xy10_burst["duration_s"] * PF_ASSUMED,
        }
        print(f"\n  XY10 (ISOLATED, idle-baseline subtracted):")
        print(f"     Delta apparent power:  {xy10_delta_VA:.1f} VA")
        print(f"     Delta active power:    {xy10_total['P_mean_W']:.1f} W")
        print(f"     Energy in burst:       {xy10_total['energy_J']:.1f} J")
    else:
        xy10_total = None


# ============================================================
# STEP 3 — Final summary table
# ============================================================
print("\n" + "=" * 70)
print("FINAL MEASUREMENT SUMMARY")
print("=" * 70)
print(f"\nAll values use assumed PF = {PF_ASSUMED} for VA → W conversion.\n")

print(f"{'Subsystem':<40} {'Power (W)':>12} {'Energy / 30 s (J)':>20} {'Source':>12}")
print("-" * 90)

# Conveyor — measured
if conveyor_total is not None:
    P_conv = conveyor_total["P_mean_W"]
    E_conv_per_cycle = P_conv * CYCLE_DURATION
    print(f"{'Conveyor (full line, steady)':<40} {P_conv:>12.1f} {E_conv_per_cycle:>20.0f} {'measured':>12}")
else:
    print(f"{'Conveyor':<40} {'—':>12} {'—':>20} {'no data':>12}")

# Idle line — measured
if idle_line is not None:
    P_idle = idle_line["P_mean_W"]
    E_idle_per_cycle = P_idle * CYCLE_DURATION
    print(f"{'Idle line (sensors+PLC+controllers)':<40} {P_idle:>12.1f} {E_idle_per_cycle:>20.0f} {'measured':>12}")

# XY10 — measured
if xy10_total is not None:
    P_xy10_burst = xy10_total["P_mean_W"]
    E_xy10_burst = xy10_total["energy_J"]
    # Per-cycle: assume XY10 burst happens once per 30 s cycle
    E_xy10_per_cycle = E_xy10_burst   # one burst = one cycle's worth
    print(f"{'XY10 (during burst, isolated)':<40} {P_xy10_burst:>12.1f} {E_xy10_burst:>20.0f} {'measured':>12}")

# Pneumatic — not isolable
print(f"{'Pneumatic (compressor cycles)':<40} {'—':>12} {'—':>20} {'not isolated':>12}")
print(f"{'  (included inside idle line + bursts)':<40}")

print("-" * 90)

if (conveyor_total is not None and idle_line is not None and xy10_total is not None):
    total_per_cycle = E_conv_per_cycle + E_xy10_per_cycle
    # Note: idle line is already inside conveyor measurement if conveyor was running
    # So we don't double-count
    print(f"\nNotes:")
    print(f"  - 'Conveyor' includes everything drawing power when the conveyor runs:")
    print(f"     the motor itself + idle line + sensors + PLC + drives.")
    print(f"  - 'Idle line' = same line with conveyor OFF, gives the non-conveyor floor.")
    print(f"  - 'Conveyor motor alone' = conveyor measured - idle line = "
          f"{P_conv - P_idle:.1f} W active power.")
    print(f"  - XY10 burst is a one-off contribution per cycle.")
    print(f"  - Pneumatic compressor cycles are folded into the idle line and bursts —")
    print(f"     we cannot isolate them with the present three-phase instrumentation.")

print("\n" + "=" * 70)
print("Results saved.  Now compare these to your model predictions:")
print("    - Model conveyor:  108 W steady")
print("    - Model XY10:      ~0 W")
print("    - Model sensors+PLC: 8 W (was an estimate)")
print("    - Model pneumatic:  4 W (was an estimate)")
print("=" * 70)