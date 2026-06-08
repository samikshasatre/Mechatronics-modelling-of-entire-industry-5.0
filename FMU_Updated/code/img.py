import matplotlib.pyplot as plt

# ---------- Stage A ----------
fig, ax = plt.subplots(figsize=(4.0, 2.3))

ax.plot(
    t_window * 1000,
    i_raw,
    color="0.7",
    lw=1.0,
    label="Raw TDMS"
)

ax.plot(
    t_window * 1000,
    i_filtered,
    color="#2E75B6",
    lw=2.0,
    label="Band-pass (40–60 Hz)"
)

ax.set_title("Stage A: Signal Conditioning", fontsize=10, weight="bold")
ax.set_xlabel("Time (ms)", fontsize=9)
ax.set_ylabel("Current (A)", fontsize=9)

ax.legend(frameon=False, fontsize=8)

ax.grid(alpha=0.3)

ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)

ax.tick_params(labelsize=8)

plt.tight_layout()

plt.savefig(
    "stage_a_mini.png",
    dpi=300,
    bbox_inches="tight"
)

plt.close()


# ---------- Stage B ----------
fig, ax = plt.subplots(figsize=(4.0, 2.3))

ax.plot(
    t_60s,
    T_fmu,
    color="#2E75B6",
    lw=2.2,
    label="FMU"
)

ax.plot(
    t_60s,
    T_dymola,
    color="#E06C5C",
    lw=1.8,
    linestyle="--",
    label="Dymola"
)

ax.set_title("Stage B: FMU Fidelity Check", fontsize=10, weight="bold")

ax.set_xlabel("Time (s)", fontsize=9)
ax.set_ylabel("Motor Temperature (K)", fontsize=9)

ax.legend(frameon=False, fontsize=8)

ax.grid(alpha=0.3)

ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)

ax.tick_params(labelsize=8)

plt.tight_layout()

plt.savefig(
    "stage_b_mini.png",
    dpi=300,
    bbox_inches="tight"
)

plt.close()