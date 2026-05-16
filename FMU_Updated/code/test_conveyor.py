"""
test_conveyor.py — Standalone validation of ConveyorMotor.fmu in Python.

Loads the FMU exported from 3DEXPERIENCE Behavior Modeling, runs a 5-second
no-load simulation, plots speed/torque/current/power, and verifies that the
Python-driven results match the values observed in 3DEXPERIENCE itself.

Expected results (matching 3DEXPERIENCE simulation at 5 N load):
  - w_motor settles at ~156.7 rad/s (≈ 1497 rpm)
  - tau_shaft settles at ~0.0065 N·m
  - i_phase settles at ~1.6 A
  - P_elec settles at ~108 W
  - v_belt settles at ~0.196 m/s
  - x_belt at t=5s ≈ 0.98 m

If this test passes, the entire 3DEXPERIENCE → FMU → Python toolchain is closed.

Usage:
    python test_conveyor.py
"""

import numpy as np
import matplotlib.pyplot as plt
import os, sys

# Make sure fmu_manager is importable from the same folder
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from fmu_manager import FMUWrapper

# ---------------------------------------------------------------------------
# Simulation settings
# ---------------------------------------------------------------------------

PROJECT_ROOT = os.path.dirname(HERE)
FMU_PATH = os.path.join(PROJECT_ROOT, "FMUS", "Conveyor_updated.fmu")
DT = 0.001          # macro time step (1 ms)
T_END = 5.0         # total simulation time (s)

# Output channels we want to log
SIGNALS = ["w_motor", "tau_shaft", "v_belt", "x_belt", "i_phase", "P_elec"]

# ---------------------------------------------------------------------------
# Load FMU and inspect
# ---------------------------------------------------------------------------

print(f"Loading FMU: {FMU_PATH}")
fmu = FMUWrapper(FMU_PATH, instance_name="conveyor_test")
fmu.print_summary()
print()

# ---------------------------------------------------------------------------
# Run simulation
# ---------------------------------------------------------------------------

fmu.initialize(start_time=0.0, stop_time=T_END)

n_steps = int(T_END / DT)
log = {name: np.zeros(n_steps) for name in SIGNALS}
log["t"] = np.zeros(n_steps)

print(f"Running co-simulation: {n_steps} steps of {DT*1000:.1f} ms = {T_END} s total")
for k in range(n_steps):
    fmu.do_step(DT)
    log["t"][k] = fmu.t
    for name in SIGNALS:
        log[name][k] = fmu.get_real(name)

fmu.close()
print("Simulation finished.")
print()

# ---------------------------------------------------------------------------
# Print final values and check against 3DEXPERIENCE reference
# ---------------------------------------------------------------------------

print("=" * 68)
print(f"{'Signal':12s} {'Final value':>15s} {'3DX expected':>15s} {'OK?':>6s}")
print("=" * 68)

# Reference values from the 3DEXPERIENCE simulation (Image 2 / Image 3)
expected = {
    "w_motor":   (156.7, 5.0,  "rad/s",  "≈ 1497 rpm"),
    "tau_shaft": (0.0065, 0.005, "N.m",  "very small (light load)"),
    "v_belt":    (0.196, 0.02, "m/s",    "drum_radius * w_drum"),
    "x_belt":    (0.98,  0.05, "m",      "≈ v_belt * 5 s"),
    "i_phase":   (1.63,  0.20, "A",      "magnetising current"),
    "P_elec":    (108.0, 15.0, "W",      "matches TDMS order of mag."),
}

all_ok = True
for name in SIGNALS:
    final = log[name][-1]
    if name in expected:
        ref, tol, unit, comment = expected[name]
        ok = abs(final - ref) <= tol or abs(final - ref) / max(abs(ref), 1e-9) <= 0.10
        status = "✓" if ok else "✗"
        if not ok:
            all_ok = False
        print(f"{name:12s} {final:>15.4f} {ref:>15.4f} {unit:>6s} {status}  ({comment})")
    else:
        print(f"{name:12s} {final:>15.4f}")

print("=" * 68)
print()
if all_ok:
    print("RESULT: ✅ Python-driven FMU reproduces 3DEXPERIENCE values.")
    print("        The 3DEXPERIENCE → FMU → Python toolchain is fully closed.")
else:
    print("RESULT: ⚠️  Some values differ from 3DEXPERIENCE reference.")
    print("        Check FMU export settings and parameter values.")
print()

# ---------------------------------------------------------------------------
# Plot
# ---------------------------------------------------------------------------

fig, axes = plt.subplots(3, 2, figsize=(14, 9), sharex=True)
fig.suptitle("ConveyorMotor.fmu — Python co-simulation (5 s, 5 N load)",
             fontsize=14, weight="bold")

axes[0, 0].plot(log["t"], log["w_motor"] * 60 / (2 * np.pi), "b-")
axes[0, 0].set_ylabel("Motor speed [rpm]")
axes[0, 0].axhline(1500, color="gray", ls="--", lw=0.7, label="Synchronous (1500)")
axes[0, 0].grid(True); axes[0, 0].legend(loc="lower right")

axes[0, 1].plot(log["t"], log["tau_shaft"], "r-")
axes[0, 1].set_ylabel("Shaft torque [N·m]")
axes[0, 1].grid(True)

axes[1, 0].plot(log["t"], log["i_phase"], "g-")
axes[1, 0].set_ylabel("Phase current [A]")
axes[1, 0].grid(True)

axes[1, 1].plot(log["t"], log["P_elec"], "m-")
axes[1, 1].set_ylabel("Electrical power [W]")
axes[1, 1].grid(True)

axes[2, 0].plot(log["t"], log["v_belt"], "c-")
axes[2, 0].set_ylabel("Belt velocity [m/s]")
axes[2, 0].set_xlabel("Time [s]")
axes[2, 0].grid(True)

axes[2, 1].plot(log["t"], log["x_belt"], "k-")
axes[2, 1].set_ylabel("Belt position [m]")
axes[2, 1].set_xlabel("Time [s]")
axes[2, 1].grid(True)

plt.tight_layout()
out_path = os.path.join(HERE, "results", "conveyor_python.png")
os.makedirs(os.path.dirname(out_path), exist_ok=True)
plt.savefig(out_path, dpi=120)
print(f"Plot saved to: {out_path}")
plt.show()
