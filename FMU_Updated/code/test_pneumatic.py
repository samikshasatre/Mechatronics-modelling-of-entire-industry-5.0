"""
test_pneumatic.py — Standalone validation of PneumaticStation.fmu in Python.

Loads the pneumatic cylinder FMU exported from 3DEXPERIENCE Behavior Modeling,
runs an 8-second test sequence (2 extend/retract cycles), and verifies that
the Python-driven results match the values observed in 3DEXPERIENCE.

Note: the current export of PneumaticStation.fmu may have either a free FMI
input (extend_cmd as BooleanInput) or an internally scheduled valve. Both
paths are handled below.

Expected results (4 bar supply, after p_supply = 400000 fix):
  - Peak chamber pressure ~400 kPa
  - Peak pneumatic force ~147 N
  - Piston reaches 50 mm during extend, returns to 0 mm during retract
  - Extension and retraction take ~500-800 ms each

Usage:
    python test_pneumatic.py
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

FMU_PATH = FMU_PATH = r"C:\Users\satres\Documents\ALIX\FMU_Updated\FMUS\Pneumatic_Station.fmu"
DT = 0.001
T_END = 8.0

REAL_SIGNALS = ["piston_pos", "piston_v", "chamber_p", "F_pneumatic"]
BOOL_SIGNALS = ["extended", "retracted"]

print(f"Loading FMU: {FMU_PATH}")
fmu = FMUWrapper(FMU_PATH, instance_name="pneumatic_test")
fmu.print_summary()
print()

# Determine if FMU has 'extend_cmd' as a top-level input
has_input = "extend_cmd" in [v[0] for v in fmu.list_variables("input")]
print(f"FMU has FMI extend_cmd input: {has_input}")
print()

fmu.initialize(start_time=0.0, stop_time=T_END)

n_steps = int(T_END / DT)
log = {name: np.zeros(n_steps) for name in REAL_SIGNALS}
log.update({name: np.zeros(n_steps, dtype=bool) for name in BOOL_SIGNALS})
log["t"] = np.zeros(n_steps)
log["extend_cmd"] = np.zeros(n_steps, dtype=bool)

print(f"Running co-simulation: {n_steps} steps of {DT*1000:.1f} ms = {T_END} s total")

# Test schedule (matches the dynamic test in 3DEXPERIENCE):
#   t < 0.5 s : retracted
#   0.5-2.5 s : EXTEND  (cycle 1)
#   2.5-4.5 s : retract
#   4.5-6.5 s : EXTEND  (cycle 2)
#   6.5-8.0 s : retract
def schedule(t):
    if t < 0.5: return False
    if t < 2.5: return True
    if t < 4.5: return False
    if t < 6.5: return True
    return False

for k in range(n_steps):
    t_now = k * DT
    cmd = schedule(t_now)
    if has_input:
        fmu.set_boolean("extend_cmd", cmd)
    fmu.do_step(DT)
    log["t"][k] = fmu.t
    log["extend_cmd"][k] = cmd
    for name in REAL_SIGNALS:
        log[name][k] = fmu.get_real(name)
    for name in BOOL_SIGNALS:
        log[name][k] = fmu.get_boolean(name)

fmu.close()
print("Simulation finished.")
print()

# Compute metrics
mask_ext1 = (log["t"] >= 0.5) & (log["t"] <= 2.5)
mask_ret1 = (log["t"] >= 2.5) & (log["t"] <= 4.5)
peak_p = log["chamber_p"].max() / 1000  # kPa
peak_F = log["F_pneumatic"].max()
piston_max = log["piston_pos"].max() * 1000  # mm
piston_min = log["piston_pos"][mask_ret1].min() * 1000  # mm at end of retract

# Extension time: from valve open (0.5s) to piston > 48 mm
ext_idx = np.where((log["t"] >= 0.5) & (log["piston_pos"] >= 0.048))[0]
t_ext = log["t"][ext_idx[0]] - 0.5 if len(ext_idx) > 0 else None

# Retraction time: from valve close (2.5s) to piston < 2 mm
ret_idx = np.where((log["t"] >= 2.5) & (log["piston_pos"] <= 0.002))[0]
t_ret = log["t"][ret_idx[0]] - 2.5 if len(ret_idx) > 0 else None

print("=" * 60)
print("PNEUMATIC STATION — VALIDATION SUMMARY")
print("=" * 60)
print(f"Peak chamber_p:    {peak_p:.1f} kPa   (expected ~400 kPa for 4 bar supply)")
print(f"Peak F_pneumatic:  {peak_F:.1f} N    (expected ~147 N at 4 bar)")
print(f"Piston max pos:    {piston_max:.1f} mm  (expected ~50 mm)")
print(f"Piston min pos:    {piston_min:.2f} mm  (expected ~0 mm)")
if t_ext: print(f"Extension time:    {t_ext*1000:.0f} ms")
if t_ret: print(f"Retraction time:   {t_ret*1000:.0f} ms")
print("=" * 60)

# Plot
fig, axes = plt.subplots(4, 1, figsize=(12, 10), sharex=True)
fig.suptitle("PneumaticStation.fmu — Python co-simulation (8 s, 4 bar supply)",
             fontsize=14, weight="bold")

axes[0].step(log["t"], log["extend_cmd"].astype(int), "k-", where="post")
axes[0].set_ylabel("extend_cmd")
axes[0].set_yticks([0, 1]); axes[0].set_yticklabels(["false", "true"])
axes[0].grid(True)

axes[1].plot(log["t"], log["piston_pos"]*1000, "b-")
axes[1].axhline(50, color="gray", ls="--", lw=0.7, label="Stroke max 50 mm")
axes[1].axhline(0, color="gray", ls=":", lw=0.7, label="Retracted 0 mm")
axes[1].set_ylabel("Piston position [mm]")
axes[1].grid(True); axes[1].legend()

axes[2].plot(log["t"], log["chamber_p"]/1000, "m-")
axes[2].axhline(400, color="gray", ls="--", lw=0.7, label="Supply 400 kPa")
axes[2].axhline(101, color="gray", ls=":", lw=0.7, label="Atmospheric 101 kPa")
axes[2].set_ylabel("Chamber pressure [kPa]")
axes[2].grid(True); axes[2].legend()

axes[3].plot(log["t"], log["F_pneumatic"], "g-")
axes[3].set_ylabel("F_pneumatic [N]")
axes[3].set_xlabel("Time [s]")
axes[3].grid(True)

plt.tight_layout()
out_path = os.path.join(HERE, "results", "pneumatic_python.png")
os.makedirs(os.path.dirname(out_path), exist_ok=True)
plt.savefig(out_path, dpi=120)
print(f"Plot saved to: {out_path}")
plt.show()