"""Generate the final energy analysis plots."""
import numpy as np
import matplotlib.pyplot as plt

# ---- MEASURED VALUES (locked) ----
PF = 0.8

subsystems = ["Conveyor\nmotor", "XY10\n(burst)", "Idle line\n(sens+PLC+ctrl)", "Pneumatic"]
model_W    = [108, 0, 8, 4]
measured_W = [557*PF, 410*PF, 33*PF, None]   # None = not measurable

# Convert "None" for pneumatic to small grey bar with annotation
measured_plot = [v if v is not None else 0 for v in measured_W]

# ---- FIGURE 1 — BAR CHART, MODEL vs MEASURED ----
fig, ax = plt.subplots(figsize=(10, 5.5))
x = np.arange(len(subsystems))
w = 0.35
ax.bar(x - w/2, model_W, w, color="#7FB3D5", label="Model / estimate")
bars = ax.bar(x + w/2, measured_plot, w, color="#1F618D", label="TDMS measured")

# Add value labels on each bar
for i, (m, t) in enumerate(zip(model_W, measured_plot)):
    ax.text(i - w/2, m + 10, f"{m} W", ha="center", fontsize=10)
    if measured_W[i] is None:
        ax.text(i + w/2, 30, "not\nisolable", ha="center", fontsize=10,
                color="darkred", fontweight="bold")
    else:
        ax.text(i + w/2, t + 10, f"{t:.0f} W", ha="center", fontsize=10, fontweight="bold")

ax.set_xticks(x)
ax.set_xticklabels(subsystems, fontsize=10)
ax.set_ylabel("Active power (W)  —  PF = 0.8 assumed", fontsize=11)
ax.set_title("Energy audit: model/estimate vs TDMS measurement",
             fontsize=12, fontweight="bold")
ax.legend(loc="upper right", fontsize=10)
ax.grid(axis="y", alpha=0.3)
ax.set_ylim(0, 600)
plt.tight_layout()
plt.savefig("energy_model_vs_measured.png", dpi=200, bbox_inches="tight")
plt.close()

# ---- FIGURE 2 — DOUGHNUT, MEASURED ENERGY SHARE ----
# Per 30 s cycle: conveyor steady, idle steady, XY10 once per cycle
E_conv = 557 * PF * 30      # conveyor motor alone, 30 s cycle
E_idle = 33  * PF * 30      # idle line, 30 s cycle
E_xy10 = 410 * PF * 15      # XY10 burst, 15 s burst

shares  = [E_conv, E_xy10, E_idle]
labels  = ["Conveyor motor", "XY10 burst", "Idle line\n(sens+PLC+ctrl)"]
colors  = ["#1F618D", "#E67E22", "#7FB3D5"]
total_J = sum(shares)
pct     = [100 * s / total_J for s in shares]

fig, ax = plt.subplots(figsize=(7, 6.5))
wedges, texts, autotexts = ax.pie(
    shares,
    labels=labels,
    autopct="%1.0f%%",
    colors=colors,
    startangle=90,
    wedgeprops=dict(width=0.4),
    textprops=dict(fontsize=11)
)
ax.text(0, 0, f"Total\n{total_J:.0f} J\nper 30 s cycle",
        ha="center", va="center", fontsize=12, fontweight="bold")
ax.set_title("Measured energy share per cycle  —  PF = 0.8",
             fontsize=12, fontweight="bold")

# Footnote
fig.text(0.5, 0.02,
         "Pneumatic + CR5 not isolable from 3-phase signature — Phase 2 work",
         ha="center", fontsize=9, style="italic", color="0.4")
plt.tight_layout()
plt.savefig("energy_share_measured.png", dpi=200, bbox_inches="tight")
plt.close()

print("Saved: energy_model_vs_measured.png")
print("Saved: energy_share_measured.png")
print()
print(f"Total measured energy / cycle:  {total_J:.0f} J  ({total_J/30:.1f} W average)")
print(f"   Conveyor: {E_conv:.0f} J ({pct[0]:.1f} %)")
print(f"   XY10:     {E_xy10:.0f} J ({pct[1]:.1f} %)")
print(f"   Idle:     {E_idle:.0f} J ({pct[2]:.1f} %)")