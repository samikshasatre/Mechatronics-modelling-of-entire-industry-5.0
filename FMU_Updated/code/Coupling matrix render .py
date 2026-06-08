"""
coupling_matrix_render.py
Render the ALIX/ERMASMART coupling matrix as a clean PNG figure.
25 coupling pairs across 8 subsystems.
"""
import os
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import Rectangle, FancyBboxPatch

HERE = os.path.dirname(os.path.abspath(__file__))

# Severity color scheme
SEV_COLORS = {
    "Strong":   "#E06C5C",  # red
    "Moderate": "#F2B96A",  # amber
    "Weak":     "#F4E18C",  # pale yellow
}

# Modelled status color scheme
MOD_COLORS = {
    "Yes (FMU)":             "#7FC97F",  # green
    "Yes (v3)":              "#7FC97F",
    "Partial (DC-eq)":       "#BFD6A8",  # light green
    "Implicit":              "#BFD6A8",
    "Implicit (orch.)":      "#BFD6A8",
    "Lumped":                "#FFF5C2",  # pale yellow (modeled but lumped)
    "No":                    "#D9D9D9",  # gray
    "No (baseline)":         "#D9D9D9",
    "No (scope)":            "#D9D9D9",
}

# Type colors (small badge)
TYPE_COLORS = {
    "EL":     "#5B9BD5",  # blue
    "MEC":    "#A0A0A0",  # gray
    "TH":     "#C00000",  # red
    "EMI":    "#B45F06",  # orange
    "PF":     "#2E7D32",  # green
    "EL+MEC": "#7E63B5",  # purple
}

# ==================================================================
# DATA - 25 coupling rows
# ==================================================================
ROWS = [
    # (#, Pair, Type, Severity, Modelled, Physical basis)
    (1,  "Supply ↔ Cabinet",                       "EL",     "Strong",   "Implicit",
     "3-phase 244 V / 50 Hz supply enters the cabinet; central distribution + protection."),
    (2,  "Cabinet ↔ Conv Motor",                   "EL",     "Strong",   "Yes (FMU)",
     "Direct connection through VFD; primary electrical pathway driving the conveyor."),
    (3,  "Cabinet ↔ XY10 drives",                  "EL",     "Strong",   "Partial (DC-eq)",
     "Direct connection to stepper drivers; chopper current ±20 A in four.tdms."),
    (4,  "Cabinet ↔ Sensors",                      "EL",     "Moderate", "No (baseline)",
     "24 V DC bus from supply via SMPS in cabinet; common ground reference."),
    (5,  "Cabinet ↔ Pneumatic",                    "EL",     "Moderate", "No (baseline)",
     "Solenoid valve control + vacuum pump motor supply from cabinet."),
    (6,  "Conv Motor ↔ Motor body",                "TH",     "Strong",   "Yes (v3)",
     "Motor losses ~107 W deposit heat into motor body lumped mass C = 500 J/K."),
    (7,  "Motor body ↔ Ambient",                   "TH",     "Moderate", "Yes (v3)",
     "Natural convection to 20 °C ambient through G = 1.5 W/K; τ = 333 s."),
    (8,  "Conv Motor ↔ Conv Frame",                "TH",     "Weak",     "Lumped",
     "Conduction through motor mount into frame; lumped into single G in current model."),
    (9,  "Conv Frame ↔ CR5 base",                  "TH",     "Weak",     "No",
     "Heat propagation through shared bench chassis to CR5 base; not measured."),
    (10, "Conv Frame ↔ XY10 base",                 "TH",     "Weak",     "No",
     "Same mechanism as Row 9; not measured."),
    (11, "CR5 ↔ Ambient",                          "TH",     "Weak",     "No",
     "Joint motor losses ~10–20 W estimated; intermittent duty cycle."),
    (12, "XY10 steppers ↔ Ambient",                "TH",     "Weak",     "No",
     "Stepper drives + motors dissipate heat; bursts only."),
    (13, "Conv Motor ↔ Conv Frame",                "MEC",    "Moderate", "No",
     "50 Hz vibration from motor rotation transmitted to mounting bracket and frame."),
    (14, "Conv Belt ↔ Conv Frame",                 "MEC",    "Weak",     "No",
     "Belt rotation at drum frequency ~1.2 Hz at operating speed; low-frequency vibration."),
    (15, "Conv Frame ↔ CR5 base",                  "MEC",    "Weak",     "No",
     "Vibration from conveyor propagates through shared chassis to CR5 base."),
    (16, "Conv Frame ↔ XY10 base",                 "MEC",    "Weak",     "No",
     "Same mechanism; chassis-borne vibration to XY10 mounting."),
    (17, "CR5 ↔ Conv Frame",                       "MEC",    "Moderate", "No",
     "Cobot inertial reactions during fast moves transmit through MI00 mounting to frame."),
    (18, "XY10 steppers ↔ XY10 chassis",           "MEC",    "Weak",     "No",
     "Stepper acceleration bursts cause structural vibration; localised to XY10 frame."),
    (19, "Cabinet ↔ Sensor cables",                "EMI",    "Moderate", "No (scope)",
     "Drive lines and sensor cables share cabinet wiring trays; PWM coupling."),
    (20, "Motor cable ↔ Sensor cables",            "EMI",    "Moderate", "No (scope)",
     "PWM inverter current creates EM emissions; coupling depends on routing and shielding."),
    (21, "XY10 stepper cables ↔ XY10 sensors",     "EMI",    "Strong",   "No (scope)",
     "Chopper switching at several kHz creates strong nearby EMI; mitigated by shielding."),
    (22, "Conv Belt ↔ CR5",                        "PF",     "Strong",   "Implicit (orch.)",
     "Pots travel on conveyor through CR5 capping station; central part-flow path."),
    (23, "Conv Belt ↔ XY10",                       "PF",     "Strong",   "Implicit (orch.)",
     "Capped pots travel from CR5 zone through XY10 packing station."),
    (24, "Pneumatic ↔ XY10 gripper",               "EL+MEC", "Strong",   "Yes (FMU)",
     "Vacuum supply mechanically and electrically coupled to XY10 gripper."),
    (25, "Sensors ↔ Cabinet (signal return)",      "EL",     "Moderate", "Implicit",
     "Sensor outputs return to S7-1200 PLC inputs; signal-level coupling."),
]

# ==================================================================
# RENDER
# ==================================================================
n_rows = len(ROWS)
# Column widths (relative, sum = 1.0)
COL_WIDTHS = [0.035, 0.18, 0.070, 0.085, 0.130, 0.500]   # #, Pair, Type, Sev, Mod, Basis
COL_HEADERS = ["#", "Pair", "Type", "Severity", "Modelled?", "Physical basis"]

fig_h = max(8.5, 0.32 * n_rows + 2.6)   # height grows with rows
fig_w = 14.0

fig, ax = plt.subplots(figsize=(fig_w, fig_h))
ax.set_xlim(0, 1)
ax.set_ylim(0, 1)
ax.axis("off")

# Title
fig.suptitle(
    "ALIX / ERMASMART Coupling Matrix — Inter-Subsystem Physical Interactions",
    fontsize=15, weight="bold", y=0.985,
)
ax.text(
    0.5, 1.02,
    "Subsystems: Supply | Cabinet | Conv Motor | Conv Frame | CR5 | XY10 | Pneumatic | Sensors",
    transform=ax.transAxes, ha="center", va="bottom",
    fontsize=10, style="italic", color="#555555",
)

# Layout positions
TOP_Y      = 0.94
ROW_H      = (TOP_Y - 0.08) / (n_rows + 1)   # +1 for header row
HEADER_Y   = TOP_Y - ROW_H

# Compute column x-positions
col_x_starts = [0.0]
for w in COL_WIDTHS[:-1]:
    col_x_starts.append(col_x_starts[-1] + w)

# Header row
for ci, (cx, cw, header) in enumerate(zip(col_x_starts, COL_WIDTHS, COL_HEADERS)):
    ax.add_patch(Rectangle(
        (cx, HEADER_Y), cw, ROW_H,
        facecolor="#1F4E78", edgecolor="black", lw=0.6
    ))
    ax.text(
        cx + cw/2, HEADER_Y + ROW_H/2,
        header, ha="center", va="center",
        fontsize=10, fontweight="bold", color="white"
    )

# Data rows
for ri, (num, pair, typ, sev, mod, basis) in enumerate(ROWS):
    y = HEADER_Y - (ri + 1) * ROW_H

    # Alternating row band
    band_color = "#F7F7F7" if (ri % 2 == 0) else "#FFFFFF"
    ax.add_patch(Rectangle(
        (0, y), 1.0, ROW_H,
        facecolor=band_color, edgecolor="none"
    ))

    # Cells with borders
    for ci, cw in enumerate(COL_WIDTHS):
        cx = col_x_starts[ci]
        ax.add_patch(Rectangle(
            (cx, y), cw, ROW_H,
            facecolor="none", edgecolor="#BBBBBB", lw=0.4
        ))

    # Column 0: row number
    ax.text(col_x_starts[0] + COL_WIDTHS[0]/2, y + ROW_H/2,
            str(num), ha="center", va="center", fontsize=9, color="#555555")

    # Column 1: pair
    ax.text(col_x_starts[1] + 0.008, y + ROW_H/2,
            pair, ha="left", va="center", fontsize=9.5)

    # Column 2: Type badge
    type_color = TYPE_COLORS.get(typ, "#999999")
    badge_pad = 0.005
    bx = col_x_starts[2] + badge_pad
    bw = COL_WIDTHS[2] - 2*badge_pad
    bh = ROW_H * 0.6
    by = y + (ROW_H - bh) / 2
    ax.add_patch(FancyBboxPatch(
        (bx, by), bw, bh,
        boxstyle="round,pad=0.005,rounding_size=0.008",
        facecolor=type_color, edgecolor="none"
    ))
    ax.text(bx + bw/2, by + bh/2,
            typ, ha="center", va="center",
            fontsize=8.5, fontweight="bold", color="white")

    # Column 3: Severity (full-cell color band)
    sev_color = SEV_COLORS.get(sev, "#FFFFFF")
    sx = col_x_starts[3] + 0.005
    sw = COL_WIDTHS[3] - 0.010
    sh = ROW_H * 0.7
    sy = y + (ROW_H - sh) / 2
    ax.add_patch(FancyBboxPatch(
        (sx, sy), sw, sh,
        boxstyle="round,pad=0.003,rounding_size=0.006",
        facecolor=sev_color, edgecolor="#888888", lw=0.4
    ))
    ax.text(sx + sw/2, sy + sh/2,
            sev, ha="center", va="center",
            fontsize=9, fontweight="bold", color="#222222")

    # Column 4: Modelled (full-cell color band)
    mod_color = MOD_COLORS.get(mod, "#D9D9D9")
    mx = col_x_starts[4] + 0.005
    mw = COL_WIDTHS[4] - 0.010
    mh = ROW_H * 0.7
    my_ = y + (ROW_H - mh) / 2
    ax.add_patch(FancyBboxPatch(
        (mx, my_), mw, mh,
        boxstyle="round,pad=0.003,rounding_size=0.006",
        facecolor=mod_color, edgecolor="#888888", lw=0.4
    ))
    ax.text(mx + mw/2, my_ + mh/2,
            mod, ha="center", va="center",
            fontsize=8.5, color="#222222")

    # Column 5: Physical basis (left-aligned, smaller)
    ax.text(col_x_starts[5] + 0.008, y + ROW_H/2,
            basis, ha="left", va="center", fontsize=8.5,
            color="#222222", wrap=True)

# Legend at the bottom — 3 clean rows
LEG_TYPE_Y = 0.058
LEG_SEV_Y  = 0.034
LEG_MOD_Y  = 0.010

# Row 1: Types
ax.text(0.005, LEG_TYPE_Y, "Type:", fontsize=9.5, fontweight="bold",
        transform=ax.transAxes, va="center")
type_x = 0.075
for typ, col in [("EL", "Electrical"), ("MEC", "Mechanical"),
                  ("TH", "Thermal"), ("EMI", "EM Interference"),
                  ("PF", "Part flow"), ("EL+MEC", "Combined")]:
    ax.add_patch(FancyBboxPatch(
        (type_x, LEG_TYPE_Y - 0.011), 0.030, 0.022,
        boxstyle="round,pad=0.002,rounding_size=0.005",
        facecolor=TYPE_COLORS.get(typ), edgecolor="none",
        transform=ax.transAxes
    ))
    ax.text(type_x + 0.015, LEG_TYPE_Y, typ,
            ha="center", va="center", fontsize=8, fontweight="bold",
            color="white", transform=ax.transAxes)
    ax.text(type_x + 0.035, LEG_TYPE_Y, col,
            ha="left", va="center", fontsize=8.5, transform=ax.transAxes)
    type_x += 0.155

ax.text(0.005, LEG_SEV_Y, "Severity:", fontsize=9.5, fontweight="bold",
        transform=ax.transAxes, va="center")
sev_x = 0.075
for sev in ["Strong", "Moderate", "Weak"]:
    ax.add_patch(FancyBboxPatch(
        (sev_x, LEG_SEV_Y - 0.011), 0.060, 0.022,
        boxstyle="round,pad=0.002,rounding_size=0.005",
        facecolor=SEV_COLORS[sev], edgecolor="#888888", lw=0.4,
        transform=ax.transAxes
    ))
    ax.text(sev_x + 0.030, LEG_SEV_Y, sev,
            ha="center", va="center", fontsize=8.5, fontweight="bold",
            transform=ax.transAxes)
    sev_x += 0.110

# Row 3: Modelled?
ax.text(0.005, LEG_MOD_Y, "Modelled?", fontsize=9.5, fontweight="bold",
        transform=ax.transAxes, va="center")
mod_x = 0.075
for mod, label in [("Yes (FMU)", "Explicit FMU"),
                    ("Implicit", "Implicit / orchestration"),
                    ("Lumped", "Lumped"),
                    ("No", "Not modelled")]:
    ax.add_patch(FancyBboxPatch(
        (mod_x, LEG_MOD_Y - 0.011), 0.030, 0.022,
        boxstyle="round,pad=0.002,rounding_size=0.005",
        facecolor=MOD_COLORS[mod], edgecolor="#888888", lw=0.4,
        transform=ax.transAxes
    ))
    ax.text(mod_x + 0.035, LEG_MOD_Y, label,
            ha="left", va="center", fontsize=8.5, transform=ax.transAxes)
    mod_x += 0.205


plt.tight_layout(rect=[0, 0.08, 1, 0.965])

out_path = os.path.join(HERE, "coupling_matrix.png")
plt.savefig(out_path, dpi=140, bbox_inches="tight", facecolor="white")
print(f"Figure saved: {out_path}")
plt.show()