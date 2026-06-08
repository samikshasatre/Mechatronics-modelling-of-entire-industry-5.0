"""
energy_decomposition_diagram.py
================================
Slide-ready energy decomposition diagram for the ALIX digital twin.

Layout per subsystem (3 rows):
  Left:    pie chart showing the model's energy share
  Middle:  bar chart - model vs measured
  Right:   status callout (gap explanation + Phase 2 action)
"""

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import FancyBboxPatch
from pathlib import Path

OUT_DIR = Path(r"C:\Users\satres\Documents\ALIX\FMU_Updated\orchestration_output")
OUT_DIR.mkdir(exist_ok=True)

# Color palette
C_CONV   = "#1F618D"
C_XY10   = "#27AE60"
C_CR5    = "#A93226"
C_MODEL  = "#2E75B6"
C_MEAS   = "#E07B47"
C_GAP    = "#A93226"
C_GOOD   = "#27AE60"
C_TEXT   = "#1E3A5F"

fig = plt.figure(figsize=(17, 12))
gs = fig.add_gridspec(4, 3,
                      height_ratios=[0.5, 2.5, 2.5, 2.5],
                      width_ratios=[1.0, 1.4, 1.6],
                      hspace=0.6, wspace=0.4)

# ============================================================
# TITLE BANNER
# ============================================================
ax_title = fig.add_subplot(gs[0, :])
ax_title.axis("off")
ax_title.text(0.5, 0.75, "ALIX LINE — ENERGY DECOMPOSITION ANALYSIS",
              ha="center", fontsize=20, fontweight="bold", color=C_TEXT)
ax_title.text(0.5, 0.20,
              "Per-subsystem energy: model vs measurement, with honest "
              "gap analysis and Phase 2 roadmap",
              ha="center", fontsize=11, style="italic", color="#5B6B7B")

# ============================================================
# HELPER FUNCTIONS
# ============================================================
def draw_pie(ax, model_val, total_val, subsystem_name, color):
    """Pie showing this subsystem's share of total model energy."""
    other = max(0, total_val - model_val)
    sizes = [model_val, other]
    colors = [color, "#ECF0F1"]
    labels = [f"{subsystem_name}\n{model_val:.0f} J",
              f"Other\n{other:.0f} J"]
    wedges, texts = ax.pie(sizes, colors=colors,
                            startangle=90, counterclock=False,
                            wedgeprops=dict(edgecolor=C_TEXT, linewidth=1.5))
    pct = model_val / total_val * 100 if total_val > 0 else 0
    ax.text(0, 0, f"{pct:.1f}%",
            ha="center", va="center", fontsize=16, fontweight="bold",
            color=C_TEXT)
    ax.text(0, -1.35, f"{subsystem_name} share of\nMODEL total ({total_val:.0f} J)",
            ha="center", va="center", fontsize=9, color="#5B6B7B")

def draw_bar(ax, labels, values, colors, ylabel, title, ylim=None, logscale=False):
    """Bar chart with values labelled above each bar."""
    x = np.arange(len(labels))
    bars = ax.bar(x, values, color=colors, edgecolor=C_TEXT, lw=1.2, alpha=0.88)
    if logscale:
        ax.set_yscale("log")
    for bar, v in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width()/2,
                v * (1.5 if logscale else 1) + (0 if logscale else 0.04 * max(values)),
                f"{v:,.0f} J" if v >= 100 else f"{v:.1f} J",
                ha="center", fontsize=10, fontweight="bold", color=C_TEXT)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=9)
    ax.set_ylabel(ylabel, fontsize=10)
    ax.set_title(title, fontsize=11, fontweight="bold", color=C_TEXT)
    if ylim:
        ax.set_ylim(ylim)
    ax.grid(axis="y", alpha=0.3, which="both" if logscale else "major")

def draw_callout(ax, color, lines):
    """Status box with bullet text."""
    ax.axis("off")
    n_lines = len(lines)
    y = 0.95
    dy = 0.85 / max(n_lines, 6)
    for line in lines:
        if line.startswith("[BOLD]"):
            ax.text(0.04, y, line.replace("[BOLD]", ""),
                    ha="left", va="top", fontsize=11, fontweight="bold",
                    color=color, transform=ax.transAxes)
        else:
            ax.text(0.04, y, line, ha="left", va="top",
                    fontsize=9.5, color="#34495E", transform=ax.transAxes,
                    wrap=True)
        y -= dy
    # Border around the callout
    box = FancyBboxPatch((0.01, 0.05), 0.97, 0.92,
                         boxstyle="round,pad=0.02,rounding_size=0.02",
                         transform=ax.transAxes,
                         edgecolor=color, facecolor="#FFFBF5",
                         linewidth=1.5)
    ax.add_patch(box)

# ============================================================
# ROW 1 — CONVEYOR
# ============================================================
TOTAL_MODEL = 3321 + 65.8 + 19.9   # 3406.7 J

ax_pie  = fig.add_subplot(gs[1, 0])
ax_bar  = fig.add_subplot(gs[1, 1])
ax_call = fig.add_subplot(gs[1, 2])

draw_pie(ax_pie, 3321, TOTAL_MODEL, "Conveyor", C_CONV)
draw_bar(ax_bar,
         ["Model\n(orchestrator)",
          "Measured\napparent",
          "Measured\nactive (cosφ=0.8)"],
         [3321, 20300, 16240],
         [C_MODEL, "#E0A04D", C_MEAS],
         "Energy per 30-s cycle (J)",
         "CONVEYOR — model vs measured",
         ylim=(0, 25000))
draw_callout(ax_call, C_CONV,
             ["[BOLD]CONVEYOR",
              "• Model:    3 321 J (110.7 W mean × 30 s)",
              "• Measured: ~16 kJ active",
              "             (843 VA × 0.8 PF × 30 s)",
              "• Gap:      ~5× under-prediction",
              "• Cause:    L_m locked 'fixed' in FMU",
              "             Rs insensitive at this op-point",
              "• Phase 2:  Unlock L_m, run LSQ Levenberg-",
              "             Marquardt on full motor set"])

# ============================================================
# ROW 2 — XY10
# ============================================================
ax_pie  = fig.add_subplot(gs[2, 0])
ax_bar  = fig.add_subplot(gs[2, 1])
ax_call = fig.add_subplot(gs[2, 2])

draw_pie(ax_pie, 19.9, TOTAL_MODEL, "XY10", C_XY10)
draw_bar(ax_bar,
         ["Model FMU\n(orchestrator)",
          "Standalone\n(xy10_clean)",
          "Measured\nburst (TDMS)"],
         [19.9, 12.4, 4922],
         [C_MODEL, "#5DADE2", C_MEAS],
         "Energy (J, log scale)",
         "XY10 — model vs measured",
         ylim=(1, 20000), logscale=True)
draw_callout(ax_call, C_XY10,
             ["[BOLD]XY10 STATION",
              "• Model FMU:   19.9 J / 30-s cycle (2 pick-place)",
              "• Standalone:  12.4 J / 12-s validation cycle",
              "• Measured:    4 922 J / 15-s TDMS burst",
              "• Gap:         400× under-prediction",
              "• Cause:       STRUCTURAL — DC-equivalent",
              "                omits stepper holding current",
              "                (±20 A chopper continuous draw)",
              "• Phase 2:     Add holding-current term to FMU,",
              "                then calibrate friction params"])

# ============================================================
# ROW 3 — CR5
# ============================================================
ax_pie  = fig.add_subplot(gs[3, 0])
ax_bar  = fig.add_subplot(gs[3, 1])
ax_call = fig.add_subplot(gs[3, 2])

draw_pie(ax_pie, 65.8, TOTAL_MODEL, "CR5", C_CR5)

# For CR5, replace the bar chart with mass-agreement comparison
# (no electrical measurement target available)
ax_bar.axis("on")
x = [0, 1]
bars = ax_bar.bar(["Model\n(CAD-derived)", "Brochure"],
                   [23.74, 25.0],
                   color=[C_MODEL, C_GOOD],
                   edgecolor=C_TEXT, lw=1.2, alpha=0.88, width=0.55)
for bar, v in zip(bars, [23.74, 25.0]):
    ax_bar.text(bar.get_x() + bar.get_width()/2, v + 0.4,
                f"{v} kg", ha="center", fontsize=10, fontweight="bold",
                color=C_TEXT)
ax_bar.set_ylabel("Total mass (kg)", fontsize=10)
ax_bar.set_ylim(0, 30)
ax_bar.set_title("CR5 — structural validation (mass)",
                  fontsize=11, fontweight="bold", color=C_TEXT)
ax_bar.grid(axis="y", alpha=0.3)
ax_bar.text(0.5, -0.18, "Agreement: 94.9 %",
             transform=ax_bar.transAxes, ha="center", fontsize=10,
             fontweight="bold", color=C_GOOD)

draw_callout(ax_call, C_CR5,
             ["[BOLD]CR5 COBOT",
              "• Model:     65.8 J / 5-s assembly cycle",
              "             (49 W peak)",
              "• Reference: Mass 23.74 kg vs 25 kg brochure",
              "             → 94.9 % agreement",
              "             (1.26 kg = cable harness + flange)",
              "• Measured:  No per-joint power available",
              "             on ALIX line",
              "• Status:    Structural validation only",
              "• Phase 2:   Instrument joint motors for",
              "             current/power calibration"])

# ============================================================
# FOOTER NOTE
# ============================================================
fig.text(0.5, 0.005,
         "TOTAL MODEL: 3 407 J per 30-s production cycle    "
         "|    Modelled subsystems cover 100 % of active mechatronic actuators    "
         "|    Phase 2 closes the remaining gaps with measurement + un-fixing L_m",
         ha="center", fontsize=10, style="italic", color="#5B6B7B")

plt.tight_layout(rect=[0, 0.01, 1, 0.97])
out_path = OUT_DIR / "energy_decomposition_diagram.png"
plt.savefig(out_path, dpi=200, bbox_inches="tight")
print(f"Saved: {out_path}")
plt.show()