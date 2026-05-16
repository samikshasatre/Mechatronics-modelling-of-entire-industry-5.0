"""
test_xy10.py — Standalone validation of XY10Station.fmu (3-axis version).

Loads the updated XY10Station FMU (with X, Y, Z) and runs a 12-second
pick-place-traverse sequence driven from Python via FMI inputs:
   1.0 s : X moves to 200 mm
   4.0 s : Z drops to 50 mm
   5.0 s : vacuum ON (gripper attaches)
   6.0 s : Z back to 0 mm
   7.0 s : Y moves to 150 mm (NEW: exercises Y axis)
   9.0 s : Z drops again at place position
  10.0 s : return all to home, vacuum OFF

Expected:
   Peak i_x ≈ 1.85 A   (consistent with TDMS observed range)
   Peak i_y ≈ 1.85 A   (same motor as X)
   Peak i_z ≈ 1.03 A   (smaller motor)
   Vacuum reaches ~30 kPa, gripper attaches between t=5 and t=9
"""

import os, sys
import numpy as np
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from fmu_manager import FMUWrapper

def find_fmu(name):
    candidates = [
        os.path.join(HERE, name),
        os.path.join(HERE, "..", "FMUS", name),
        os.path.join(HERE, "FMUS", name),
    ]
    for p in candidates:
        if os.path.exists(p):
            return os.path.abspath(p)
    return os.path.join(HERE, name)

FMU_PATH = find_fmu("XY10Station_v2.fmu")
DT = 0.001
T_END = 12.0

REAL_OUTPUTS = ["x_pos", "x_v", "y_pos", "y_v", "z_pos", "z_v",
                "i_x", "i_y", "i_z", "P_elec", "vacuum_p"]
BOOL_OUTPUTS = ["gripper_attached"]

print(f"Loading FMU: {FMU_PATH}")
fmu = FMUWrapper(FMU_PATH, instance_name="xy10_test")
fmu.print_summary()
print()

# Detect FMU input mode (input-driven vs internally-scheduled)
inputs_list = [v[0] for v in fmu.list_variables("input")]
has_inputs = all(k in inputs_list for k in ["x_cmd", "y_cmd", "z_cmd", "vacuum_cmd"])
print(f"FMU has FMI inputs (x_cmd, y_cmd, z_cmd, vacuum_cmd): {has_inputs}")
print()

fmu.initialize(start_time=0.0, stop_time=T_END)
n_steps = int(T_END / DT)

log = {name: np.zeros(n_steps) for name in REAL_OUTPUTS}
log.update({name: np.zeros(n_steps, dtype=bool) for name in BOOL_OUTPUTS})
log["t"] = np.zeros(n_steps)
log["x_cmd"] = np.zeros(n_steps)
log["y_cmd"] = np.zeros(n_steps)
log["z_cmd"] = np.zeros(n_steps)
log["vacuum_cmd"] = np.zeros(n_steps, dtype=bool)

def schedule(t):
    """Returns (x_cmd, y_cmd, z_cmd, vacuum_cmd) at time t."""
    x_cmd = 0.20 if 1.0 <= t < 10.0 else 0.0
    y_cmd = 0.15 if 7.0 <= t < 10.0 else 0.0
    z_down = (4.0 <= t < 6.0) or (9.0 <= t < 10.0)
    z_cmd = 0.05 if z_down else 0.0
    vacuum_cmd = (5.0 <= t < 9.0)
    return x_cmd, y_cmd, z_cmd, vacuum_cmd

print(f"Running co-simulation: {n_steps} steps of {DT*1000:.1f} ms = {T_END} s total")
for k in range(n_steps):
    t_now = k * DT
    x_c, y_c, z_c, vac_c = schedule(t_now)
    if has_inputs:
        fmu.set_real("x_cmd", x_c)
        fmu.set_real("y_cmd", y_c)
        fmu.set_real("z_cmd", z_c)
        fmu.set_boolean("vacuum_cmd", vac_c)
    fmu.do_step(DT)
    log["t"][k] = fmu.t
    log["x_cmd"][k] = x_c
    log["y_cmd"][k] = y_c
    log["z_cmd"][k] = z_c
    log["vacuum_cmd"][k] = vac_c
    for name in REAL_OUTPUTS:
        log[name][k] = fmu.get_real(name)
    for name in BOOL_OUTPUTS:
        log[name][k] = fmu.get_boolean(name)

fmu.close()
print("Simulation finished.")

# ----- Metrics -----
mask_x = (log["t"] >= 0.95) & (log["t"] <= 4.0)
mask_y = (log["t"] >= 6.95) & (log["t"] <= 10.0)
mask_z = (log["t"] >= 3.95) & (log["t"] <= 6.5)
peak_ix = float(np.max(np.abs(log["i_x"][mask_x])))
peak_iy = float(np.max(np.abs(log["i_y"][mask_y])))
peak_iz = float(np.max(np.abs(log["i_z"][mask_z])))
peak_P  = float(log["P_elec"].max())
vac_min = float(log["vacuum_p"].min()) / 1000  # kPa
grip_ever = bool(log["gripper_attached"].any())

print()
print("=" * 60)
print("XY10 STATION (3-AXIS) — VALIDATION SUMMARY")
print("=" * 60)
print(f"X final position:    {log['x_pos'][-1]*1000:.1f} mm   (target: 0 mm at end)")
print(f"Y final position:    {log['y_pos'][-1]*1000:.1f} mm   (target: 0 mm at end)")
print(f"Z final position:    {log['z_pos'][-1]*1000:.1f} mm   (target: 0 mm at end)")
print(f"Peak i_x (X move):   {peak_ix:.2f} A  (expected ~1.85 A)")
print(f"Peak i_y (Y move):   {peak_iy:.2f} A  (expected ~1.85 A, same motor as X)")
print(f"Peak i_z (Z move):   {peak_iz:.2f} A  (expected ~1.03 A, smaller motor)")
print(f"Peak P_elec:         {peak_P:.1f} W")
print(f"Min vacuum_p:        {vac_min:.1f} kPa  (expected ~30 kPa)")
print(f"Gripper attached:    {grip_ever}")
print("=" * 60)

# ----- Plot -----
fig, axes = plt.subplots(5, 2, figsize=(14, 13))
fig.suptitle("XY10Station.fmu (3 axes) — Python co-simulation (12 s pick-place-traverse)",
             fontsize=14, weight="bold")

axes[0,0].plot(log["t"], log["x_pos"]*1000, "b-", label="x_pos")
axes[0,0].plot(log["t"], log["x_cmd"]*1000, "b--", alpha=0.5, label="x_cmd")
axes[0,0].set_ylabel("X [mm]"); axes[0,0].grid(True); axes[0,0].legend()

axes[0,1].plot(log["t"], log["y_pos"]*1000, "g-", label="y_pos")
axes[0,1].plot(log["t"], log["y_cmd"]*1000, "g--", alpha=0.5, label="y_cmd")
axes[0,1].set_ylabel("Y [mm]"); axes[0,1].grid(True); axes[0,1].legend()

axes[1,0].plot(log["t"], log["z_pos"]*1000, "r-", label="z_pos")
axes[1,0].plot(log["t"], log["z_cmd"]*1000, "r--", alpha=0.5, label="z_cmd")
axes[1,0].set_ylabel("Z [mm]"); axes[1,0].grid(True); axes[1,0].legend()

axes[1,1].plot(log["t"], log["vacuum_p"]/1000, "c-", label="vacuum_p")
axes[1,1].axhline(70, color="orange", ls="--", lw=0.7, label="threshold 70 kPa")
axes[1,1].axhline(101, color="gray", ls=":", lw=0.7, label="atm 101 kPa")
axes[1,1].set_ylabel("Vacuum [kPa]"); axes[1,1].grid(True); axes[1,1].legend(fontsize=8)

axes[2,0].plot(log["t"], log["i_x"], "b-")
axes[2,0].set_ylabel("i_x [A]"); axes[2,0].grid(True)

axes[2,1].plot(log["t"], log["i_y"], "g-")
axes[2,1].set_ylabel("i_y [A]"); axes[2,1].grid(True)

axes[3,0].plot(log["t"], log["i_z"], "r-")
axes[3,0].set_ylabel("i_z [A]"); axes[3,0].grid(True)

axes[3,1].plot(log["t"], log["P_elec"], "m-")
axes[3,1].set_ylabel("P_elec [W]"); axes[3,1].grid(True)

axes[4,0].plot(log["t"], log["x_v"], "b-", label="x_v")
axes[4,0].plot(log["t"], log["y_v"], "g-", label="y_v")
axes[4,0].plot(log["t"], log["z_v"], "r-", label="z_v")
axes[4,0].set_ylabel("Velocity [m/s]"); axes[4,0].set_xlabel("Time [s]")
axes[4,0].grid(True); axes[4,0].legend()

axes[4,1].step(log["t"], log["gripper_attached"].astype(int), "k-", where="post",
               label="gripper_attached")
axes[4,1].step(log["t"], log["vacuum_cmd"].astype(int), "c--", where="post", alpha=0.6,
               label="vacuum_cmd")
axes[4,1].set_ylabel("Boolean"); axes[4,1].set_xlabel("Time [s]")
axes[4,1].set_yticks([0,1]); axes[4,1].set_yticklabels(["false","true"])
axes[4,1].grid(True); axes[4,1].legend()

plt.tight_layout()
out_path = os.path.join(HERE, "results", "xy10_python.png")
os.makedirs(os.path.dirname(out_path), exist_ok=True)
plt.savefig(out_path, dpi=120, bbox_inches="tight")
print(f"Plot saved to: {out_path}")
plt.show()