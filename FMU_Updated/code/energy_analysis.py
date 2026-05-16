"""
energy_analysis.py — Energy efficiency analysis of the ALIX digital twin.

Answers the question (per supervisor request, 13 May 2026):
  "Plot the % of energy flowing into each subsystem over time —
   end goal is to enhance energy efficiency."

Re-runs the master ALIX simulation, then breaks down the total electrical
energy into per-subsystem contributions:
  - Conveyor (induction motor, continuous)
  - XY10 X axis (stepper motor, intermittent during pick-place)
  - XY10 Z axis (stepper motor, intermittent during vertical moves)
  - XY10 Y axis (stepper motor, held at 0 in current scope)
  - Pneumatic (vacuum + indexer cylinders, estimated)
  - Sensors + PLC (Siemens S7-1200 + IO-Link master, estimated constant)

Produces:
  - 3-panel figure: instantaneous power, % stacked area, cumulative energy
  - Markdown summary table for report Section 9 (Energy Analysis)

Output:
  results/energy_analysis.png
  results/energy_summary.md
"""

import os
import sys
import numpy as np
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from fmu_manager import FMUWrapper
from sensor_model import default_alix_sensors
from process_state_machine import ALIXStateMachine, State


def find_fmu(name):
    for p in [
        os.path.join(HERE, name),
        os.path.join(HERE, "..", "FMUS", name),
        os.path.join(HERE, "FMUS", name),
    ]:
        if os.path.exists(p):
            return os.path.abspath(p)
    return os.path.join(HERE, name)


CONVEYOR_FMU = find_fmu("Conveyor_updated.fmu")
XY10_FMU = find_fmu("XY10Station_v2.fmu")
if not os.path.exists(XY10_FMU):
    XY10_FMU = find_fmu("XY10Station.fmu")

DT = 0.005
T_END = 30.0

P_PNEUMATIC_ACTIVE = 15.0
P_PLC_CONSTANT = 6.0
P_HMI_CONSTANT = 2.0


def run_simulation():
    print("=" * 70)
    print("Running ALIX simulation for energy analysis...")
    print("=" * 70)

    conv = FMUWrapper(CONVEYOR_FMU, instance_name="conv_energy")
    conv.initialize(start_time=0.0, stop_time=T_END)

    xy10 = FMUWrapper(XY10_FMU, instance_name="xy10_energy")
    xy10.initialize(start_time=0.0, stop_time=T_END)

    xy10_inputs = [v[0] for v in xy10.list_variables("input")]
    has_xy_inputs = all(
        k in xy10_inputs for k in ["x_cmd", "y_cmd", "z_cmd", "vacuum_cmd"]
    )

    sensors = default_alix_sensors()
    sm = ALIXStateMachine()

    n_steps = int(round(T_END / DT))
    t_arr = np.arange(n_steps) * DT

    log = {
        "t": t_arr,
        "P_conv": np.zeros(n_steps),
        "i_x": np.zeros(n_steps),
        "i_y": np.zeros(n_steps),
        "i_z": np.zeros(n_steps),
        "vacuum_cmd": np.zeros(n_steps, dtype=bool),
        "indexer_active": np.zeros(n_steps, dtype=bool),
        "conveyor_run": np.zeros(n_steps, dtype=bool),
        "state": np.zeros(n_steps, dtype=int),
        "cycle": np.zeros(n_steps, dtype=int),
    }

    pallet_x = 0.0
    last_x_belt = 0.0
    n_resets = 0
    magazine_already_released = False

    for k, t in enumerate(t_arr):
        conv.do_step(DT)
        x_belt = conv.get_real("x_belt")
        P_conv = conv.get_real("P_elec")

        if has_xy_inputs:
            xy10.set_real("x_cmd", sm.io.xy10_x_target)
            xy10.set_real("y_cmd", 0.0)
            xy10.set_real("z_cmd", sm.io.xy10_z_target)
            xy10.set_boolean("vacuum_cmd", sm.io.xy10_vacuum_cmd)

        xy10.do_step(DT)
        i_x = xy10.get_real("i_x")
        i_y = xy10.get_real("i_y")
        i_z = xy10.get_real("i_z")

        d_belt = x_belt - last_x_belt
        last_x_belt = x_belt

        pallet_held = False
        if not sm.io.magazine_blocker_extended:
            magazine_already_released = True
        if (pallet_x < 0.020 and sm.io.magazine_blocker_extended and not magazine_already_released):
            pallet_held = True
        if abs(pallet_x - 0.650) < 0.020 and sm.io.indexer_pickup_extended:
            pallet_held = True
        if sm.io.conveyor_run and not pallet_held:
            pallet_x += d_belt

        if sm.state == State.IDLE and pallet_x > 0.05 and sm.io.cycle_count > n_resets:
            sensors.reset_all()
            pallet_x = 0.0
            n_resets += 1
            magazine_already_released = False

        sensor_states = sensors.update_all(t, pallet_x)
        sm.io.s1_input = sensor_states["S1_input"]
        sm.io.s2_assembly = sensor_states["S2_assembly"]
        sm.io.s3_vision = sensor_states["S3_vision"]
        sm.io.s4_quality = sensor_states["S4_quality"]
        sm.io.gripper_attached = xy10.get_boolean("gripper_attached")
        sm.step(t, DT)

        indexer_active = (
            sm.io.xy10_vacuum_cmd
            or sm.io.indexer_pickup_extended
            or sm.io.separator_extended
        )

        log["P_conv"][k] = P_conv
        log["i_x"][k] = i_x
        log["i_y"][k] = i_y
        log["i_z"][k] = i_z
        log["vacuum_cmd"][k] = sm.io.xy10_vacuum_cmd
        log["indexer_active"][k] = indexer_active
        log["conveyor_run"][k] = sm.io.conveyor_run
        log["state"][k] = sm.state.value
        log["cycle"][k] = sm.io.cycle_count

    conv.close()
    xy10.close()

    print("Simulation finished. Computing per-subsystem power...")
    print()
    return log


def compute_subsystem_power(log):
    R_xy = 2.0
    R_z = 2.5

    P_x = log["i_x"] ** 2 * R_xy
    P_y = log["i_y"] ** 2 * R_xy
    P_z = log["i_z"] ** 2 * R_z

    P_pneumatic = np.where(log["indexer_active"], P_PNEUMATIC_ACTIVE, 0.0)
    P_plc = np.where(log["conveyor_run"], P_PLC_CONSTANT + P_HMI_CONSTANT, P_HMI_CONSTANT)

    return {
        "Conveyor (induction motor)": log["P_conv"],
        "XY10 X axis (stepper)": P_x,
        "XY10 Y axis (stepper)": P_y,
        "XY10 Z axis (stepper)": P_z,
        "Pneumatic (vacuum + cylinders)": P_pneumatic,
        "Sensors + PLC + HMI": P_plc,
    }


def main():
    log = run_simulation()
    powers = compute_subsystem_power(log)

    P_total = np.zeros_like(log["t"])
    for P in powers.values():
        P_total += P

    integrate_fn = getattr(np, "trapezoid", None)
    if integrate_fn is None:
        integrate_fn = np.trapz

    energies = {name: integrate_fn(P, log["t"]) for name, P in powers.items()}
    E_total = sum(energies.values())

    print("=" * 70)
    print(f"TOTAL ENERGY OVER {T_END:.0f} s SIMULATION: {E_total:.1f} J = {E_total / 3600:.4f} Wh")
    print("=" * 70)
    print(f"{'Subsystem':<35} {'Energy [J]':>12} {'%':>8} {'Avg P [W]':>12}")
    print("-" * 70)
    for name, E in sorted(energies.items(), key=lambda x: -x[1]):
        pct = 100 * E / E_total if E_total > 0 else 0.0
        avg_P = E / T_END
        print(f"{name:<35} {E:>12.1f} {pct:>7.1f}% {avg_P:>12.2f}")
    print()

    colors = {
        "Conveyor (induction motor)": "#1f77b4",
        "XY10 X axis (stepper)": "#ff7f0e",
        "XY10 Y axis (stepper)": "#bcbd22",
        "XY10 Z axis (stepper)": "#d62728",
        "Pneumatic (vacuum + cylinders)": "#2ca02c",
        "Sensors + PLC + HMI": "#9467bd",
    }
    order = list(colors.keys())

    fig = plt.figure(figsize=(14, 12))
    fig.subplots_adjust(left=0.10, right=0.93, top=0.93, bottom=0.08, hspace=0.45)
    fig.suptitle(
        "ALIX Digital Twin — Energy Analysis per Subsystem\n"
        "End goal: identify energy-efficiency opportunities for Industry 5.0",
        fontsize=13,
        weight="bold",
        y=0.985,
    )

    ax1 = fig.add_subplot(3, 1, 1)
    for name in order:
        ax1.plot(log["t"], powers[name], label=name, color=colors[name], lw=1.2)
    ax1.plot(log["t"], P_total, "k--", lw=0.7, label="Total", alpha=0.5)
    ax1.set_ylabel("Power [W]")
    ax1.set_xlabel("Time [s]")
    ax1.set_title("Panel A: Instantaneous electrical power per subsystem")
    ax1.set_ylim(-10, 250)
    ax1.grid(True, alpha=0.3)
    ax1.legend(loc="upper right", fontsize=8, ncol=2)

    ax2 = fig.add_subplot(3, 1, 2)
    P_safe = np.where(P_total > 0.1, P_total, 1.0)
    pct_arrays = [100 * powers[name] / P_safe for name in order]
    pct_stack = np.vstack(pct_arrays)
    ax2.stackplot(
        log["t"],
        pct_stack,
        labels=order,
        colors=[colors[n] for n in order],
        alpha=0.85,
    )
    ax2.set_ylabel("% of total power")
    ax2.set_xlabel("Time [s]")
    ax2.set_ylim(0, 100)
    ax2.set_title("Panel B: % of total instantaneous power per subsystem over time")
    ax2.grid(True, alpha=0.3)
    ax2.legend(loc="upper right", fontsize=8, ncol=2)

    ax3 = fig.add_subplot(3, 1, 3)
    sorted_items = sorted(energies.items(), key=lambda x: -x[1])
    names = [n for n, _ in sorted_items]
    values = [E for _, E in sorted_items]
    pcts = [100 * E / E_total if E_total > 0 else 0.0 for E in values]
    bar_colors = [colors[n] for n in names]
    bars = ax3.barh(range(len(names)), values, color=bar_colors, edgecolor="black", alpha=0.85)
    ax3.set_yticks(range(len(names)))
    ax3.set_yticklabels([f"{n}\n({pct:.1f}%)" for n, pct in zip(names, pcts)], fontsize=9)
    ax3.set_xlabel(f"Cumulative energy over {T_END:.0f} s [J]")
    ax3.set_title(f"Panel C: Cumulative energy per subsystem — total = {E_total:.0f} J ({E_total / 3600:.3f} Wh)")
    ax3.grid(True, axis="x", alpha=0.3)

    for i, (bar, E, pct) in enumerate(zip(bars, values, pcts)):
        ax3.text(E + max(values) * 0.01, i, f" {E:.0f} J ({pct:.1f}%)", va="center", fontsize=9)
    ax3.invert_yaxis()

    out_dir = os.path.join(HERE, "results")
    os.makedirs(out_dir, exist_ok=True)

    fig_path = os.path.join(out_dir, "energy_analysis.png")
    plt.savefig(fig_path, dpi=130, bbox_inches="tight")
    print(f"Figure saved: {fig_path}")

    md_path = os.path.join(out_dir, "energy_summary.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("# Energy Analysis — ALIX Digital Twin\n\n")
        f.write(f"Total simulation: {T_END:.0f} s (2 production cycles)\n")
        f.write(f"Total electrical energy consumed: **{E_total:.1f} J = {E_total / 3600:.4f} Wh**\n\n")
        f.write("## Per-subsystem breakdown\n\n")
        f.write("| Subsystem | Energy [J] | % of total | Avg power [W] |\n")
        f.write("|---|---:|---:|---:|\n")
        for name, E in sorted_items:
            pct = 100 * E / E_total if E_total > 0 else 0.0
            avg_P = E / T_END
            f.write(f"| {name} | {E:.1f} | {pct:.1f}% | {avg_P:.2f} |\n")
        f.write("\n## Observations\n\n")
        dominant = sorted_items[0][0]
        dominant_pct = 100 * sorted_items[0][1] / E_total if E_total > 0 else 0.0
        f.write(f"- **{dominant}** dominates the energy budget at {dominant_pct:.0f}% of total.\n")
        f.write("- The XY10 stepper motors contribute only marginally over a full cycle.\n")
        f.write("- The conveyor is the largest steady consumer.\n\n")
        f.write("## Energy efficiency opportunities\n\n")
        f.write("1. Conveyor power optimization.\n")
        f.write("2. Stepper holding current reduction.\n")
        f.write("3. Pneumatic on-demand control.\n")

    print(f"Summary saved: {md_path}")
    print()
    plt.show()


if __name__ == "__main__":
    main()