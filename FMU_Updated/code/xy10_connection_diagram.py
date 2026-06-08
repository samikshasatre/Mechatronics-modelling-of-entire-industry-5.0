"""
xy10_connection_diagram.py
Architecture diagram for the XY10Station_v2 Modelica model.
Every block corresponds directly to an equation or parameter in the source.

Run:  python xy10_connection_diagram.py
Output: xy10_connection_diagram.png  (300 dpi, slide-ready)
"""

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

# ----- Colour palette (matches Modelica convention + your deck) -----
C_SIGNAL = "#E8ECF0"
C_ELEC   = "#CDE3F5"
C_MECH   = "#D7E9CB"
C_PNEU   = "#FFE0B2"
C_BOOL   = "#F4D7C8"
C_OUT    = "#F5F5F5"
EDGE     = "#1E3A5F"
ARR_SIG  = "#5B6B7B"
ARR_PHYS = "#1E3A5F"
ARR_PNEU = "#E67E22"

fig, ax = plt.subplots(figsize=(17, 10))
ax.set_xlim(0, 17)
ax.set_ylim(0, 10)
ax.set_aspect("equal"); ax.axis("off")

# ---------- Title ----------
ax.text(8.5, 9.55,
        "XY10Station_v2 — Modelica Architecture Diagram",
        ha="center", va="center", fontsize=16, fontweight="bold", color=EDGE)
ax.text(8.5, 9.18,
        "Equation-based multiphysics model · 3 mechanical-electrical axes (X, Y, Z) + pneumatic vacuum branch",
        ha="center", va="center", fontsize=10, style="italic", color="#5B6B7B")

def block(x, y, w, h, label, fill, sub=None, fs=9.0):
    box = FancyBboxPatch((x, y), w, h,
                         boxstyle="round,pad=0.04,rounding_size=0.10",
                         linewidth=1.0, edgecolor=EDGE, facecolor=fill)
    ax.add_patch(box)
    ax.text(x + w/2, y + h/2 + (0.13 if sub else 0), label,
            ha="center", va="center", fontsize=fs, fontweight="bold", color=EDGE)
    if sub:
        ax.text(x + w/2, y + h/2 - 0.20, sub,
                ha="center", va="center", fontsize=7.5, style="italic", color="#5B6B7B")
    return (x, y, w, h)

def arrow(x1, y1, x2, y2, color=ARR_SIG, lw=1.2):
    a = FancyArrowPatch((x1, y1), (x2, y2),
                        arrowstyle="-|>", mutation_scale=13,
                        linewidth=lw, color=color, shrinkA=2, shrinkB=2)
    ax.add_patch(a)

def line(x1, y1, x2, y2, color=ARR_SIG, lw=1.2):
    ax.plot([x1, x2], [y1, y2], color=color, lw=lw, solid_capstyle="round")


# ============================================================
#  ONE-AXIS TEMPLATE (drawn for X axis; Y and Z identical structure)
#  Layout: vertical bands from left to right
# ============================================================

# ---- INPUT (left edge) ----
inp_y = 7.0
b_cmd = block(0.3, inp_y, 1.6, 0.9, "x_cmd", C_SIGNAL, "RealInput  (m)")

# ---- PD CONTROLLER ----
b_pd = block(2.4, inp_y, 2.1, 0.9, "PD controller",
             C_SIGNAL, "Kp·(x_cmd−xp) − Kd·xv")

# ---- VOLTAGE SATURATION ----
b_sat = block(5.0, inp_y, 1.8, 0.9, "Saturation",
              C_ELEC, "±V_dc_xy = 48 V")

# ---- ELECTRICAL DYNAMICS (R-L + back-EMF) ----
b_elec = block(7.3, inp_y, 3.0, 0.9, "Electrical ODE",
               C_ELEC, "L·di/dt = V − R·i − K·(2π/lead)·xv")

# ---- COIL CURRENT STATE ----
b_i = block(10.8, inp_y, 1.6, 0.9, "i (state)", C_ELEC, "ix_int")

# ---- 2-COIL SCALING ----
b_2c = block(12.8, inp_y, 1.6, 0.9, "× 2", C_ELEC, "2-coil chopper")

# ---- CURRENT OUTPUT ----
b_iout = block(14.7, inp_y, 1.9, 0.9, "i_x", C_OUT, "RealOutput  (A)")

# Arrows along top band
arrow(b_cmd[0]+b_cmd[2], inp_y+0.45, b_pd[0], inp_y+0.45)
arrow(b_pd[0]+b_pd[2],   inp_y+0.45, b_sat[0], inp_y+0.45)
arrow(b_sat[0]+b_sat[2], inp_y+0.45, b_elec[0], inp_y+0.45)
arrow(b_elec[0]+b_elec[2], inp_y+0.45, b_i[0], inp_y+0.45,
      color=ARR_PHYS, lw=1.6)
arrow(b_i[0]+b_i[2], inp_y+0.45, b_2c[0], inp_y+0.45,
      color=ARR_PHYS, lw=1.6)
arrow(b_2c[0]+b_2c[2], inp_y+0.45, b_iout[0], inp_y+0.45,
      color=ARR_PHYS, lw=1.6)


# ============================================================
#  TORQUE → FORCE → MECHANICAL DYNAMICS (middle band)
# ============================================================
mid_y = 5.0

# Force conversion
b_F = block(7.3, mid_y, 3.0, 0.9, "Force conversion",
            C_MECH, "F = (2π/lead) · K · i")

# Friction
b_fric = block(2.0, mid_y, 2.4, 0.9, "Friction",
               C_MECH, "−b·xv − Fc·tanh(100·xv)")

# End-stop
b_end = block(0.3, mid_y - 1.6, 2.5, 0.9, "End-stop",
              C_MECH, "K_endstop springs")

# Newton's law
b_N = block(11.0, mid_y, 3.8, 0.9, "Newton's 2nd law",
            C_MECH, "m·dxv/dt = F_motor + F_fric + F_end")

# Drop from electrical band into force conv (via current)
arrow(b_2c[0]+b_2c[2]/2, inp_y, b_F[0]+b_F[2]/2, mid_y+0.9,
      color=ARR_PHYS, lw=1.6)
ax.text(b_F[0]+b_F[2]/2 + 1.6, (inp_y + mid_y+0.9)/2,
        "i (current)", fontsize=8, style="italic", color="#5B6B7B",
        ha="left")

# Friction → Newton
arrow(b_fric[0]+b_fric[2], mid_y+0.45, b_N[0], mid_y+0.45,
      color=ARR_PHYS, lw=1.6)

# End-stop → Newton (curved)
arrow(b_end[0]+b_end[2]/2, b_end[1]+b_end[3],
      b_N[0]+0.4, b_N[1], color=ARR_PHYS, lw=1.4)

# Force → Newton
arrow(b_F[0]+b_F[2], mid_y+0.45, b_N[0], mid_y+0.45,
      color=ARR_PHYS, lw=1.6)


# ============================================================
#  KINEMATIC STATES (bottom band)
# ============================================================
bot_y = 3.0

b_xv = block(11.0, bot_y, 1.8, 0.9, "xv (state)",
             C_MECH, "velocity")
b_xp = block(13.0, bot_y, 1.8, 0.9, "xp (state)",
             C_MECH, "∫ xv dt")

# Outputs to FMU
b_xpo = block(15.0, bot_y + 0.5, 1.8, 0.9, "x_pos", C_OUT, "RealOutput")
b_xvo = block(15.0, bot_y - 0.7, 1.8, 0.9, "x_v", C_OUT, "RealOutput")

# Newton → xv
arrow(b_N[0]+b_N[2]/2, b_N[1], b_xv[0]+b_xv[2]/2, b_xv[1]+b_xv[3],
      color=ARR_PHYS, lw=1.6)
# xv → xp (integration)
arrow(b_xv[0]+b_xv[2], bot_y+0.45, b_xp[0], bot_y+0.45,
      color=ARR_PHYS, lw=1.6)
ax.text((b_xv[0]+b_xv[2] + b_xp[0])/2, bot_y+0.78,
        "∫ dt", ha="center", fontsize=8, style="italic", color="#5B6B7B")

# xv → friction (feedback)
arrow(b_xv[0], bot_y+0.45, b_fric[0]+b_fric[2]/2, b_fric[1],
      color=ARR_SIG, lw=1.0)
ax.text(7.2, 4.0, "feedback: xv", fontsize=7.5,
        style="italic", color="#5B6B7B")

# xp → end-stop (feedback)
arrow(b_xp[0]+b_xp[2]/2, b_xp[1], b_end[0]+b_end[2]/2, b_end[1]+b_end[3],
      color=ARR_SIG, lw=1.0)
ax.text(8.5, 2.6, "feedback: xp", fontsize=7.5,
        style="italic", color="#5B6B7B")

# xp → x_pos out
arrow(b_xp[0]+b_xp[2], bot_y+0.7, b_xpo[0], b_xpo[1]+0.45)
# xv → x_v out
arrow(b_xv[0]+b_xv[2]+0.15, bot_y+0.3, b_xvo[0], b_xvo[1]+0.45)

# Feedback xp → PD (long arrow back to top)
line(b_xp[0]+b_xp[2]/2+0.4, b_xp[1], b_xp[0]+b_xp[2]/2+0.4, 1.5,
     color=ARR_SIG, lw=0.9)
line(b_xp[0]+b_xp[2]/2+0.4, 1.5, 3.4, 1.5, color=ARR_SIG, lw=0.9)
arrow(3.4, 1.5, b_pd[0]+b_pd[2]/2, b_pd[1], color=ARR_SIG, lw=0.9)
ax.text(7.5, 1.7, "position feedback to PD controller",
        ha="center", fontsize=8, style="italic", color="#5B6B7B")


# ============================================================
#  GRAVITY (only Z axis) — annotated separately
# ============================================================
ax.text(11.0, mid_y - 0.45, "Z axis only: −m·g term in Newton's law",
        ha="left", fontsize=7.5, style="italic", color="#A0522D")


# ============================================================
#  PNEUMATIC BRANCH (bottom-left, separate)
# ============================================================
py = 0.4
p1 = block(0.3, py, 2.0, 0.85, "vacuum_cmd", C_BOOL, "BooleanInput")
p2 = block(2.6, py, 2.4, 0.85, "Switch",     C_PNEU,
           "ON: p→p_vac_min   OFF: p→p_atm")
p3 = block(5.2, py, 2.6, 0.85, "Pneumatic ODE", C_PNEU,
           "dp/dt = (p_target − p) / τ_vac")
p4 = block(8.0, py, 1.8, 0.85, "pv (state)", C_PNEU, "vacuum_p")
p5 = block(10.0, py, 1.9, 0.85, "vacuum_p",  C_OUT, "RealOutput  (Pa)")
p6 = block(12.1, py, 2.4, 0.85, "Threshold",  C_PNEU,
           "pv < p_vac_threshold ?")
p7 = block(14.7, py, 2.1, 0.85, "gripper_attached", C_OUT, "BooleanOutput")

arrow(p1[0]+p1[2], py+0.42, p2[0], py+0.42)
arrow(p2[0]+p2[2], py+0.42, p3[0], py+0.42, color=ARR_PNEU, lw=1.4)
arrow(p3[0]+p3[2], py+0.42, p4[0], py+0.42, color=ARR_PNEU, lw=1.4)
arrow(p4[0]+p4[2], py+0.42, p5[0], py+0.42, color=ARR_PNEU, lw=1.4)
arrow(p4[0]+p4[2]/2, py, p6[0]+p6[2]/2, py - 0.05, color=ARR_PNEU, lw=1.0)
# small connector
line(p4[0]+p4[2]/2, py, p4[0]+p4[2]/2, py-0.4, color=ARR_PNEU, lw=1.0)
line(p4[0]+p4[2]/2, py-0.4, p6[0]+p6[2]/2, py-0.4, color=ARR_PNEU, lw=1.0)
arrow(p6[0]+p6[2], py+0.42, p7[0], py+0.42)

ax.text(7.5, py + 1.05, "PNEUMATIC BRANCH (vacuum via Venturi, 1st-order chamber)",
        ha="center", fontsize=9, fontweight="bold", color=EDGE)


# ============================================================
#  REPEAT-FOR-Y-AND-Z annotation
# ============================================================
ax.text(8.5, 8.2,
        "Diagram shows the X axis. Y axis is structurally identical (same R, L, K, lead, mass class). "
        "Z axis has a smaller motor (R_z, L_z, K_z) and adds the gravity term −m·g.",
        ha="center", fontsize=9, style="italic", color="#5B6B7B")


# ============================================================
#  LEGEND
# ============================================================
def chip(x, y, c, label):
    box = FancyBboxPatch((x, y), 0.32, 0.22,
                         boxstyle="round,pad=0.02,rounding_size=0.04",
                         linewidth=0.8, edgecolor=EDGE, facecolor=c)
    ax.add_patch(box)
    ax.text(x+0.4, y+0.11, label, ha="left", va="center",
            fontsize=8, color=EDGE)

chip(0.3, 2.45, C_SIGNAL, "Signal (Real)")
chip(0.3, 2.15, C_BOOL,   "Signal (Boolean)")
chip(2.5, 2.45, C_ELEC,   "Electrical")
chip(2.5, 2.15, C_MECH,   "Mechanical")
chip(5.0, 2.45, C_PNEU,   "Pneumatic")
chip(5.0, 2.15, C_OUT,    "FMU output")


# ============================================================
#  SAVE
# ============================================================
plt.savefig("xy10_connection_diagram.png", dpi=300,
            bbox_inches="tight", facecolor="white")
print("Saved: xy10_connection_diagram.png")
plt.show()