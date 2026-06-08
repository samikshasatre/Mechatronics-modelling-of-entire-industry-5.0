"""
stage_ab_diagram.py
====================
Clarifying diagram: Stage A vs Stage B validation.

Stage A: FMU output vs real TDMS measurement
         (physics question: does the model match the world?)
Stage B: FMU output vs Dymola native simulation
         (engineering question: did the export stay faithful?)
"""

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

C_REAL    = "#E07B47"
C_MODEL   = "#2E75B6"
C_COMPARE = "#1E3A5F"
EDGE      = "#1E3A5F"
ARR       = "#5B6B7B"

fig, (ax_a, ax_b) = plt.subplots(2, 1, figsize=(14, 11))

def block(ax, x, y, w, h, label, fill, sub=None, fs=10):
    box = FancyBboxPatch((x, y), w, h,
                         boxstyle="round,pad=0.05,rounding_size=0.12",
                         linewidth=1.2, edgecolor=EDGE, facecolor=fill)
    ax.add_patch(box)
    ax.text(x + w/2, y + h/2 + (0.15 if sub else 0), label,
            ha="center", va="center", fontsize=fs, fontweight="bold",
            color="white" if fill == C_COMPARE else EDGE)
    if sub:
        ax.text(x + w/2, y + h/2 - 0.25, sub, ha="center", va="center",
                fontsize=8.5, style="italic",
                color="white" if fill == C_COMPARE else "#5B6B7B")

def arrow(ax, x1, y1, x2, y2, color=ARR, lw=1.6):
    a = FancyArrowPatch((x1, y1), (x2, y2),
                        arrowstyle="-|>", mutation_scale=18,
                        linewidth=lw, color=color, shrinkA=2, shrinkB=2)
    ax.add_patch(a)

# =========================================================
# STAGE A
# =========================================================
ax_a.set_xlim(0, 14); ax_a.set_ylim(0, 7)
ax_a.set_aspect("equal"); ax_a.axis("off")
ax_a.text(7, 6.7,
          "STAGE A - Does the model match the REAL WORLD?",
          ha="center", fontsize=15, fontweight="bold", color=C_COMPARE)
ax_a.text(7, 6.25,
          "Scientific question: physics accuracy",
          ha="center", fontsize=10, style="italic", color="#5B6B7B")

# Real-world chain (left)
block(ax_a, 0.3, 4.8, 2.6, 0.8, "ALIX line", C_REAL, "running production")
arrow(ax_a, 1.6, 4.8, 1.6, 4.4)
block(ax_a, 0.3, 3.6, 2.6, 0.8, "NI DAQ system", C_REAL, "6 kHz, 6 channels")
arrow(ax_a, 1.6, 3.6, 1.6, 3.2)
block(ax_a, 0.3, 2.4, 2.6, 0.8, "TDMS files", C_REAL,
      "first.tdms / four.tdms")
arrow(ax_a, 1.6, 2.4, 1.6, 2.0)
block(ax_a, 0.3, 1.2, 2.6, 0.8, "Signal pipeline", C_REAL,
      "gains, RMS, alignment")
arrow(ax_a, 2.9, 1.6, 5.3, 1.6, lw=2.0)

# Model chain (right)
block(ax_a, 11.1, 4.8, 2.6, 0.8, "Dymola model", C_MODEL,
      "Modelica source code")
arrow(ax_a, 12.4, 4.8, 12.4, 4.4)
block(ax_a, 11.1, 3.6, 2.6, 0.8, "Export FMU", C_MODEL, "FMI 2.0 Co-Sim")
arrow(ax_a, 12.4, 3.6, 12.4, 3.2)
block(ax_a, 11.1, 2.4, 2.6, 0.8, "Python run", C_MODEL, "fmpy library")
arrow(ax_a, 12.4, 2.4, 12.4, 2.0)
block(ax_a, 11.1, 1.2, 2.6, 0.8, "Model output", C_MODEL,
      "same time grid")
arrow(ax_a, 11.1, 1.6, 8.7, 1.6, lw=2.0)

# Compare box
block(ax_a, 5.4, 1.0, 3.3, 1.2, "COMPARE", C_COMPARE,
      "R-squared, NRMSE, MAE,\nFIT %, peak ratio, phase lag",
      fs=13)
arrow(ax_a, 7.0, 1.0, 7.0, 0.5, color=C_COMPARE, lw=2.0)
ax_a.text(7.0, 0.2,
          "STAGE A RESULT: current R-squared = 0.91 phase-aligned, "
          "thermal FIT = 91 %, voltage FIT = 96 %",
          ha="center", fontsize=10, fontweight="bold", color=C_COMPARE)

# =========================================================
# STAGE B
# =========================================================
ax_b.set_xlim(0, 14); ax_b.set_ylim(0, 7)
ax_b.set_aspect("equal"); ax_b.axis("off")
ax_b.text(7, 6.7,
          "STAGE B - Did the FMU export stay FAITHFUL to Dymola?",
          ha="center", fontsize=15, fontweight="bold", color=C_COMPARE)
ax_b.text(7, 6.25,
          "Engineering question: software / toolchain fidelity",
          ha="center", fontsize=10, style="italic", color="#5B6B7B")

# Single source on top
block(ax_b, 5.4, 5.0, 3.3, 0.8, "Dymola model", C_MODEL,
      "ONE source of truth")
arrow(ax_b, 6.0, 5.0, 2.6, 4.0)
arrow(ax_b, 8.1, 5.0, 11.4, 4.0)

# Two paths
block(ax_b, 1.3, 3.2, 2.6, 0.8, "Run in Dymola", C_MODEL,
      "native simulation")
block(ax_b, 10.1, 3.2, 2.6, 0.8, "Export + run FMU", C_MODEL,
      "Python via fmpy")

arrow(ax_b, 2.6, 3.2, 2.6, 2.5)
arrow(ax_b, 11.4, 3.2, 11.4, 2.5)

# Outputs
block(ax_b, 1.3, 1.7, 2.6, 0.8, "Dymola output", C_MODEL,
      "T, P, current")
block(ax_b, 10.1, 1.7, 2.6, 0.8, "FMU output", C_MODEL,
      "T, P, current")
arrow(ax_b, 3.9, 2.1, 5.4, 1.7)
arrow(ax_b, 10.1, 2.1, 8.6, 1.7)

# Compare box
block(ax_b, 5.4, 1.0, 3.3, 1.0, "COMPARE", C_COMPARE,
      "every signal, every sample", fs=13)
arrow(ax_b, 7.0, 1.0, 7.0, 0.5, color=C_COMPARE, lw=2.0)
ax_b.text(7.0, 0.2,
          "STAGE B RESULT: < 0.01 % per-signal error - "
          "FMU export is essentially lossless",
          ha="center", fontsize=10, fontweight="bold", color=C_COMPARE)

# Right side insight box
fig.text(0.99, 0.5,
         "KEY INSIGHT\n\n"
         "Stage A has TWO sources\n(real line + model)\n"
         "-> tests physics\n\n"
         "Stage B has ONE source\n(Dymola only, two ways\nto run it)\n"
         "-> tests software\n\n"
         "Stage B near-zero error\n-> Stage A gap is REAL physics,\n"
         "not a software artefact",
         ha="right", va="center", fontsize=9, color=C_COMPARE,
         bbox=dict(boxstyle="round,pad=0.5",
                   facecolor="#F2F4F7", edgecolor=C_COMPARE, lw=1.2))

plt.tight_layout()
out_path = r"C:\Users\satres\Documents\ALIX\FMU_Updated\stage_ab_diagram.png"
plt.savefig(out_path, dpi=200, bbox_inches="tight")
print(f"Saved: {out_path}")
plt.show()