"""
energy_analysis_chart.py
=========================
Complete energy analysis chart for the ALIX digital twin.
Compares per-subsystem energy: model vs measured, with honest
explanation of every gap.

Output: energy_analysis_update.png (slide-ready, 16:9 friendly)
"""

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import FancyBboxPatch
from pathlib import Path

OUT_DIR = Path(r"C:\Users\satres\Documents\ALIX\FMU_Updated\orchestration_output")
OUT_DIR.mkdir(exist_ok=True)

# Colours
C_MODEL    = "#2E75B6"   # blue — model
C_MEAS     = "#E07B47"   # orange — measured
C_GAP      = "#A93226"   # red — gap
C_GOOD     = "#27AE60"   # green — good agreement
C_TEXT     = "#1E3A5F"

fig = plt.figure(figsize=(16, 9))
gs = fig.add_gridspec(3, 3, height_ratios=[0.6, 2.5, 1.3],
                      hspace=0.45, wspace=0.35)

# ============================================================
# TITLE BANNER
# ============================================================
ax_title = fig.add_subplot(gs[0, :])
ax_title.axis("off")
ax_title.text(0.5, 0.7, "ALIX LINE — ENERGY ANALYSIS ",
              ha="center", fontsize=18, fontweight="bold", color=C_TEXT)
ax_title.text(0.5, 0.15,
              "Per-subsystem model vs measured energy "
              "with honest gap analysis · 30 s production cycle",
              ha="center", fontsize=11, style="italic", color="#5B6B7B")

# ============================================================
# PANEL 1 — CONVEYOR (bar chart)
# ============================================================
ax1 = fig.add_subplot(gs[1, 0])
conveyor_data = {
    "Model\n(end-to-end)":        3321.4,
    "Apparent\npower est.":       ~20000,
    "Active power\n(cos phi=0.8)":~16000,
}
# Use sensible scale
conv_labels  = ["Model FMU\n(orchestrator)",
                "Measured\napparent (VA·s)",
                "Measured\nactive (W·s)"]
conv_values  = [3321, 20300, 16240]
conv_colors  = [C_MODEL, C_MEAS, C_MEAS]

bars = ax1.bar(conv_labels, conv_values, color=conv_colors,
               edgecolor=C_TEXT, lw=1.2, alpha=0.85)
for bar, v in zip(bars, conv_values):
    ax1.text(bar.get_x() + bar.get_width()/2, v + 500,
             f"{v:,} J", ha="center", fontsize=9.5,
             fontweight="bold", color=C_TEXT)

ax1.set_ylabel("Energy per 30-s cycle (J)", fontsize=10)
ax1.set_title("CONVEYOR", fontsize=12, fontweight="bold", color=C_TEXT)
ax1.set_ylim(0, 24000)
ax1.grid(axis="y", alpha=0.3)
ax1.text(0.5, -0.32,
         "Model: continuous 110.7 W mean × 30 s = 3321 J\n"
         "Measured: 843 VA × 30 s × 0.8 PF ≈ 16 kJ active\n"
         "Gap: ~5× — model under-predicts losses\n"
         "(iron, stray, friction not fully captured)",
         transform=ax1.transAxes, ha="center", va="top",
         fontsize=8, color="#5B6B7B",
         bbox=dict(boxstyle="round,pad=0.4", fc="#FFF3E0",
                   edgecolor="#E07B47", lw=0.8))

# ============================================================
# PANEL 2 — XY10 (logarithmic to show 400× gap)
# ============================================================
ax2 = fig.add_subplot(gs[1, 1])
xy_labels = ["Model FMU\n(end-to-end)",
             "Model standalone\n(xy10_clean)",
             "Measured\nburst (TDMS)"]
xy_values = [19.9, 12.4, 4922]
xy_colors = [C_MODEL, C_MODEL, C_MEAS]

bars = ax2.bar(xy_labels, xy_values, color=xy_colors,
               edgecolor=C_TEXT, lw=1.2, alpha=0.85)
ax2.set_yscale("log")
ax2.set_ylim(1, 30000)
for bar, v in zip(bars, xy_values):
    ax2.text(bar.get_x() + bar.get_width()/2, v * 1.5,
             f"{v:.1f} J", ha="center", fontsize=9.5,
             fontweight="bold", color=C_TEXT)
ax2.set_ylabel("Energy (J, log scale)", fontsize=10)
ax2.set_title("XY10 STATION", fontsize=12, fontweight="bold", color=C_TEXT)
ax2.grid(axis="y", alpha=0.3, which="both")
ax2.text(0.5, -0.32,
         "Model captures motion + copper losses only.\n"
         "Measured includes stepper HOLDING current\n"
         "(chopper-mode ±20 A continuous drive electronics).\n"
         "Gap is STRUCTURAL — Phase 2 adds holding-current term.",
         transform=ax2.transAxes, ha="center", va="top",
         fontsize=8, color="#5B6B7B",
         bbox=dict(boxstyle="round,pad=0.4", fc="#FFF3E0",
                   edgecolor="#E07B47", lw=0.8))

# ============================================================
# PANEL 3 — CR5 (no measurement target)
# ============================================================
ax3 = fig.add_subplot(gs[1, 2])
cr5_labels = ["Model FMU\n(5 s cycle)",
              "Brochure\nstatic mass check",
              "Per-joint\npower meas."]
cr5_values = [65.8, 94.9, 0]   # mass check shown as %
cr5_colors = [C_MODEL, C_GOOD, "#BDC3C7"]

# Mixed-unit display, so use two y-axes
bars = ax3.bar(cr5_labels[:1], cr5_values[:1], color=cr5_colors[:1],
               edgecolor=C_TEXT, lw=1.2, alpha=0.85, width=0.6)
ax3.text(0, cr5_values[0] + 5, f"{cr5_values[0]:.1f} J",
         ha="center", fontsize=9.5, fontweight="bold", color=C_TEXT)
ax3.set_ylabel("Energy per assembly cycle (J)", fontsize=10)
ax3.set_ylim(0, 100)
ax3.set_xlim(-0.5, 2.5)

# annotation for the other two
ax3.text(1, 50, "94.9 %\nmass match\n(structural)",
         ha="center", va="center", fontsize=10, fontweight="bold",
         color=C_GOOD,
         bbox=dict(boxstyle="round,pad=0.3", fc="#E8F5E9",
                   edgecolor=C_GOOD, lw=1.2))
ax3.text(2, 50, "NO TARGET\nPhase 2:\ninstrument\njoint motors",
         ha="center", va="center", fontsize=9, fontweight="bold",
         color="#7F8C8D",
         bbox=dict(boxstyle="round,pad=0.3", fc="#F2F4F7",
                   edgecolor="#7F8C8D", lw=1.0))
ax3.set_xticks([0, 1, 2])
ax3.set_xticklabels(cr5_labels, fontsize=9)

ax3.set_title("CR5 COBOT", fontsize=12, fontweight="bold", color=C_TEXT)
ax3.grid(axis="y", alpha=0.3)
ax3.text(0.5, -0.32,
         "Model: 49 W peak × 5 s assembly cycle = 66 J\n"
         "CAD mass agreement 23.74 kg vs 25 kg brochure = 94.9 %\n"
         "No per-joint power measurement on ALIX line.\n"
         "Phase 2: instrument joint motor currents for calibration.",
         transform=ax3.transAxes, ha="center", va="top",
         fontsize=8, color="#5B6B7B",
         bbox=dict(boxstyle="round,pad=0.4", fc="#E8F5E9",
                   edgecolor=C_GOOD, lw=0.8))

# ============================================================
# BOTTOM PANEL — TOTAL LINE ENERGY DECOMPOSITION
# ============================================================
ax4 = fig.add_subplot(gs[2, :])

# Stacked horizontal bar — total line per 30 s cycle
categories = ["MODEL\n(orchestrator)", "MEASURED\n(line apparent)"]
conv_vals    = [3321, 16240]      # active power equivalent
cr5_vals     = [66, 0]            # not measured separately
xy10_vals    = [20, 4922 * 30/15] # scaled to 30-s window: 9844 J
unmeasured   = [0, max(0, 25000 - 16240 - 9844)]  # unaccounted

# build stacked bar
bottom = 0
for vals, color, label in [
    (conv_vals, C_MODEL,  "Conveyor"),
    (xy10_vals, C_GOOD,   "XY10"),
    (cr5_vals,  "#A93226", "CR5"),
    (unmeasured, "#BDC3C7","Unmeasured / standby")]:
    ax4.barh(categories, vals, left=bottom, color=color,
             edgecolor=C_TEXT, lw=0.8, alpha=0.85, label=label)
    bottom = bottom + np.array(vals)

ax4.set_xlabel("Energy per 30-s production cycle (J)", fontsize=11)
ax4.set_title("TOTAL LINE ENERGY DECOMPOSITION — MODEL vs MEASURED",
              fontsize=12, fontweight="bold", color=C_TEXT)
ax4.legend(loc="upper right", ncol=4, fontsize=9)
ax4.grid(axis="x", alpha=0.3)
ax4.text(0.5, -0.35,
         "MODEL total per cycle: 3 407 J          MEASURED apparent: ~16-20 kJ\n"
         "Modelled subsystems cover 100 % of active mechatronic actuators\n"
         "but capture only the dynamic (motion) component of total line energy.\n"
         "Idle electronics + stepper holding + control cabinet not modelled — "
         "Phase 2 work.",
         transform=ax4.transAxes, ha="center", va="top",
         fontsize=9.5, color=C_TEXT,
         bbox=dict(boxstyle="round,pad=0.4", fc="#F2F4F7",
                   edgecolor=C_TEXT, lw=1.0))

plt.tight_layout(rect=[0, 0.02, 1, 0.96])
out_path = OUT_DIR / "energy_analysis_update.png"
plt.savefig(out_path, dpi=200, bbox_inches="tight")
print(f"Saved: {out_path}")
plt.show()