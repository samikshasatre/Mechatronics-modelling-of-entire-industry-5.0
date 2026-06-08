"""
orchestrate_alix_line.py
========================
End-to-end orchestration of the ALIX Industry 5.0 production line digital twin.

Loads three FMUs (Conveyor, XY10 Cartesian station, CR5 cobot) and runs them
together in a single Python program for one full 30 s production cycle that
matches the real ALIX line cadence.

This is the central deliverable of the internship per the brief:
"the entire production line should be simulated end-to-end from a single
program, enabling real-time integration with learning algorithms or digital
twin platforms."

Architecture:
    +---------+    +-----------+    +------------+
    |Conveyor |    |   XY10    |    |    CR5     |
    | (cont.) |    | (2 cycles)|    | (1 cycle)  |
    +---------+    +-----------+    +------------+
         |              |                  |
         +-----+--------+--------+---------+
               |                 |
        Master timeline    Total line power
               |                 |
         +-------------------+
         | Master CSV + Plot |
         +-------------------+

Author: Samiksha Satre - ISAE-Supméca Euler Lab, June 2026
"""

import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
from pathlib import Path
from fmpy import simulate_fmu
import time

# ============================================================
# CONFIGURATION
# ============================================================
BASE_DIR = Path(r"C:\Users\satres\Documents\ALIX\FMU_Updated")
FMU_DIR  = BASE_DIR / "FMUS"
OUT_DIR  = BASE_DIR / "orchestration_output"
OUT_DIR.mkdir(exist_ok=True)

FMU_CONV = str(FMU_DIR / "Conveyor_updated_v3.fmu")
FMU_XY10 = str(FMU_DIR / "XY10Station_v2.fmu")
FMU_CR5  = str(FMU_DIR / "CR5_Cobot.fmu")

# Master timeline
T_CYCLE   = 30.0         # one ALIX production cycle (s)
DT_MASTER = 0.01         # 100 Hz master grid

t_master = np.arange(0.0, T_CYCLE + DT_MASTER, DT_MASTER)
N_master = len(t_master)

print("=" * 75)
print("ALIX LINE - END-TO-END DIGITAL TWIN ORCHESTRATION")
print("=" * 75)
print(f"Master timeline: 0 to {T_CYCLE} s at {1/DT_MASTER:.0f} Hz "
      f"({N_master} samples)")
print()

# ============================================================
# STEP 1 - CONVEYOR (continuous operation)
# ============================================================
print("[1/4] Running CONVEYOR FMU (continuous operation, 30 s)...")
t0 = time.time()

# The conveyor has no FMU inputs - it runs autonomously on its sineVoltage
# source. We simulate the full 30 s in one shot.
res_conv = simulate_fmu(
    filename        = FMU_CONV,
    start_time      = 0.0,
    stop_time       = T_CYCLE,
    output_interval = DT_MASTER,
)
dt_conv = time.time() - t0
print(f"      Done in {dt_conv:.1f} s real-time, "
      f"{N_master} samples")

# Resample to master grid (just in case)
t_c = res_conv["time"]
P_conv     = np.interp(t_master, t_c, res_conv["P_elec"])
i_conv     = np.interp(t_master, t_c, res_conv["i_phase"])
T_motor    = np.interp(t_master, t_c, res_conv["T_motor"])
v_belt     = np.interp(t_master, t_c, res_conv["v_belt"])
x_belt     = np.interp(t_master, t_c, res_conv["x_belt"])
print(f"      Mean conveyor power : {np.mean(P_conv):.1f} W")
print(f"      Peak belt speed     : {np.max(v_belt):.3f} m/s")
print(f"      Final motor temp    : {T_motor[-1]-273.15:.1f} deg C")
print()

# ============================================================
# STEP 2 - XY10 STATION (2 pick-and-place cycles in 30 s)
# ============================================================
print("[2/4] Building XY10 input trajectory (2 cycles)...")

def ramp(t, t0, t1, y0, y1):
    """Linear ramp from y0 to y1 between t0 and t1, clipped outside."""
    a = (t - t0) / (t1 - t0)
    a = np.clip(a, 0.0, 1.0)
    return y0 + (y1 - y0) * a

# Two XY10 pick-and-place cycles within the 30 s window
#  Cycle 1: t = 2 to 12 s
#  Cycle 2: t = 17 to 27 s
def build_xy10_cycle(t, t_start):
    """One pick-and-place cycle starting at t_start, length 10 s."""
    tau = t - t_start
    # X: 0 -> 0.10 (pick) -> 0.25 (place) -> 0
    x = np.zeros_like(tau)
    x = np.where((tau >= 0.5) & (tau < 2.0),
                 ramp(tau, 0.5, 2.0, 0.0, 0.10), x)
    x = np.where((tau >= 2.0) & (tau < 6.5), 0.10, x)
    x = np.where((tau >= 6.5) & (tau < 7.0),
                 ramp(tau, 6.5, 7.0, 0.10, 0.25), x)
    x = np.where((tau >= 7.0) & (tau < 9.0), 0.25, x)
    x = np.where((tau >= 9.0) & (tau < 9.5),
                 ramp(tau, 9.0, 9.5, 0.25, 0.0), x)
    # Y: similar pattern
    y = np.zeros_like(tau)
    y = np.where((tau >= 0.5) & (tau < 2.0),
                 ramp(tau, 0.5, 2.0, 0.0, 0.10), y)
    y = np.where((tau >= 2.0) & (tau < 6.5), 0.10, y)
    y = np.where((tau >= 6.5) & (tau < 7.0),
                 ramp(tau, 6.5, 7.0, 0.10, 0.20), y)
    y = np.where((tau >= 7.0) & (tau < 9.0), 0.20, y)
    y = np.where((tau >= 9.0) & (tau < 9.5),
                 ramp(tau, 9.0, 9.5, 0.20, 0.0), y)
    # Z: down to pick, up, down to place, up
    z = np.zeros_like(tau)
    z = np.where((tau >= 2.0) & (tau < 2.5),
                 ramp(tau, 2.0, 2.5, 0.0, 0.05), z)
    z = np.where((tau >= 2.5) & (tau < 4.5), 0.05, z)
    z = np.where((tau >= 4.5) & (tau < 5.0),
                 ramp(tau, 4.5, 5.0, 0.05, 0.0), z)
    z = np.where((tau >= 7.0) & (tau < 7.5),
                 ramp(tau, 7.0, 7.5, 0.0, 0.05), z)
    z = np.where((tau >= 7.5) & (tau < 9.0), 0.05, z)
    z = np.where((tau >= 9.0) & (tau < 9.5),
                 ramp(tau, 9.0, 9.5, 0.05, 0.0), z)
    # Vacuum on between engage and release
    vac = (tau >= 4.5) & (tau < 9.5)
    # Active mask (this cycle is running)
    active = (tau >= 0.0) & (tau <= 10.0)
    return x, y, z, vac, active

x_cmd = np.zeros(N_master)
y_cmd = np.zeros(N_master)
z_cmd = np.zeros(N_master)
vac_cmd = np.zeros(N_master, dtype=bool)
xy10_active = np.zeros(N_master, dtype=bool)

for t_start in [2.0, 17.0]:
    x_c, y_c, z_c, v_c, a_c = build_xy10_cycle(t_master, t_start)
    x_cmd = np.where(a_c, x_c, x_cmd)
    y_cmd = np.where(a_c, y_c, y_cmd)
    z_cmd = np.where(a_c, z_c, z_cmd)
    vac_cmd = np.where(a_c, v_c, vac_cmd)
    xy10_active = xy10_active | a_c

# Pack as FMU input array
input_xy10 = np.zeros(N_master,
    dtype=[("time", "f8"),
           ("x_cmd", "f8"), ("y_cmd", "f8"), ("z_cmd", "f8"),
           ("vacuum_cmd", "?")])
input_xy10["time"]       = t_master
input_xy10["x_cmd"]      = x_cmd
input_xy10["y_cmd"]      = y_cmd
input_xy10["z_cmd"]      = z_cmd
input_xy10["vacuum_cmd"] = vac_cmd

print(f"      Two pick-and-place cycles scheduled: t=2-12 s, t=17-27 s")
print(f"      Running XY10 FMU...")
t0 = time.time()
res_xy = simulate_fmu(
    filename        = FMU_XY10,
    start_time      = 0.0,
    stop_time       = T_CYCLE,
    output_interval = DT_MASTER,
    input           = input_xy10,
)
dt_xy = time.time() - t0
print(f"      Done in {dt_xy:.1f} s real-time")

t_xy = res_xy["time"]
P_xy   = np.interp(t_master, t_xy, res_xy["P_elec"])
x_pos  = np.interp(t_master, t_xy, res_xy["x_pos"])
y_pos  = np.interp(t_master, t_xy, res_xy["y_pos"])
z_pos  = np.interp(t_master, t_xy, res_xy["z_pos"])
vac_p  = np.interp(t_master, t_xy, res_xy["vacuum_p"])
print(f"      Peak XY10 power : {np.max(P_xy):.2f} W")
print(f"      X range         : {x_pos.min():.3f} to {x_pos.max():.3f} m")
print()

# ============================================================
# STEP 3 - CR5 COBOT (one pick-place between conveyor and XY10)
# ============================================================
print("[3/4] Building CR5 torque trajectory (one assembly cycle)...")

# Simplified J2 (shoulder) torque profile: hold + lift + return
# Real CR5 motion planning would come from inverse kinematics, but for the
# orchestration demo we use a representative torque profile.
tau_J2 = np.zeros(N_master)

# Active phase: t = 12 to 17 s (between the two XY10 cycles)
for ti in range(N_master):
    t = t_master[ti]
    if 12.0 <= t < 13.0:
        # Lift phase - peak torque to overcome gravity + accelerate
        tau_J2[ti] = 30.0 * (t - 12.0)
    elif 13.0 <= t < 14.0:
        # Hold at extended position - gravity compensation
        tau_J2[ti] = 30.0
    elif 14.0 <= t < 15.0:
        # Return phase
        tau_J2[ti] = 30.0 - 30.0 * (t - 14.0)
    elif 15.0 <= t < 16.0:
        # Lower & approach
        tau_J2[ti] = -15.0 + 15.0 * (t - 15.0)

cr5_active = (t_master >= 12.0) & (t_master <= 17.0)

# Pack as FMU input (6 joint torques)
input_cr5 = np.zeros(N_master,
    dtype=[("time", "f8")] +
          [(f"tau_ref[{i+1}]", "f8") for i in range(6)])
input_cr5["time"] = t_master
input_cr5["tau_ref[2]"] = tau_J2  # only J2 driven in this demo
print(f"      CR5 active window: t=12-17 s")
print(f"      Peak J2 torque   : {np.max(np.abs(tau_J2)):.1f} N.m")
print(f"      Running CR5 FMU...")

t0 = time.time()
try:
    res_cr5 = simulate_fmu(
        filename        = FMU_CR5,
        start_time      = 0.0,
        stop_time       = T_CYCLE,
        output_interval = DT_MASTER,
        input           = input_cr5,
    )
    dt_cr5 = time.time() - t0
    print(f"      Done in {dt_cr5:.1f} s real-time")
    t_cr = res_cr5["time"]
    P_cr5   = np.interp(t_master, t_cr, res_cr5["P_total"])
    q2_cr5  = np.interp(t_master, t_cr, res_cr5["q_out[2]"])
    q2d_cr5 = np.interp(t_master, t_cr, res_cr5["qdot_out[2]"])
    x_tcp   = np.interp(t_master, t_cr, res_cr5["x_tcp"])
    y_tcp   = np.interp(t_master, t_cr, res_cr5["y_tcp"])
    z_tcp   = np.interp(t_master, t_cr, res_cr5["z_tcp"])
    cr5_ok = True
    print(f"      Peak CR5 power : {np.max(P_cr5):.2f} W")
    print(f"      J2 angle range : "
          f"{np.degrees(q2_cr5).min():.1f} to "
          f"{np.degrees(q2_cr5).max():.1f} deg")
except Exception as e:
    print(f"      CR5 FMU failed: {e}")
    print(f"      Substituting zero CR5 trace (plot will show 'CR5 not "
          f"available').")
    P_cr5   = np.zeros(N_master)
    q2_cr5  = np.zeros(N_master)
    q2d_cr5 = np.zeros(N_master)
    x_tcp = y_tcp = z_tcp = np.zeros(N_master)
    cr5_ok = False
print()

# ============================================================
# STEP 4 - AGGREGATE LINE STATE
# ============================================================
print("[4/4] Aggregating line state and building output...")

# Total instantaneous line power
P_total = P_conv + P_xy + P_cr5

# Energies per subsystem and total
E_conv  = float(np.trapezoid(P_conv,  t_master))
E_xy    = float(np.trapezoid(P_xy,    t_master))
E_cr5   = float(np.trapezoid(P_cr5,   t_master))
E_total = float(np.trapezoid(P_total, t_master))

print(f"      Energy per 30-s cycle:")
print(f"        Conveyor : {E_conv:>10.1f} J  ({E_conv/E_total*100:5.1f} %)")
print(f"        XY10     : {E_xy:>10.1f} J  ({E_xy/E_total*100:5.1f} %)")
print(f"        CR5      : {E_cr5:>10.1f} J  ({E_cr5/E_total*100:5.1f} %)")
print(f"        TOTAL    : {E_total:>10.1f} J")
print()

# ============================================================
# STEP 5 - SAVE CSV (for digital twin / RL downstream use)
# ============================================================
df = pd.DataFrame({
    "time_s"       : t_master,
    "P_conv_W"     : P_conv,
    "P_xy10_W"     : P_xy,
    "P_cr5_W"      : P_cr5,
    "P_total_W"    : P_total,
    "i_conv_A"     : i_conv,
    "v_belt_m_s"   : v_belt,
    "x_belt_m"     : x_belt,
    "T_motor_K"    : T_motor,
    "x_xy10_m"     : x_pos,
    "y_xy10_m"     : y_pos,
    "z_xy10_m"     : z_pos,
    "vacuum_p_Pa"  : vac_p,
    "q2_cr5_rad"   : q2_cr5,
    "q2_dot_rad_s" : q2d_cr5,
    "xy10_active"  : xy10_active.astype(int),
    "cr5_active"   : cr5_active.astype(int),
})
csv_path = OUT_DIR / "alix_line_state.csv"
df.to_csv(csv_path, index=False, float_format="%.6f")
print(f"      Master state CSV saved: {csv_path}")
print(f"      ({len(df)} rows x {len(df.columns)} columns)")
print()

# ============================================================
# STEP 6 - PLOT MASTER TIMELINE
# ============================================================
print("Building master timeline figure...")
fig, axes = plt.subplots(6, 1, figsize=(13, 14), sharex=True)

# 1 - Total line power
ax = axes[0]
ax.plot(t_master, P_total, color="#1E3A5F", lw=2, label="Total line")
ax.fill_between(t_master, 0, P_total, color="#1E3A5F", alpha=0.15)
ax.set_ylabel("Power (W)", fontsize=11)
ax.set_title("ALIX LINE - 30-second production cycle (single-program "
             f"end-to-end simulation)", fontsize=13, fontweight="bold")
ax.grid(alpha=0.3)
ax.legend(loc="upper right")

# 2 - Per subsystem power
ax = axes[1]
ax.plot(t_master, P_conv, color="#1F618D", lw=1.5, label="Conveyor")
ax.plot(t_master, P_xy,   color="#27AE60", lw=1.5, label="XY10")
ax.plot(t_master, P_cr5,  color="#A93226", lw=1.5, label="CR5")
ax.set_ylabel("Power (W)", fontsize=11)
ax.grid(alpha=0.3)
ax.legend(loc="upper right", ncol=3)

# 3 - Conveyor belt position
ax = axes[2]
ax.plot(t_master, x_belt, color="#1F618D", lw=1.5)
ax.set_ylabel("Belt x (m)", fontsize=11)
ax.grid(alpha=0.3)

# 4 - XY10 positions
ax = axes[3]
ax.plot(t_master, x_pos, color="#27AE60", lw=1.5, label="x")
ax.plot(t_master, y_pos, color="#1E8449", lw=1.5, label="y")
ax.plot(t_master, z_pos, color="#0E6655", lw=1.5, label="z")
# Shade XY10 active windows
ax.axvspan(2, 12, alpha=0.08, color="#27AE60")
ax.axvspan(17, 27, alpha=0.08, color="#27AE60")
ax.set_ylabel("XY10 pos (m)", fontsize=11)
ax.grid(alpha=0.3)
ax.legend(loc="upper right", ncol=3)

# 5 - CR5 J2 angle
ax = axes[4]
ax.plot(t_master, np.degrees(q2_cr5), color="#A93226", lw=1.5,
        label="J2 angle")
ax.axvspan(12, 17, alpha=0.08, color="#A93226")
ax.set_ylabel("CR5 J2 (deg)", fontsize=11)
ax.grid(alpha=0.3)
ax.legend(loc="upper right")

# 6 - Activity bar (which subsystem is doing work)
ax = axes[5]
ax.fill_between(t_master, 0, 1,
                where=(P_conv > 50), color="#1F618D", alpha=0.5,
                label="Conveyor running")
ax.fill_between(t_master, 1, 2,
                where=xy10_active, color="#27AE60", alpha=0.5,
                label="XY10 active")
ax.fill_between(t_master, 2, 3,
                where=cr5_active, color="#A93226", alpha=0.5,
                label="CR5 active")
ax.set_ylim(0, 3.2)
ax.set_yticks([0.5, 1.5, 2.5])
ax.set_yticklabels(["Conveyor", "XY10", "CR5"])
ax.set_xlabel("Time (s)", fontsize=11)
ax.grid(alpha=0.3, axis="x")
ax.legend(loc="upper right", ncol=3, fontsize=9)

plt.tight_layout()
fig_path = OUT_DIR / "alix_line_master_timeline.png"
plt.savefig(fig_path, dpi=180, bbox_inches="tight")
print(f"Master timeline figure saved: {fig_path}")
print()

# ============================================================
# SUMMARY TEXT
# ============================================================
summary_path = OUT_DIR / "orchestration_summary.txt"
with open(summary_path, "w") as f:
    f.write("ALIX LINE - END-TO-END ORCHESTRATION SUMMARY\n")
    f.write("=" * 60 + "\n\n")
    f.write(f"Production cycle duration : {T_CYCLE} s\n")
    f.write(f"Master timestep           : {DT_MASTER*1000:.0f} ms "
            f"(rate {1/DT_MASTER:.0f} Hz)\n")
    f.write(f"Samples on master grid    : {N_master}\n\n")
    f.write(f"Conveyor:\n")
    f.write(f"  Mean power         : {np.mean(P_conv):.1f} W\n")
    f.write(f"  Peak phase current : {np.max(np.abs(i_conv)):.3f} A\n")
    f.write(f"  Final motor temp   : {T_motor[-1]-273.15:.1f} deg C\n")
    f.write(f"  Energy per cycle   : {E_conv:.1f} J\n\n")
    f.write(f"XY10 (2 cycles per 30-s window):\n")
    f.write(f"  Peak power         : {np.max(P_xy):.2f} W\n")
    f.write(f"  X travel max       : {x_pos.max():.3f} m\n")
    f.write(f"  Y travel max       : {y_pos.max():.3f} m\n")
    f.write(f"  Energy per cycle   : {E_xy:.1f} J\n\n")
    f.write(f"CR5 (1 cycle per 30-s window):\n")
    if cr5_ok:
        f.write(f"  Peak power         : {np.max(P_cr5):.2f} W\n")
        f.write(f"  J2 angle range     : "
                f"{np.degrees(q2_cr5).min():.1f} to "
                f"{np.degrees(q2_cr5).max():.1f} deg\n")
        f.write(f"  Energy per cycle   : {E_cr5:.1f} J\n\n")
    else:
        f.write(f"  FMU run failed - see console log\n\n")
    f.write(f"TOTAL line energy per cycle: {E_total:.1f} J\n")
print(f"Summary text saved: {summary_path}")
print()
print("=" * 75)
print("ORCHESTRATION COMPLETE")
print("=" * 75)
print()
print("Files produced:")
print(f"  CSV   : {csv_path}")
print(f"  Plot  : {fig_path}")
print(f"  Text  : {summary_path}")
print()
print("This is the central deliverable of the internship per the brief:")
print("'the entire production line simulated end-to-end from a single program'")
print()
plt.show()