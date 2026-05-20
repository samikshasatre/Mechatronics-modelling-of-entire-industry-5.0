"""
main_alix_simulation.py — End-to-End ALIX digital twin simulation.

VERSION 3 — Following supervisor feedback (Romain Delabeye, 6 May 2026):
  - Sensor plot redesigned: each sensor on its own labeled track
  - New actuator Gantt plot showing concurrent actuator activations
  - State plot retained but complemented by the actuator plot
"""

import os, sys
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from fmu_manager import FMUWrapper
from sensor_model import default_alix_sensors
from process_state_machine import ALIXStateMachine, State

def find_fmu(name):
    candidates = [
        os.path.join(HERE, name),
        os.path.join(HERE, "..", "FMUS", name),
        os.path.join(HERE, "FMUS", name),
    ]
    for p in candidates:
        if os.path.exists(p):
            return os.path.abspath(p)
    return os.path.join(HERE, name)

CONVEYOR_FMU = find_fmu("Conveyor_updated.fmu")
XY10_FMU = find_fmu("XY10Station_v2.fmu")
if not os.path.exists(XY10_FMU):
    XY10_FMU = find_fmu("XY10Station.fmu")

DT = 0.005
T_END = 30.0


def main():
    print("=" * 70)
    print("ALIX Digital Twin — End-to-End Simulation (3-axis XY10 FMU, v3 plots)")
    print("=" * 70)
    print()

    print(f"Loading conveyor FMU: {CONVEYOR_FMU}")
    conv = FMUWrapper(CONVEYOR_FMU, instance_name="conv_main")
    conv.initialize(start_time=0.0, stop_time=T_END)
    print(f"  Conveyor FMU initialized.")

    print(f"Loading XY10 FMU: {XY10_FMU}")
    xy10 = FMUWrapper(XY10_FMU, instance_name="xy10_main")
    xy10.initialize(start_time=0.0, stop_time=T_END)
    xy10_inputs = [v[0] for v in xy10.list_variables("input")]
    has_xy_inputs = all(k in xy10_inputs for k in ["x_cmd", "y_cmd", "z_cmd", "vacuum_cmd"])
    print(f"  XY10 FMU initialized.")
    print(f"  XY10 has 3-axis FMI inputs: {has_xy_inputs}")
    print()

    sensors = default_alix_sensors()
    print(f"  Sensor array: {len(sensors.sensors)} sensors")
    for s in sensors.sensors:
        print(f"    {s.id}: x = {s.x*1000:.0f} mm")
    sm = ALIXStateMachine()
    print(f"  State machine initialized.")
    print()

    n_steps = int(T_END / DT)
    log = {
        "t": np.zeros(n_steps),
        "x_belt": np.zeros(n_steps),
        "v_belt": np.zeros(n_steps),
        "P_conv": np.zeros(n_steps),
        "i_conv": np.zeros(n_steps),
        "x_xy10": np.zeros(n_steps),
        "y_xy10": np.zeros(n_steps),
        "z_xy10": np.zeros(n_steps),
        "i_x_xy10": np.zeros(n_steps),
        "i_y_xy10": np.zeros(n_steps),
        "i_z_xy10": np.zeros(n_steps),
        "P_elec_xy10": np.zeros(n_steps),
        "vacuum_p": np.zeros(n_steps),
        "gripper": np.zeros(n_steps, dtype=bool),
        # ACTUATOR ACTIVATION STATES (NEW)
        "conveyor_run": np.zeros(n_steps, dtype=bool),
        "xy10_pick_active": np.zeros(n_steps, dtype=bool),
        "xy10_place_active": np.zeros(n_steps, dtype=bool),
        "xy10_vacuum_cmd": np.zeros(n_steps, dtype=bool),
        # SENSORS
        "S1": np.zeros(n_steps, dtype=bool),
        "S2": np.zeros(n_steps, dtype=bool),
        "S3": np.zeros(n_steps, dtype=bool),
        "S4": np.zeros(n_steps, dtype=bool),
        "state": np.zeros(n_steps, dtype=int),
        "cycle": np.zeros(n_steps, dtype=int),
    }

    pallet_x = 0.0
    last_x_belt = 0.0
    n_resets = 0

    print(f"Running co-simulation: {n_steps} steps of {DT*1000:.1f} ms = {T_END:.0f} s total")
    print()

    for k in range(n_steps):
        t = k * DT

        conv.do_step(DT)
        x_belt = conv.get_real("x_belt")
        v_belt = conv.get_real("v_belt")
        P_conv = conv.get_real("P_elec")
        i_conv = conv.get_real("i_phase")

        if has_xy_inputs:
            xy10.set_real("x_cmd", sm.io.xy10_x_target)
            xy10.set_real("y_cmd", 0.0)
            xy10.set_real("z_cmd", sm.io.xy10_z_target)
            xy10.set_boolean("vacuum_cmd", sm.io.xy10_vacuum_cmd)

        xy10.do_step(DT)
        x_xy10 = xy10.get_real("x_pos")
        y_xy10 = xy10.get_real("y_pos")
        z_xy10 = xy10.get_real("z_pos")
        i_x = xy10.get_real("i_x")
        i_y = xy10.get_real("i_y")
        i_z = xy10.get_real("i_z")
        P_elec_xy10 = xy10.get_real("P_elec")
        vacuum_p = xy10.get_real("vacuum_p")
        gripper_attached = xy10.get_boolean("gripper_attached")

        # Pallet motion logic — matches real ALIX (continuous belt, indexer-gated)
        # The belt always moves when conveyor_run; the pallet only moves
        # if it is NOT held by an indexer at its current station position.
        d_belt = x_belt - last_x_belt
        last_x_belt = x_belt

        # Check if pallet is currently held by an indexer:
        # - At XY10 pickup station (~650 mm): held by indexer_pickup_extended
        # - At magazine release (~0 mm): held by magazine_blocker_extended
        pallet_held = False
        if abs(pallet_x - 0.650) < 0.020 and sm.io.indexer_pickup_extended:
            pallet_held = True
        if pallet_x < 0.020 and sm.io.magazine_blocker_extended:
            pallet_held = True

        # Pallet moves only if belt is running AND it's not being held
        if sm.io.conveyor_run and not pallet_held:
            pallet_x += d_belt

        if sm.state == State.IDLE and pallet_x > 0.05 and sm.io.cycle_count > n_resets:
            sensors.reset_all()
            pallet_x = 0.0
            n_resets += 1

        sensor_states = sensors.update_all(t, pallet_x)
        sm.io.s1_input = sensor_states["S1_input"]
        sm.io.s2_assembly = sensor_states["S2_assembly"]
        sm.io.s3_vision = sensor_states["S3_vision"]
        sm.io.s4_quality = sensor_states["S4_quality"]
        sm.io.gripper_attached = gripper_attached
        sm.step(t, DT)

        log["t"][k] = t
        log["x_belt"][k] = pallet_x
        log["v_belt"][k] = v_belt
        log["P_conv"][k] = P_conv
        log["i_conv"][k] = i_conv
        log["x_xy10"][k] = x_xy10
        log["y_xy10"][k] = y_xy10
        log["z_xy10"][k] = z_xy10
        log["i_x_xy10"][k] = i_x
        log["i_y_xy10"][k] = i_y
        log["i_z_xy10"][k] = i_z
        log["P_elec_xy10"][k] = P_elec_xy10
        log["vacuum_p"][k] = vacuum_p
        log["gripper"][k] = gripper_attached
        log["conveyor_run"][k] = sm.io.conveyor_run
        log["xy10_pick_active"][k] = sm.io.xy10_pick_active
        log["xy10_place_active"][k] = sm.io.xy10_place_active
        log["xy10_vacuum_cmd"][k] = sm.io.xy10_vacuum_cmd
        log["S1"][k] = sm.io.s1_input
        log["S2"][k] = sm.io.s2_assembly
        log["S3"][k] = sm.io.s3_vision
        log["S4"][k] = sm.io.s4_quality
        log["state"][k] = sm.state.value
        log["cycle"][k] = sm.io.cycle_count
        

        if k % int(5.0/DT) == 0 and k > 0:
            print(f"  t = {t:5.1f} s  state = {sm.state.name:20s}  "
                  f"pallet_x = {pallet_x*1000:6.0f} mm  "
                  f"XY10: x={x_xy10*1000:5.0f}mm z={z_xy10*1000:5.0f}mm "
                  f"cycle_count = {sm.io.cycle_count}")

    conv.close()
    xy10.close()
    print()
    print("Simulation finished.")
    print(f"Total cycles completed: {sm.io.cycle_count}")
    print(f"Pallet resets: {n_resets}")
    print()

    print("=" * 70)
    print("STATE TRANSITIONS")
    print("=" * 70)
    for et, ev in sm.get_event_log():
        print(f"  t = {et:6.2f} s : {ev}")
    print()

    # =================================================================
    # PLOTTING — V3 with redesigned sensor + actuator panels
    # =================================================================
    print("Generating plots...")

    fig = plt.figure(figsize=(14, 16))
    gs = fig.add_gridspec(8, 1, hspace=0.45, height_ratios=[2, 2.5, 1.5, 2, 2, 2, 2.5, 2.5])
    fig.suptitle("ALIX Digital Twin — End-to-End Multi-Cycle Simulation (3-axis XY10 FMU)\n"
                 "Sensors and actuators on separate tracks per supervisor feedback",
                 fontsize=13, weight="bold")

    # ----------- Panel 0: Pallet position with sensor positions marked -----------
    ax0 = fig.add_subplot(gs[0])
    ax0.plot(log["t"], log["x_belt"]*1000, "b-", lw=1.5, label="Pallet position")
    for s in sensors.sensors:
        ax0.axhline(s.x*1000, color="gray", ls=":", lw=0.7, alpha=0.6)
        ax0.text(T_END*1.005, s.x*1000, s.id.replace("_", " "),
                 fontsize=8, va="center", color="dimgray")
    ax0.set_ylabel("Pallet x [mm]")
    ax0.set_title("Pallet position along the conveyor (sensor trigger positions in gray)")
    ax0.grid(True); ax0.legend(loc="upper left")

    # ----------- Panel 1: Sensors, each on its own clear track -----------
    ax1 = fig.add_subplot(gs[1], sharex=ax0)
    sensor_keys = ["S1", "S2", "S3", "S4"]
    sensor_labels = [
        "S1  at  100 mm  —  input detection",
        "S2  at  650 mm  —  XY10 pick position",
        "S3  at 1100 mm  —  vision station",
        "S4  at 1650 mm  —  quality check",
    ]
    sensor_colors = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728"]
    for i, (key, lab, col) in enumerate(zip(sensor_keys, sensor_labels, sensor_colors)):
        # signal stays low (=i) when inactive, jumps to (i+0.7) when active
        y_low = i
        y_high = i + 0.7
        y = np.where(log[key], y_high, y_low)
        ax1.fill_between(log["t"], y_low, y, where=log[key], color=col, alpha=0.8,
                         step="post")
        # mark first activation time
        active_idx = np.where(log[key])[0]
        if len(active_idx) > 0:
            first_t = log["t"][active_idx[0]]
            ax1.axvline(first_t, color=col, ls="--", lw=0.5, alpha=0.4)
    ax1.set_yticks([i + 0.35 for i in range(4)])
    ax1.set_yticklabels(sensor_labels, fontsize=9)
    ax1.set_ylabel("")
    ax1.set_title("Sensor activations — each sensor on its own track (pulse goes high when pallet detected)")
    ax1.set_ylim(-0.3, 4.3)
    ax1.grid(True, axis="x")

    # ----------- Panel 2: Cycle counter -----------
    ax2 = fig.add_subplot(gs[2], sharex=ax0)
    ax2.step(log["t"], log["cycle"], "k-", where="post", lw=1.5)
    ax2.set_ylabel("Cycle #")
    ax2.set_title("Cycle counter (increments on each COMPLETE)")
    ax2.set_yticks([0, 1, 2])
    ax2.grid(True)

    # ----------- Panel 3: Conveyor power and current -----------
    ax3 = fig.add_subplot(gs[3], sharex=ax0)
    ax3b = ax3.twinx()
    ax3.plot(log["t"], log["P_conv"], "m-", lw=1.0)
    ax3.set_ylim(-50, 300)  # Clip out the startup spike to see the steady state
    ax3b.set_ylim(-1, 3)  # Same for current    ax3.set_ylabel("Conveyor P_elec [W]", color="m")
    ax3.tick_params(axis="y", labelcolor="m")
    ax3b.plot(log["t"], log["i_conv"], "c-", lw=1.0)
    ax3b.set_ylabel("Conveyor i_phase [A]", color="c")
    ax3b.tick_params(axis="y", labelcolor="c")
    ax3.set_title("Conveyor FMU electrical signals — power (left) and phase current (right)")
    ax3.grid(True)

    # ----------- Panel 4: XY10 positions (all 3 axes) -----------
    ax4 = fig.add_subplot(gs[4], sharex=ax0)
    ax4.plot(log["t"], log["x_xy10"]*1000, "b-", label="X", lw=1.5)
    ax4.plot(log["t"], log["y_xy10"]*1000, "g-", label="Y (held at 0 in single-cycle)", lw=1.0)
    ax4.plot(log["t"], log["z_xy10"]*1000, "r-", label="Z", lw=1.5)
    ax4.set_ylabel("XY10 position [mm]")
    ax4.set_title("XY10 axis positions — 3-axis Cartesian gantry (X, Y, Z)")
    ax4.grid(True); ax4.legend(loc="upper left", ncol=3, fontsize=9)

    # ----------- Panel 5: XY10 stepper currents -----------
    ax5 = fig.add_subplot(gs[5], sharex=ax0)
    ax5.plot(log["t"], log["i_x_xy10"], "b-", label="i_x", lw=0.8)
    ax5.plot(log["t"], log["i_y_xy10"], "g-", label="i_y", lw=0.8)
    ax5.plot(log["t"], log["i_z_xy10"], "r-", label="i_z", lw=0.8)
    ax5.set_ylabel("XY10 currents [A]")
    ax5.set_title("XY10 stepper currents (FMU output, 2-coil scaled)")
    ax5.grid(True); ax5.legend(loc="upper left", ncol=3, fontsize=9)

    # ----------- Panel 6: ACTUATOR Gantt (NEW — addresses Remark 4) -----------
    ax6 = fig.add_subplot(gs[6], sharex=ax0)
    actuator_keys = ["conveyor_run", "xy10_pick_active", "xy10_place_active",
                     "xy10_vacuum_cmd", "gripper"]
    actuator_labels = [
        "conveyor_run         —  belt motor on/off",
        "xy10_pick_active     —  pick command active",
        "xy10_place_active    —  place command active",
        "xy10_vacuum_cmd      —  vacuum solenoid on/off",
        "gripper_attached     —  part held (vacuum_p < 70 kPa)",
    ]
    actuator_colors = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd"]
    for i, (key, lab, col) in enumerate(zip(actuator_keys, actuator_labels, actuator_colors)):
        y_low = i
        y_high = i + 0.7
        active = log[key].astype(bool)
        y = np.where(active, y_high, y_low)
        ax6.fill_between(log["t"], y_low, y, where=active, color=col, alpha=0.8,
                         step="post")
    ax6.set_yticks([i + 0.35 for i in range(len(actuator_keys))])
    ax6.set_yticklabels(actuator_labels, fontsize=9)
    ax6.set_title("ACTUATOR ACTIVATION TRACKS — concurrent activations visible (NEW per supervisor feedback)")
    ax6.set_ylim(-0.3, len(actuator_keys) + 0.3)
    ax6.grid(True, axis="x")

    # ----------- Panel 7: State machine Gantt (existing, kept) -----------
    ax7 = fig.add_subplot(gs[7], sharex=ax0)
    state_names = [s.name for s in State]
    state_colors = plt.cm.tab20(np.linspace(0, 1, len(state_names)))
    state_to_idx = {s.value: i for i, s in enumerate(State)}
    prev = log["state"][0]
    block_start = 0
    for k in range(1, n_steps):
        if log["state"][k] != prev or k == n_steps - 1:
            color = state_colors[state_to_idx[prev]]
            ax7.axvspan(log["t"][block_start], log["t"][k], color=color, alpha=0.7)
            prev = log["state"][k]
            block_start = k
    ax7.set_yticks([])
    ax7.set_ylabel("State")
    ax7.set_xlabel("Time [s]")
    ax7.set_title("State machine — the ALIX line moves through 12 states per cycle")
    ax7.grid(True, axis="x")
    handles = [mpatches.Patch(color=state_colors[i], label=name)
               for i, name in enumerate(state_names)]
    ax7.legend(handles=handles, loc="upper center",
               bbox_to_anchor=(0.5, -0.45), ncol=6, fontsize=7)

    plt.tight_layout(rect=[0, 0, 1, 0.97])
    out_path = os.path.join(HERE, "results", "alix_full_cycle.png")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    plt.savefig(out_path, dpi=120, bbox_inches="tight")
    print(f"Plot saved to: {out_path}")
    print()

    # ----------- Metrics -----------
    print("=" * 70)
    print("CYCLE 1 METRICS")
    print("=" * 70)
    def first_true(arr):
        idx = np.where(arr)[0]
        return log["t"][idx[0]] if len(idx) > 0 else None

    t_s1 = first_true(log["S1"])
    t_s2 = first_true(log["S2"])
    t_s3 = first_true(log["S3"])
    t_s4 = first_true(log["S4"])
    t_grip = first_true(log["gripper"])
    if t_s1: print(f"  Pallet at S1 (input):    t = {t_s1:.2f} s")
    if t_s2: print(f"  Pallet at S2 (XY10):     t = {t_s2:.2f} s")
    if t_grip: print(f"  Gripper attached:        t = {t_grip:.2f} s")
    if t_s3: print(f"  Pallet at S3 (vision):   t = {t_s3:.2f} s")
    if t_s4: print(f"  Pallet at S4 (quality):  t = {t_s4:.2f} s")
    if t_s1 and t_s2:
        travel = t_s2 - t_s1
        dist = sensors["S2_assembly"].x - sensors["S1_input"].x
        v_avg = dist / travel
        print(f"\n  Travel time S1 -> S2:    {travel:.2f} s")
        print(f"  Distance S1 -> S2:        {dist*1000:.0f} mm")
        print(f"  Average belt speed:       {v_avg*1000:.0f} mm/s = {v_avg:.3f} m/s")

    print()
    print("  XY10 STEPPER CURRENT PEAKS:")
    print(f"    Peak i_x: {np.max(np.abs(log['i_x_xy10'])):.2f} A")
    print(f"    Peak i_y: {np.max(np.abs(log['i_y_xy10'])):.2f} A")
    print(f"    Peak i_z: {np.max(np.abs(log['i_z_xy10'])):.2f} A")
    print(f"    Peak P_elec (XY10): {log['P_elec_xy10'].max():.1f} W")
    print(f"    Min vacuum_p: {log['vacuum_p'].min()/1000:.1f} kPa")

    print()
    print("=" * 70)
    print("PER-CYCLE TIMING")
    print("=" * 70)
    completes = [(et, ev) for et, ev in sm.get_event_log() if "-> COMPLETE" in ev]
    starts = [(et, ev) for et, ev in sm.get_event_log() if "IDLE -> CONVEYOR_START" in ev]
    for i, (t_complete, _) in enumerate(completes):
        if i < len(starts):
            t_start = starts[i][0]
            duration = t_complete - t_start
            print(f"  Cycle {i+1}: start = {t_start:6.2f} s, complete = {t_complete:6.2f} s, "
                  f"duration = {duration:5.2f} s")
    print()
    # ----------- Panel 3: Conveyor power and current -----------
    ax3 = fig.add_subplot(gs[3], sharex=ax0)
    ax3b = ax3.twinx()

    # Plot power (left axis, magenta)
    ax3.plot(log["t"], log["P_conv"], "m-", lw=1.5, label="P_elec (FMU)")
    ax3.axhline(108, color="m", ls="--", lw=0.5, alpha=0.5,
                label="108 W expected steady-state")
    ax3.set_ylabel("Conveyor P_elec [W]", color="m")
    ax3.tick_params(axis="y", labelcolor="m")
    ax3.set_ylim(-50, 300)
    ax3.legend(loc="upper right", fontsize=7)

    # Plot current (right axis, cyan)
    ax3b.plot(log["t"], log["i_conv"], "c-", lw=1.5, label="i_phase (FMU)")
    ax3b.axhline(1.63, color="c", ls="--", lw=0.5, alpha=0.5)
    ax3b.set_ylabel("Conveyor i_phase [A]", color="c")
    ax3b.tick_params(axis="y", labelcolor="c")
    ax3b.set_ylim(-0.5, 3)

    ax3.set_title("Conveyor FMU electrical signals — steady state ~108 W / 1.63 A (startup inrush clipped)")
    ax3.grid(True)

    # Annotation
    ax3.annotate("Startup inrush\n(clipped: peaks ~6 kW / 10 A)",
                 xy=(0.3, 280), xytext=(3, 250),
                 fontsize=8, color="dimgray", style="italic",
                 arrowprops=dict(arrowstyle="->", color="dimgray", lw=0.5))
    plt.show()


if __name__ == "__main__":
    main()