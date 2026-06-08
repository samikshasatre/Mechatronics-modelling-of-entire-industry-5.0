"""
energy_analysis_FIXED.py - Energy analysis with axis fix (Romain's feedback).

FIX (vs original): Panel A is split into two stacked sub-panels matched to
each subsystem's actual magnitude:
  - Panel A1 (top):    Conveyor only,           y-axis 100-120 W
  - Panel A2 (bottom): Stations + sensors,      y-axis 0-25 W
This separates signals by physical nature rather than forcing all on one
0-250 W axis where the conveyor dominates visually.

Panels B (% over time) and C (cumulative bars) are unchanged.

DATA INPUTS:
This script expects power-vs-time arrays for each subsystem. Adjust the
LOAD DATA section below to match how your original script reads the data.
If you have a CSV or .npz file from your line simulation, point to it there.
"""

import os
import numpy as np
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))

# =====================================================================
# LOAD DATA - replace this block to match your actual data source
# =====================================================================
# Option A: load from .npz file produced by your line simulation
# data = np.load(os.path.join(HERE, "..", "Results", "energy_data.npz"))
# t = data["t"]
# P_conveyor = data["P_conveyor"]
# P_xy_x = data["P_xy_x"]
# ... etc

# Option B: load from CSV
# import pandas as pd
# df = pd.read_csv(os.path.join(HERE, "..", "Results", "energy_data.csv"))
# t = df["time"].values
# P_conveyor = df["P_conveyor"].values
# ... etc

# Option C: REGENERATE from FMU orchestration (if your original did this)
# Insert your FMU orchestration loop here.

# Fallback: example data matching the shape of the original plot
# REPLACE THIS WITH YOUR REAL DATA LOAD
t = np.linspace(0, 30, 3000)
P_conveyor = np.full_like(t, 108.0)
P_conveyor[:50] = np.linspace(0, 250, 50)  # startup transient
P_conveyor[50:100] = np.linspace(250, 108, 50)  # settling
P_xy_x = np.zeros_like(t)
P_xy_y = np.zeros_like(t)
P_xy_z = np.zeros_like(t)
P_pneumatic = np.zeros_like(t)
P_pneumatic[(t > 4) & (t < 8)] = 15.0
P_pneumatic[(t > 18) & (t < 22)] = 15.0
P_sensors = np.full_like(t, 8.0)
# =====================================================================

# Build station + sensors group (small/intermittent signals)
P_total = P_conveyor + P_xy_x + P_xy_y + P_xy_z + P_pneumatic + P_sensors

# Energies (J = integral of power over time)
# Use np.trapezoid (numpy >=2.0) with fallback to np.trapz (older numpy)
_trapz = getattr(np, "trapezoid", None) or np.trapz
dt = t[1] - t[0]
E_conveyor   = _trapz(P_conveyor,   t)
E_xy_x       = _trapz(P_xy_x,       t)
E_xy_y       = _trapz(P_xy_y,       t)
E_xy_z       = _trapz(P_xy_z,       t)
E_pneumatic  = _trapz(P_pneumatic,  t)
E_sensors    = _trapz(P_sensors,    t)
E_total      = E_conveyor + E_xy_x + E_xy_y + E_xy_z + E_pneumatic + E_sensors

# ============== PLOT ==============
fig = plt.figure(figsize=(15, 13))
gs = fig.add_gridspec(4, 1, height_ratios=[1.2, 1.2, 1.5, 1.5], hspace=0.45)

fig.suptitle("ALIX Digital Twin - Energy Analysis per Subsystem\n"
             "End goal: identify energy-efficiency opportunities for Industry 5.0",
             fontsize=13, weight="bold")

# -------- Panel A1 (top): Conveyor only, tight y-axis around 108 W --------
ax1 = fig.add_subplot(gs[0])
ax1.plot(t, P_conveyor, color="#1f77b4", lw=1.4, label="Conveyor (induction motor)")
ax1.set_ylabel("Power [W]")
ax1.set_title("Panel A1: Conveyor - continuous load (axis matched to 100-120 W range)")
ax1.set_ylim(100, 120)
ax1.set_xlim(0, t[-1])
ax1.grid(True, alpha=0.4)
ax1.legend(loc="upper right")

# -------- Panel A2: stations + sensors, tight y-axis around 0-25 W --------
ax2 = fig.add_subplot(gs[1], sharex=ax1)
ax2.plot(t, P_xy_x,      lw=1.2, label="XY10 X axis (stepper)", color="#ff7f0e")
ax2.plot(t, P_xy_y,      lw=1.2, label="XY10 Y axis (stepper)", color="#bcbd22")
ax2.plot(t, P_xy_z,      lw=1.2, label="XY10 Z axis (stepper)", color="#d62728")
ax2.plot(t, P_pneumatic, lw=1.2, label="Pneumatic (vacuum + cylinders)", color="#2ca02c")
ax2.plot(t, P_sensors,   lw=1.2, label="Sensors + PLC + HMI", color="#9467bd")
ax2.set_ylabel("Power [W]")
ax2.set_xlabel("Time [s]")
ax2.set_title("Panel A2: Stations + sensors - intermittent + low-power (axis 0-25 W)")
ax2.set_ylim(0, 25)
ax2.grid(True, alpha=0.4)
ax2.legend(loc="upper right", ncol=2, fontsize=8)

# -------- Panel B: % of total power over time (unchanged) --------
ax3 = fig.add_subplot(gs[2])
shares = np.vstack([P_conveyor, P_xy_x, P_xy_y, P_xy_z, P_pneumatic, P_sensors])
shares_pct = 100.0 * shares / np.maximum(P_total, 1e-6)
ax3.stackplot(t, shares_pct,
              labels=["Conveyor (induction motor)",
                      "XY10 X axis (stepper)",
                      "XY10 Y axis (stepper)",
                      "XY10 Z axis (stepper)",
                      "Pneumatic (vacuum + cylinders)",
                      "Sensors + PLC + HMI"],
              colors=["#1f77b4", "#ff7f0e", "#bcbd22", "#d62728", "#2ca02c", "#9467bd"],
              alpha=0.85)
ax3.set_ylabel("% of total power")
ax3.set_xlabel("Time [s]")
ax3.set_title("Panel B: % of total instantaneous power per subsystem over time")
ax3.set_ylim(0, 100)
ax3.set_xlim(0, t[-1])
ax3.grid(True, alpha=0.4)
ax3.legend(loc="upper right", ncol=2, fontsize=8)

# -------- Panel C: cumulative energy bars (unchanged) --------
ax4 = fig.add_subplot(gs[3])
energies = [E_conveyor, E_sensors, E_pneumatic, E_xy_z, E_xy_x, E_xy_y]
labels   = ["Conveyor (induction motor)",
            "Sensors + PLC + HMI",
            "Pneumatic (vacuum + cylinders)",
            "XY10 Z axis (stepper)",
            "XY10 X axis (stepper)",
            "XY10 Y axis (stepper)"]
colors   = ["#1f77b4", "#9467bd", "#2ca02c", "#d62728", "#ff7f0e", "#bcbd22"]
pcts     = [100.0 * e / E_total if E_total > 0 else 0 for e in energies]

y_pos = np.arange(len(labels))
ax4.barh(y_pos, energies, color=colors, alpha=0.85)
ax4.set_yticks(y_pos)
ax4.set_yticklabels([f"{lab}\n({pct:.1f}%)" for lab, pct in zip(labels, pcts)],
                     fontsize=9)
ax4.invert_yaxis()
ax4.set_xlabel(f"Cumulative energy over {t[-1]:.0f} s [J]")
ax4.set_title(f"Panel C: Cumulative energy per subsystem - total = {E_total:.0f} J ({E_total/3600:.3f} Wh)")
ax4.grid(True, axis="x", alpha=0.4)
for i, (e, p) in enumerate(zip(energies, pcts)):
    ax4.text(e + 0.01 * E_total, i, f"{e:.0f} J ({p:.1f}%)", va="center", fontsize=9)

fig.subplots_adjust(top=0.95, hspace=0.7, wspace=0.35)
out_path = os.path.join(HERE, "energy_analysis_FIXED.png")
plt.savefig(out_path, dpi=140, bbox_inches="tight")
print(f"Figure saved: {out_path}")
plt.show()