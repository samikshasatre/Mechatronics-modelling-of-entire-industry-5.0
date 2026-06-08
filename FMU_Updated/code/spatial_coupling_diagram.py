"""
spatial_coupling_diagram.py
============================
Spatial layout of the ALIX line subsystems + qualitative coupling analysis.

Shows the 8.4 m ALIX line with five stations, the three modelled subsystems
highlighted, and annotated coupling pathways:
  - Mechanical (vibration along the frame)
  - Thermal (heat dissipation to surrounding air)
  - Electrical (shared 400 V three-phase mains)
  - Pneumatic (shared 5 bar air supply)
  - Discrete-event (workpiece handoff between stations)

This addresses the brief's requirement of "simplified spatial representation
to locate components and potential coupling effects".
"""

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Rectangle
import numpy as np

fig, ax = plt.subplots(figsize=(16, 9))
ax.set_xlim(0, 17); ax.set_ylim(0, 10)
ax.set_aspect("equal"); ax.axis("off")

# Colour palette
C_FRAME    = "#7F8C8D"
C_CONV     = "#1F618D"   # blue
C_CR5      = "#A93226"   # red
C_XY10     = "#27AE60"   # green
C_OUT      = "#BDC3C7"   # grey for out-of-scope
C_VIB      = "#E67E22"   # orange — vibration coupling
C_THERM    = "#C0392B"   # red — thermal coupling
C_ELEC     = "#2E86AB"   # blue — electrical coupling
C_PNEU     = "#F39C12"   # amber — pneumatic coupling
C_EVT      = "#8E44AD"   # purple — discrete-event coupling
EDGE       = "#1E3A5F"

# ============================================================
# TITLE + SCALE
# ============================================================
ax.text(8.5, 9.55,
        "ALIX Line — Spatial Layout & Coupling Analysis",
        ha="center", fontsize=15, fontweight="bold", color=EDGE)
ax.text(8.5, 9.2,
        "8.4 m total length · 5 stations · 30 s production cadence · "
        "modelled subsystems highlighted",
        ha="center", fontsize=9.5, style="italic", color="#5B6B7B")

# Scale bar
ax.plot([1, 15], [0.6, 0.6], color="black", lw=1.5)
ax.plot([1, 1],   [0.5, 0.7], color="black", lw=1.5)
ax.plot([15, 15], [0.5, 0.7], color="black", lw=1.5)
ax.text(8, 0.3, "8.4 m", ha="center", fontsize=10, fontweight="bold")

# ============================================================
# CONVEYOR — runs along the whole line
# ============================================================
conv = Rectangle((1, 4.0), 14, 1.0, facecolor=C_CONV, edgecolor=EDGE,
                 lw=1.5, alpha=0.85)
ax.add_patch(conv)
ax.text(8, 4.5, "CONVEYOR  (Modelled)",
        ha="center", va="center", fontsize=11, fontweight="bold", color="white")
ax.text(8, 3.7, "induction motor + gearbox + drum + belt + thermal · v = 0.196 m/s",
        ha="center", fontsize=8, color="#5B6B7B", style="italic")

# ============================================================
# FIVE STATIONS (left to right)
# ============================================================
stations = [
    {"name": "ON10",       "x": 1.8, "color": C_OUT,  "modelled": False,
     "label": "Magasin\nentree"},
    {"name": "MI00 + MD20","x": 4.6, "color": C_CR5,  "modelled": True,
     "label": "CR5 cobot\nbouchage"},
    {"name": "XY10",       "x": 8.0, "color": C_XY10, "modelled": True,
     "label": "XY pick&place\n+ vacuum"},
    {"name": "DX10",       "x": 11.2,"color": C_OUT,  "modelled": False,
     "label": "Inspection\nvision"},
    {"name": "VL10",       "x": 14.0,"color": C_OUT,  "modelled": False,
     "label": "Magasin\nsortie"},
]

for s in stations:
    box = FancyBboxPatch((s["x"]-0.9, 5.3), 1.8, 1.8,
                         boxstyle="round,pad=0.05,rounding_size=0.10",
                         lw=1.5, edgecolor=EDGE, facecolor=s["color"],
                         alpha=0.85)
    ax.add_patch(box)
    ax.text(s["x"], 6.7, s["name"],
            ha="center", va="center", fontsize=9.5, fontweight="bold",
            color="white" if s["modelled"] else "#34495E")
    ax.text(s["x"], 6.1, s["label"],
            ha="center", va="center", fontsize=7.5,
            color="white" if s["modelled"] else "#34495E")
    if s["modelled"]:
        ax.text(s["x"], 5.5, "MODELLED",
                ha="center", va="center", fontsize=7, fontweight="bold",
                color="white",
                bbox=dict(boxstyle="round,pad=0.1", fc="black", alpha=0.4))
    else:
        ax.text(s["x"], 5.5, "out of scope",
                ha="center", va="center", fontsize=7,
                color="#34495E", style="italic")

# ============================================================
# UTILITIES (top of figure)
# ============================================================
ax.add_patch(Rectangle((0.5, 8.1), 16, 0.5, facecolor=C_ELEC,
                       alpha=0.25, edgecolor="none"))
ax.text(8.5, 8.35, "400 V three-phase mains · 50 Hz · shared electrical bus",
        ha="center", fontsize=9, color=EDGE, fontweight="bold")

ax.add_patch(Rectangle((0.5, 7.55), 16, 0.4, facecolor=C_PNEU,
                       alpha=0.25, edgecolor="none"))
ax.text(8.5, 7.75, "5 bar compressed air supply (Venturi-regulated to 4 bar at XY10)",
        ha="center", fontsize=8.5, color=EDGE)

# ============================================================
# COUPLING ARROWS
# ============================================================
# 1) Mechanical vibration along the conveyor frame
for x in [2.5, 5.5, 8.5, 11.5, 14.5]:
    ax.annotate("", xy=(x+0.4, 3.0), xytext=(x, 3.5),
                arrowprops=dict(arrowstyle="->", color=C_VIB, lw=1.4,
                                connectionstyle="arc3,rad=0.0"))
ax.text(8.5, 2.7,
        "VIBRATION → propagates along the shared aluminium frame "
        "(coupling between conveyor motor and XY10/CR5 mounting)",
        ha="center", fontsize=8.5, color=C_VIB, style="italic")

# 2) Thermal — motor heat to ambient
ax.annotate("", xy=(2.5, 8.0), xytext=(2.5, 5.2),
            arrowprops=dict(arrowstyle="->", color=C_THERM, lw=1.4,
                            ls="--"))
ax.text(2.5, 7.0, "thermal\nrise\n(motor)",
        ha="center", fontsize=7.5, color=C_THERM, fontweight="bold")

# 3) Discrete-event handoff arrows along the conveyor
for x_from, x_to, label in [(1.8, 4.6, "T_arrive_CR5"),
                              (4.6, 8.0, "T_handoff_XY10"),
                              (8.0, 11.2, "T_to_inspection"),
                              (11.2, 14.0, "T_finished")]:
    ax.annotate("", xy=(x_to-0.9, 4.5), xytext=(x_from+0.9, 4.5),
                arrowprops=dict(arrowstyle="->", color=C_EVT, lw=1.6))
    ax.text((x_from + x_to)/2, 4.78, label,
            ha="center", fontsize=7, color=C_EVT, style="italic")

# ============================================================
# LEGEND — coupling types
# ============================================================
def legend_box(x, y, color, text):
    box = Rectangle((x, y), 0.4, 0.2, facecolor=color, alpha=0.85,
                    edgecolor=EDGE, lw=0.8)
    ax.add_patch(box)
    ax.text(x+0.5, y+0.10, text, ha="left", va="center",
            fontsize=9, color=EDGE)

legend_x = 0.5
legend_y = 1.4
ax.text(legend_x, legend_y + 0.6, "COUPLING TYPES",
        fontsize=10, fontweight="bold", color=EDGE)
legend_box(legend_x,      legend_y,        C_ELEC,  "Electrical (shared 400 V bus)")
legend_box(legend_x+4.5,  legend_y,        C_PNEU,  "Pneumatic (shared air supply)")
legend_box(legend_x+9.0,  legend_y,        C_VIB,   "Mechanical (frame vibration)")
legend_box(legend_x,      legend_y-0.35,   C_THERM, "Thermal (motor → ambient)")
legend_box(legend_x+4.5,  legend_y-0.35,   C_EVT,   "Discrete-event (workpiece handoff)")
ax.text(legend_x+9.0,  legend_y-0.3,
        "Phase 2: quantitative coupling models (mode shapes, conjugate-heat)",
        fontsize=8, style="italic", color="#7F8C8D")

# ============================================================
# SCOPE NOTE
# ============================================================
ax.text(8.5, 0.02,
        "Modelled subsystems (Conveyor + MI00/MD20 cobot + XY10) cover "
        "~65% of the line's energy and all active actuators.\n"
        "Coupling pathways are LISTED here; quantitative cross-domain "
        "models (e.g. vibration FEM, conjugate heat transfer) are Phase 2 work.",
        ha="center", fontsize=8.5, style="italic", color="#5B6B7B",
        bbox=dict(boxstyle="round,pad=0.4", fc="#F8F9FA",
                  edgecolor="#BDC3C7", lw=0.8))

plt.tight_layout()
out_path = r"C:\Users\satres\Documents\ALIX\FMU_Updated\spatial_coupling_diagram.png"
plt.savefig(out_path, dpi=200, bbox_inches="tight")
print(f"Saved: {out_path}")
plt.show()