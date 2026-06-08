"""
xy10_clean.py
=============
Run the XY10Station FMU with a pick-and-place command sequence
and produce a clean 3-panel validation plot.
"""

import numpy as np
import matplotlib.pyplot as plt
from fmpy import simulate_fmu

# ============================================================
# CONFIGURATION
# ============================================================
FMU_PATH      = r"C:\Users\satres\Documents\ALIX\FMU_Updated\FMUS\XY10Station_v2.fmu"
OUTPUT_FIGURE = r"C:\Users\satres\Documents\ALIX\FMU_Updated\xy10_clean.png"

T_END = 12.0
DT    = 0.005

# ============================================================
# STEP 1 - Build the pick-and-place command sequence (12 s)
# ============================================================
n_steps = int(T_END / DT) + 1
t       = np.linspace(0, T_END, n_steps)

T_MOVE_TO_PICK   = 2.0
T_ENGAGE         = 4.5
T_MOVE_TO_PLACE  = 7.0
T_RELEASE        = 9.5


def ramp(t_arr, t_a, t_b, v_a, v_b):
    out = np.where(t_arr <= t_a, v_a, v_b)
    mask = (t_arr > t_a) & (t_arr < t_b)
    out = np.where(mask, v_a + (v_b - v_a) * (t_arr - t_a) / (t_b - t_a), out)
    return out


# X axis: starts at 0, moves to 0.10 m for pick, then 0.25 m for place
# (within 0 to 0.30 m physical travel)
x_cmd = ramp(t, 0.5, T_MOVE_TO_PICK, 0.0, 0.10)
mask = t > T_MOVE_TO_PLACE - 0.5
x_cmd[mask] = ramp(t[mask], T_MOVE_TO_PLACE - 0.5, T_MOVE_TO_PLACE, 0.10, 0.25)
x_cmd[t > T_MOVE_TO_PLACE] = 0.25

# Y axis: 0 to 0.10 m for pick, 0.20 m for place
# (within 0 to 0.25 m physical travel)
y_cmd = ramp(t, 0.5, T_MOVE_TO_PICK, 0.0, 0.10)
mask = t > T_MOVE_TO_PLACE - 0.5
y_cmd[mask] = ramp(t[mask], T_MOVE_TO_PLACE - 0.5, T_MOVE_TO_PLACE, 0.10, 0.20)
y_cmd[t > T_MOVE_TO_PLACE] = 0.20

# Z axis: 0 to 0.05 m down for pick, back to 0, down for place, back to 0
# (within 0 to 0.10 m physical travel — POSITIVE means down in this model)
z_cmd = np.zeros_like(t)
# Down to pick
mask = (t >= T_MOVE_TO_PICK) & (t < T_MOVE_TO_PICK + 0.5)
z_cmd[mask] = ramp(t[mask], T_MOVE_TO_PICK, T_MOVE_TO_PICK + 0.5, 0.0, 0.05)
# Hold low while engaging
mask = (t >= T_MOVE_TO_PICK + 0.5) & (t < T_ENGAGE + 0.3)
z_cmd[mask] = 0.05
# Up after engage
mask = (t >= T_ENGAGE + 0.3) & (t < T_ENGAGE + 0.8)
z_cmd[mask] = ramp(t[mask], T_ENGAGE + 0.3, T_ENGAGE + 0.8, 0.05, 0.0)
# Transit at top
mask = (t >= T_ENGAGE + 0.8) & (t < T_MOVE_TO_PLACE)
z_cmd[mask] = 0.0
# Down to place
mask = (t >= T_MOVE_TO_PLACE) & (t < T_MOVE_TO_PLACE + 0.5)
z_cmd[mask] = ramp(t[mask], T_MOVE_TO_PLACE, T_MOVE_TO_PLACE + 0.5, 0.0, 0.05)
# Hold low while releasing
mask = (t >= T_MOVE_TO_PLACE + 0.5) & (t < T_RELEASE + 0.3)
z_cmd[mask] = 0.05
# Up after release
mask = (t >= T_RELEASE + 0.3) & (t < T_RELEASE + 0.8)
z_cmd[mask] = ramp(t[mask], T_RELEASE + 0.3, T_RELEASE + 0.8, 0.05, 0.0)

# Vacuum command
vacuum_cmd = ((t >= T_ENGAGE) & (t <= T_RELEASE))

# ============================================================
# STEP 2 - Pack into FMI input structured array
# ============================================================
input_dtype = np.dtype([
    ("time",       np.float64),
    ("x_cmd",      np.float64),
    ("y_cmd",      np.float64),
    ("z_cmd",      np.float64),
    ("vacuum_cmd", np.bool_),
])
inp = np.zeros(n_steps, dtype=input_dtype)
inp["time"]       = t
inp["x_cmd"]      = x_cmd
inp["y_cmd"]      = y_cmd
inp["z_cmd"]      = z_cmd
inp["vacuum_cmd"] = vacuum_cmd

print(f"Input trajectory built: {n_steps} samples, {T_END:.1f} s")
print(f"  x_cmd range: {x_cmd.min():.3f} to {x_cmd.max():.3f} m")
print(f"  y_cmd range: {y_cmd.min():.3f} to {y_cmd.max():.3f} m")
print(f"  z_cmd range: {z_cmd.min():.3f} to {z_cmd.max():.3f} m")
print(f"  vacuum_cmd: ON from {T_ENGAGE} to {T_RELEASE} s")


# ============================================================
# STEP 3 - Run the FMU
# ============================================================
print(f"\nSimulating FMU...")
result = simulate_fmu(
    filename        = FMU_PATH,
    start_time      = 0.0,
    stop_time       = T_END,
    output_interval = DT,
    input           = inp,
)
print(f"Done: {len(result)} output samples")

# ============================================================
# STEP 4 - Extract outputs
# ============================================================
t_out = result["time"]
x_pos = result["x_pos"]
y_pos = result["y_pos"]
z_pos = result["z_pos"]
i_x   = result["i_x"]
i_y   = result["i_y"]
i_z   = result["i_z"]
vac_p = result["vacuum_p"]
grip  = result["gripper_attached"]
P_el  = result["P_elec"]

# Energy integral (handles both old + new numpy)
try:
    energy = np.trapezoid(P_el, t_out)
except AttributeError:
    energy = np.trapz(P_el, t_out)

print(f"\nFMU output signal ranges:")
print(f"  x_pos:    {x_pos.min():+.4f} to {x_pos.max():+.4f} m   (cmd 0 to 0.55)")
print(f"  y_pos:    {y_pos.min():+.4f} to {y_pos.max():+.4f} m   (cmd 0 to 0.20)")
print(f"  z_pos:    {z_pos.min():+.4f} to {z_pos.max():+.4f} m   (cmd 0 to -0.05)")
print(f"  i_x:      {i_x.min():+.3f} to {i_x.max():+.3f} A")
print(f"  i_y:      {i_y.min():+.3f} to {i_y.max():+.3f} A")
print(f"  i_z:      {i_z.min():+.3f} to {i_z.max():+.3f} A")
print(f"  vac_p:    {vac_p.min():.0f} to {vac_p.max():.0f} Pa")
print(f"  grip:     {grip.min():.2f} to {grip.max():.2f}")
print(f"  P_elec:   {P_el.min():.2f} to {P_el.max():.2f} W")
print(f"  Energy:   E = integral(P_elec dt) = {energy:.2f} J")

# ============================================================
# STEP 5 - Make the 3-panel plot
# ============================================================
fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(11, 9), sharex=True)
fig.suptitle("XY10 station - pick-and-place over 12 s (3-axis model)",
             fontsize=13, fontweight="bold", y=0.995)

events = [(T_MOVE_TO_PICK,  "Move to pick"),
          (T_ENGAGE,        "Engage gripper"),
          (T_MOVE_TO_PLACE, "Move to place"),
          (T_RELEASE,       "Release")]

# PANEL 1: Position tracking
ax1.plot(t,     x_cmd, color="#1F618D", ls="--", lw=1.0, alpha=0.6, label="X cmd")
ax1.plot(t_out, x_pos, color="#1F618D", ls="-",  lw=1.8,            label="X actual")
ax1.plot(t,     y_cmd, color="#1E8449", ls="--", lw=1.0, alpha=0.6, label="Y cmd")
ax1.plot(t_out, y_pos, color="#1E8449", ls="-",  lw=1.8,            label="Y actual")
ax1.plot(t,     z_cmd, color="#A93226", ls="--", lw=1.0, alpha=0.6, label="Z cmd")
ax1.plot(t_out, z_pos, color="#A93226", ls="-",  lw=1.8,            label="Z actual")
ax1.set_ylabel("Position (m)", fontsize=11)
ax1.legend(loc="upper right", ncol=3, fontsize=9, frameon=False)
ax1.grid(alpha=0.3)
ax1.set_title("Panel 1 - Position tracking (commanded dashed, actual solid)",
              fontsize=10, loc="left")
for t_evt, lbl in events:
    ax1.axvline(t_evt, color="grey", ls=":", alpha=0.5)
    ax1.text(t_evt, ax1.get_ylim()[1]*1.02, lbl, ha="center",
             fontsize=9, color="grey")

# PANEL 2: Motor currents
ax2.plot(t_out, i_x, color="#1F618D", lw=1.5, label="i_x")
ax2.plot(t_out, i_y, color="#1E8449", lw=1.5, label="i_y")
ax2.plot(t_out, i_z, color="#A93226", lw=1.5, label="i_z")
ax2.set_ylabel("Motor current (A)", fontsize=11)
ax2.legend(loc="upper right", ncol=3, fontsize=9, frameon=False)
ax2.grid(alpha=0.3)
ax2.set_title("Panel 2 - Motor currents (peaks during acceleration/deceleration)",
              fontsize=10, loc="left")
for t_evt, _ in events:
    ax2.axvline(t_evt, color="grey", ls=":", alpha=0.5)
ax2.annotate(
    "Holding current between\nmoves is abstracted\n(DC-equivalent model).",
    xy=(0.02, 0.96), xycoords="axes fraction",
    fontsize=8, style="italic", color="0.4",
    verticalalignment="top",
    bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.7, edgecolor="none")
)

# PANEL 3: Vacuum + gripper
ax3.plot(t_out, vac_p / 1000.0, color="#E67E22", lw=2.0, label="Vacuum pressure (kPa)")
ax3.set_ylabel("Pressure (kPa)", color="#E67E22", fontsize=11)
ax3.tick_params(axis="y", labelcolor="#E67E22")
ax3.set_xlabel("Time (s)", fontsize=11)
ax3.grid(alpha=0.3)
ax3.set_title("Panel 3 - Vacuum + gripper logic (first-order chamber tau = 0.15 s)",
              fontsize=10, loc="left")

ax3b = ax3.twinx()
ax3b.step(t_out, (grip > 0.5).astype(int), color="#7B2CBF", lw=2.0,
          where="post", label="Gripper attached")
ax3b.set_ylabel("Gripper", color="#7B2CBF", fontsize=11)
ax3b.set_yticks([0, 1])
ax3b.set_yticklabels(["Off", "On"])
ax3b.tick_params(axis="y", labelcolor="#7B2CBF")
ax3b.set_ylim(-0.1, 1.3)

ax3.axvspan(T_ENGAGE, T_RELEASE, alpha=0.10, color="grey")
ax3.text((T_ENGAGE + T_RELEASE) / 2.0, 55, "Pot held",
         ha="center", fontsize=10, color="0.4", fontweight="bold")
for t_evt, _ in events:
    ax3.axvline(t_evt, color="grey", ls=":", alpha=0.5)

plt.tight_layout()
plt.savefig(OUTPUT_FIGURE, dpi=200, bbox_inches="tight")
print(f"\nFigure saved: {OUTPUT_FIGURE}")
plt.show()