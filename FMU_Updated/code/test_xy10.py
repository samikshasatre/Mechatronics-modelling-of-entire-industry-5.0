"""
test_xy10.py — Standalone validation of XY10Station.fmu in Python.

Loads the XY10 FMU exported from 3DEXPERIENCE, runs a 10-second simulation,
and verifies that the dynamic test sequence (X step at t=1s, Z step at t=4s,
vacuum activation at t=5s) produces results consistent with TDMS data.

NOTE: this version of the FMU has the test schedule baked in as parameters
(t_x_step=1.0, t_z_step=4.0, t_vac_step=5.0, x_target=0.20, z_target=0.05).
There are no FMI inputs — the model self-runs. For the integration phase
(state-machine driven), a re-export with RealInput connectors is required.

Expected results (from 3DEXPERIENCE dynamic test):
  - x_pos at t=10 ≈ 0.20 m
  - z_pos at t=10 ≈ 0.05 m
  - Peak i_x at t≈1 s ≈ 1.85 A
  - Peak i_z at t≈4 s ≈ 1.09 A
  - Peak P_elec ≈ 87 W (during X move)
  - vacuum_p at t=10 ≈ 30000 Pa
  - gripper_attached at t=10 = True

Usage:
    python test_xy10.py
"""

import numpy as np
import matplotlib.pyplot as plt
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from fmu_manager import FMUWrapper

# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------

PROJECT_ROOT = os.path.dirname(HERE)
FMU_PATH = os.path.join(PROJECT_ROOT, "FMUS", "XY10Station.fmu")
DT = 0.001
T_END = 10.0

REAL_SIGNALS = ["x_pos", "x_v", "z_pos", "z_v",
                "i_x", "i_z", "P_elec", "vacuum_p"]
BOOL_SIGNALS = ["gripper_attached"]

# ---------------------------------------------------------------------------
# Load FMU
# ---------------------------------------------------------------------------

print(f"Loading FMU: {FMU_PATH}")
fmu = FMUWrapper(FMU_PATH, instance_name="xy10_test")
fmu.print_summary()
print()

# ---------------------------------------------------------------------------
# Run simulation
# ---------------------------------------------------------------------------

fmu.initialize(start_time=0.0, stop_time=T_END)

n_steps = int(T_END / DT)
log = {name: np.zeros(n_steps) for name in REAL_SIGNALS}
log.update({name: np.zeros(n_steps, dtype=bool) for name in BOOL_SIGNALS})
log["t"] = np.zeros(n_steps)

print(f"Running co-simulation: {n_steps} steps of {DT*1000:.1f} ms = {T_END} s total")
for k in range(n_steps):
    fmu.do_step(DT)
    log["t"][k] = fmu.t
    for name in REAL_SIGNALS:
        log[name][k] = fmu.get_real(name)
    for name in BOOL_SIGNALS:
        log[name][k] = fmu.get_boolean(name)

fmu.close()
print("Simulation finished.")
print()

# ---------------------------------------------------------------------------
# Compute metrics and check against 3DEXPERIENCE reference
# ---------------------------------------------------------------------------

# Final values
x_pos_final = log["x_pos"][-1]
z_pos_final = log["z_pos"][-1]
vac_final = log["vacuum_p"][-1]
grip_final = bool(log["gripper_attached"][-1])

# Peaks during movement intervals
mask_x_move = (log["t"] >= 0.95) & (log["t"] <= 3.0)
mask_z_move = (log["t"] >= 3.95) & (log["t"] <= 5.5)
peak_ix = np.max(np.abs(log["i_x"][mask_x_move]))
peak_iz = np.max(np.abs(log["i_z"][mask_z_move]))
peak_P_x = np.max(log["P_elec"][mask_x_move])
peak_P_z = np.max(log["P_elec"][mask_z_move])

print("=" * 70)
print(f"{'Metric':25s} {'Value':>15s} {'TDMS expected':>20s} {'OK?':>5s}")
print("=" * 70)

checks = [
    ("x_pos at t=10",          x_pos_final, 0.20, 0.005,  "m"),
    ("z_pos at t=10",          z_pos_final, 0.05, 0.005,  "m"),
    ("vacuum_p at t=10",       vac_final, 30000, 5000,    "Pa"),
    ("Peak i_x (X move)",      peak_ix,   1.85,  0.50,    "A"),
    ("Peak i_z (Z move)",      peak_iz,   1.09,  0.40,    "A"),
    ("Peak P_elec (X move)",   peak_P_x,  87.0,  20.0,    "W"),
    ("Peak P_elec (Z move)",   peak_P_z,  48.0,  20.0,    "W"),
]

all_ok = True
for label, value, ref, tol, unit in checks:
    ok = abs(value - ref) <= tol
    if not ok:
        all_ok = False
    status = "✓" if ok else "✗"
    print(f"{label:25s} {value:>13.4g} {unit:<3s} {ref:>15.4g} ±{tol:<6.2g} {status}")

print(f"{'gripper_attached':25s} {str(grip_final):>15s} {'True':>20s} "
      f"{'✓' if grip_final else '✗'}")

print("=" * 70)
if all_ok and grip_final:
    print("RESULT: ✅ Python-driven XY10 FMU reproduces 3DEXPERIENCE results.")
    print("        XY10 multiphysics model is TDMS-validated AND Python-callable.")
else:
    print("RESULT: ⚠️  Some metrics differ from reference.")
print()

# ---------------------------------------------------------------------------
# Plot
# ---------------------------------------------------------------------------

fig, axes = plt.subplots(4, 2, figsize=(14, 11), sharex=True)
fig.suptitle("XY10Station.fmu — Python co-simulation (10 s pick-and-place)",
             fontsize=14, weight="bold")

axes[0, 0].plot(log["t"], log["x_pos"] * 1000, "b-")
axes[0, 0].axhline(200, color="gray", ls="--", lw=0.7, label="Target 200 mm")
axes[0, 0].set_ylabel("X position [mm]"); axes[0, 0].grid(True); axes[0, 0].legend()

axes[0, 1].plot(log["t"], log["z_pos"] * 1000, "r-")
axes[0, 1].axhline(50, color="gray", ls="--", lw=0.7, label="Target 50 mm")
axes[0, 1].set_ylabel("Z position [mm]"); axes[0, 1].grid(True); axes[0, 1].legend()

axes[1, 0].plot(log["t"], log["i_x"], "b-")
axes[1, 0].axhline(1.85, color="orange", ls="--", lw=0.7, label="3DX peak 1.85 A")
axes[1, 0].set_ylabel("X current i_x [A]"); axes[1, 0].grid(True); axes[1, 0].legend()

axes[1, 1].plot(log["t"], log["i_z"], "r-")
axes[1, 1].axhline(1.09, color="orange", ls="--", lw=0.7, label="3DX peak 1.09 A")
axes[1, 1].set_ylabel("Z current i_z [A]"); axes[1, 1].grid(True); axes[1, 1].legend()

axes[2, 0].plot(log["t"], log["P_elec"], "m-")
axes[2, 0].set_ylabel("P_elec [W]"); axes[2, 0].grid(True)
axes[2, 0].text(0.02, 0.95, "TDMS range: 50-150 W during axis moves",
                transform=axes[2, 0].transAxes, fontsize=9, va="top",
                bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.5))

axes[2, 1].plot(log["t"], log["vacuum_p"] / 1000, "c-")
axes[2, 1].axhline(70, color="orange", ls="--", lw=0.7, label="Suction threshold 70 kPa")
axes[2, 1].axhline(101.325, color="gray", ls=":", lw=0.7, label="Atmospheric")
axes[2, 1].set_ylabel("Vacuum pressure [kPa]"); axes[2, 1].grid(True); axes[2, 1].legend()

axes[3, 0].plot(log["t"], log["x_v"], "b-", label="x_v")
axes[3, 0].plot(log["t"], log["z_v"], "r-", label="z_v")
axes[3, 0].set_ylabel("Velocity [m/s]"); axes[3, 0].set_xlabel("Time [s]")
axes[3, 0].grid(True); axes[3, 0].legend()

axes[3, 1].step(log["t"], log["gripper_attached"].astype(int), "k-", where="post")
axes[3, 1].set_ylabel("gripper_attached"); axes[3, 1].set_xlabel("Time [s]")
axes[3, 1].set_yticks([0, 1]); axes[3, 1].set_yticklabels(["false", "true"])
axes[3, 1].grid(True)

plt.tight_layout()
out_path = os.path.join(HERE, "results", "xy10_python.png")
os.makedirs(os.path.dirname(out_path), exist_ok=True)
plt.savefig(out_path, dpi=120)
print(f"Plot saved to: {out_path}")
plt.show()
