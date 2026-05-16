
import os
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

HERE = os.path.dirname(os.path.abspath(__file__))

# =====================================================================
# COLOR PALETTE
# =====================================================================
COLOR_MULTIPHYSICS = "#27ae60"   # green
COLOR_LOGICAL      = "#f39c12"   # orange/yellow
COLOR_NOT_MODELED  = "#e74c3c"   # red

# =====================================================================
# DATA — 6 machines of the ALIX line
# =====================================================================
# Each station: code, name (FR), function (EN), modelling status, color
stations = [
    {
        "code": "ON10",
        "name": "Dévracage 2D",
        "function": "Bulk picking with\n6-axis cobot + vision\n(TM5-900)",
        "status": "Not modeled",
        "color": COLOR_NOT_MODELED,
        "x": 0,
    },
    {
        "code": "DX10",
        "name": "Dosaxe",
        "function": "Pot filling with\ngranule dosing\n(brushless axis)",
        "status": "Not modeled",
        "color": COLOR_NOT_MODELED,
        "x": 1,
    },
    {
        "code": "MI00+MR10",
        "name": "Cobot bouchage",
        "function": "Capping with\nDobot CR5\n6-axis cobot",
        "status": "Not modeled",
        "color": COLOR_NOT_MODELED,
        "x": 2,
    },
    {
        "code": "XY10",
        "name": "Robot cartésien XYZ",
        "function": "Packaging into trays\n3-axis Cartesian\n+ vacuum gripper",
        "status": "MULTIPHYSICS\nMODELED",
        "color": COLOR_MULTIPHYSICS,
        "x": 3,
    },
    {
        "code": "VL10",
        "name": "Magasin vertical",
        "function": "Vertical storage\nand destocking\nof finished products",
        "status": "Not modeled",
        "color": COLOR_NOT_MODELED,
        "x": 4,
    },
    {
        "code": "AG10",
        "name": "AGV + UR5",
        "function": "Mobile robot\nMiR100 + UR5e\n(off-line transport)",
        "status": "Not modeled",
        "color": COLOR_NOT_MODELED,
        "x": 5.3,  # offset, off-line not part of inline flow
    },
]

# =====================================================================
# DATA — Subsystems INSIDE the XY10 station (which is what we modeled)
# =====================================================================
xy10_subsystems = [
    {
        "name": "Conveyor",
        "details": "Induction motor (TIA56-2)\n+ gearbox + drum + belt\n+ VFD speed control",
        "status": "MULTIPHYSICS",
        "color": COLOR_MULTIPHYSICS,
        "x": 0,
    },
    {
        "name": "3-axis Cartesian",
        "details": "X, Y, Z steppers\nlead-screw transmission\n+ incremental encoders",
        "status": "MULTIPHYSICS",
        "color": COLOR_MULTIPHYSICS,
        "x": 1,
    },
    {
        "name": "Vacuum gripper",
        "details": "Venturi ejector\nfirst-order chamber\n+ threshold attachment",
        "status": "MULTIPHYSICS",
        "color": COLOR_MULTIPHYSICS,
        "x": 2,
    },
    {
        "name": "Pneumatic cylinders",
        "details": "Separator, indexer,\nblocker, depiler\n(generic model)",
        "status": "MULTIPHYSICS",
        "color": COLOR_MULTIPHYSICS,
        "x": 3,
    },
    {
        "name": "Sensors + PLC",
        "details": "SICK photoelectric\n+ Siemens S7-1200\nstate machine emulation",
        "status": "Logical Python",
        "color": COLOR_LOGICAL,
        "x": 4,
    },
]


def main():
    # Make the figure
    fig = plt.figure(figsize=(16, 10))
    fig.suptitle("ALIX line — scope map (Conditionnement mode)\n"
                 "Which machines are modeled, which are not",
                 fontsize=15, weight="bold", y=0.97)

    # =================================================================
    # TOP HALF — Line-level view (all 6 ALIX machines)
    # =================================================================
    ax_top = fig.add_axes([0.05, 0.55, 0.9, 0.35])
    ax_top.set_xlim(-0.5, 6.5)
    ax_top.set_ylim(0, 2.7)
    ax_top.axis("off")
    ax_top.set_title("Line-level view — 6 machines in the ALIX line",
                     fontsize=12, weight="bold", loc="left", pad=10)

    # Draw flow arrows between inline stations (ON10 → DX10 → MI00 → XY10 → VL10)
    for i in range(4):
        arrow = FancyArrowPatch(
            (i + 0.42, 1.25), (i + 1 - 0.42, 1.25),
            arrowstyle="->", mutation_scale=20, lw=2, color="dimgray"
        )
        ax_top.add_patch(arrow)

    # Draw each station as a colored box
    for st in stations:
        box = FancyBboxPatch(
            (st["x"] - 0.4, 0.5), 0.8, 1.5,
            boxstyle="round,pad=0.05", lw=2,
            edgecolor="black", facecolor=st["color"], alpha=0.75
        )
        ax_top.add_patch(box)
        # Code (large, top of box)
        ax_top.text(st["x"], 1.85, st["code"],
                    ha="center", va="center", fontsize=11, weight="bold")
        # Name (italic)
        ax_top.text(st["x"], 1.55, st["name"],
                    ha="center", va="center", fontsize=8, style="italic")
        # Function (multi-line description)
        ax_top.text(st["x"], 1.05, st["function"],
                    ha="center", va="center", fontsize=7)
        # Status badge (white text on dark background)
        ax_top.text(st["x"], 0.65, st["status"],
                    ha="center", va="center", fontsize=7,
                    weight="bold", color="white",
                    bbox=dict(facecolor="black", alpha=0.7,
                              boxstyle="round,pad=0.2"))

    # AG10 has a clarifier label below
    ax_top.text(5.3, 0.25, "(off-line / mobile)",
                ha="center", fontsize=8, style="italic", color="dimgray")

    # Flow direction note above
    ax_top.text(2, 2.45,
                "Flow direction (Conditionnement mode):  pots → bulked → filled → capped → packaged → stored",
                ha="center", fontsize=9.5, color="dimgray", style="italic")

    # =================================================================
    # BOTTOM HALF — Zoom on XY10 (what we modeled)
    # =================================================================
    ax_bot = fig.add_axes([0.05, 0.10, 0.9, 0.35])
    ax_bot.set_xlim(-0.5, 5)
    ax_bot.set_ylim(0, 2.5)
    ax_bot.axis("off")
    ax_bot.set_title("Zoom on XY10 station — subsystems modeled "
                     "(multiphysics in green, logical in orange)",
                     fontsize=12, weight="bold", loc="left", pad=10)

    for sub in xy10_subsystems:
        box = FancyBboxPatch(
            (sub["x"] - 0.4, 0.5), 0.8, 1.5,
            boxstyle="round,pad=0.05", lw=2,
            edgecolor="black", facecolor=sub["color"], alpha=0.75
        )
        ax_bot.add_patch(box)
        # Subsystem name (large)
        ax_bot.text(sub["x"], 1.8, sub["name"],
                    ha="center", va="center", fontsize=10, weight="bold")
        # Technical details
        ax_bot.text(sub["x"], 1.15, sub["details"],
                    ha="center", va="center", fontsize=7)
        # Status badge
        ax_bot.text(sub["x"], 0.65, sub["status"],
                    ha="center", va="center", fontsize=7,
                    weight="bold", color="white",
                    bbox=dict(facecolor="black", alpha=0.7,
                              boxstyle="round,pad=0.2"))

    # =================================================================
    # LEGEND (centered at the bottom)
    # =================================================================
    legend_elements = [
        mpatches.Patch(facecolor=COLOR_MULTIPHYSICS, alpha=0.75, edgecolor="black",
                       label="Multiphysics Modelica model + FMU "
                             "(exported via FMI 2.0 Co-Simulation)"),
        mpatches.Patch(facecolor=COLOR_LOGICAL, alpha=0.75, edgecolor="black",
                       label="Logical Python model "
                             "(sensors, PLC state machine)"),
        mpatches.Patch(facecolor=COLOR_NOT_MODELED, alpha=0.75, edgecolor="black",
                       label="Not modeled "
                             "(out of internship scope)"),
    ]
    fig.legend(handles=legend_elements, loc="lower center",
               bbox_to_anchor=(0.5, 0.02), ncol=3, fontsize=10,
               frameon=True, fancybox=True, edgecolor="gray")

    # =================================================================
    # Save and show
    # =================================================================
    out_dir = os.path.join(HERE, "..", "documentation", "figures")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "fig_00_alix_scope_map.png")
    plt.savefig(out_path, dpi=140, bbox_inches="tight", facecolor="white")
    print(f"Scope map saved: {out_path}")

    # Also save to the results folder for easier finding
    results_dir = os.path.join(HERE, "results")
    os.makedirs(results_dir, exist_ok=True)
    out_path2 = os.path.join(results_dir, "scope_map.png")
    plt.savefig(out_path2, dpi=140, bbox_inches="tight", facecolor="white")
    print(f"Scope map also saved: {out_path2}")

    plt.show()


if __name__ == "__main__":
    main()