"""
measure_corrected.py
====================
Honest energy measurement with three corrections from diagnosis:
  1. Flip I0 sign (wiring polarity reversed on phase 0)
  2. Ignore I2 (channel dead — reads ~3 VA in every window)
  3. Scale (P0 + P1) by 3/2 to estimate balanced three-phase total
  4. Use the clean 150–250 s window for first.tdms (not the contaminated 5–30 s)
"""

import numpy as np
from nptdms import TdmsFile

GAIN_U = 200.0
GAIN_I = 10.0


def load_and_measure(path, window, label):
    tdms = TdmsFile.read(path)
    g = tdms.groups()[0]

    u0 = np.asarray(g["U0"][:]) * GAIN_U
    u1 = np.asarray(g["U1"][:]) * GAIN_U
    i0 = -np.asarray(g["I0"][:]) * GAIN_I    # POLARITY FLIPPED
    i1 = np.asarray(g["I1"][:]) * GAIN_I
    # I2 / U2 ignored — channel dead in this session

    try:
        dt = g["U0"].properties["wf_increment"]
    except KeyError:
        dt = 1.0 / 6000.2

    fs = 1.0 / dt
    n = min(len(u0), len(u1), len(i0), len(i1))
    t = np.arange(n) * dt

    mask = (t >= window[0]) & (t <= window[1])
    u0w, u1w = u0[mask], u1[mask]
    i0w, i1w = i0[mask], i1[mask]

    # Per-phase active power (mean of u·i over the window)
    P0 = np.mean(u0w * i0w)
    P1 = np.mean(u1w * i1w)

    # Per-phase apparent power
    S0 = np.sqrt(np.mean(u0w ** 2)) * np.sqrt(np.mean(i0w ** 2))
    S1 = np.sqrt(np.mean(u1w ** 2)) * np.sqrt(np.mean(i1w ** 2))

    # Two-phase totals
    P_two_phase = P0 + P1
    S_two_phase = S0 + S1

    # Scale to estimated three-phase total (3/2 factor assuming balanced load)
    P_three_phase_est = P_two_phase * 1.5
    S_three_phase_est = S_two_phase * 1.5

    PF = P_three_phase_est / S_three_phase_est if S_three_phase_est > 0 else 0.0
    duration = window[1] - window[0]
    energy_J = P_three_phase_est * duration

    print(f"\n{label}  [{window[0]:.0f}–{window[1]:.0f} s]")
    print(f"  Per-phase P:    P0={P0:+.1f} W   P1={P1:+.1f} W")
    print(f"  Per-phase S:    S0={S0:.1f} VA   S1={S1:.1f} VA")
    print(f"  Two-phase sum:  P={P_two_phase:.1f} W   S={S_two_phase:.1f} VA")
    print(f"  Three-phase estimate (×1.5):  "
          f"P={P_three_phase_est:.1f} W   S={S_three_phase_est:.1f} VA   PF={PF:.3f}")
    print(f"  Energy in window: {energy_J:.0f} J over {duration:.0f} s")

    return {
        "label": label,
        "P_W": P_three_phase_est,
        "S_VA": S_three_phase_est,
        "PF": PF,
        "energy_J": energy_J,
        "duration": duration,
    }


print("=" * 70)
print("CORRECTED MEASUREMENT  (I0 polarity flipped, I2 ignored, ×1.5 scaling)")
print("=" * 70)

# Conveyor — use the CLEAN window from the flat region
conveyor = load_and_measure(
    "first.tdms",
    (150.0, 250.0),
    "Conveyor steady state (clean window)"
)

# XY10 burst — already validated, just recompute with corrected sign
xy10 = load_and_measure(
    "four.tdms",
    (85.0, 100.0),
    "XY10 burst"
)

# Idle line — already validated, recompute with corrected sign
idle = load_and_measure(
    "four.tdms",
    (50.0, 60.0),
    "Idle line (sensors+PLC+controllers)"
)

# Conveyor motor alone = conveyor full − idle line
conveyor_motor_only_W = conveyor["P_W"] - idle["P_W"]

# XY10 isolated = XY10 burst − idle line
xy10_isolated_W = xy10["P_W"] - idle["P_W"]
xy10_isolated_energy = xy10_isolated_W * xy10["duration"]

print("\n" + "=" * 70)
print("FINAL SUBSYSTEM SUMMARY")
print("=" * 70)
print(f"\n  Idle line (sensors+PLC+controllers): {idle['P_W']:.1f} W")
print(f"     Energy / 30 s cycle:               {idle['P_W'] * 30:.0f} J")

print(f"\n  Conveyor full (motor + idle):         {conveyor['P_W']:.1f} W   PF={conveyor['PF']:.2f}")
print(f"  Conveyor motor alone (- idle):         {conveyor_motor_only_W:.1f} W")
print(f"     Energy / 30 s cycle:               {conveyor['P_W'] * 30:.0f} J")

print(f"\n  XY10 burst (full):                    {xy10['P_W']:.1f} W   PF={xy10['PF']:.2f}")
print(f"  XY10 isolated (- idle):                {xy10_isolated_W:.1f} W")
print(f"     Energy in 15 s burst:              {xy10_isolated_energy:.0f} J")

print("\n" + "=" * 70)
print("COMPARED TO MODEL PREDICTIONS")
print("=" * 70)
print(f"  Conveyor motor:  model 108 W   measured {conveyor_motor_only_W:.1f} W")
print(f"  XY10:            model ~0 W    measured {xy10_isolated_W:.1f} W")
print(f"  Idle line:       estimate 8 W  measured {idle['P_W']:.1f} W")