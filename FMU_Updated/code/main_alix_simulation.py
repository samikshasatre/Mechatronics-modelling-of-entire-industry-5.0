"""
main_alix_simulation.py — End-to-End ALIX digital twin simulation.

Master loop that orchestrates the full production line:

  - ConveyorMotor.fmu        : real-time multiphysics conveyor (electrical+mechanical)
  - XY10 kinematic surrogate : Python position-tracker mimicking the XY10 FMU's
                              motion behaviour. The full multiphysics XY10 FMU
                              is validated standalone via test_xy10.py.
  - Vacuum                   : first-order pressure dynamics (Python)
  - Sensors                  : sensor_model.py logical photoelectric sensors
  - State machine            : process_state_machine.py PLC emulator

The pallet's position on the belt is derived from x_belt of the conveyor FMU.
Sensors fire when the pallet crosses their position. The state machine reads
sensors and drives both the conveyor (run/stop) and the XY10 (targets, vacuum).

Multi-cycle support: when the state machine returns to IDLE after completing
a cycle, the pallet is reset to x=0 and sensors are reset to represent a
new pallet entering the line. This emulates the real ALIX line where
multiple pallets circulate continuously.

Run:
    python main_alix_simulation.py
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

# =====================================================================
# CONFIGURATION
# =====================================================================

# Allow the FMU to live somewhere else (e.g. ../FMUS/) — fall back to local
def find_fmu(name):
    candidates = [
        os.path.join(HERE, name),
        os.path.join(HERE, "..", "FMUS", name),
        os.path.join(HERE, "FMUS", name),
    ]
    for p in candidates:
        if os.path.exists(p):
            return os.path.abspath(p)
    return os.path.join(HERE, name)  # default — will fail with clear message

CONVEYOR_FMU = find_fmu("Conveyor_updated.fmu")
DT = 0.005                       # 5 ms macro time step
T_END = 30.0                     # 30 s total simulation

# XY10 kinematic surrogate parameters (matches the FMU dynamics)
XY10_X_MAX_VEL = 0.10            # m/s
XY10_X_TIMECONST = 0.5           # s
XY10_Z_MAX_VEL = 0.10            # m/s
XY10_Z_TIMECONST = 0.3           # s

# Vacuum chamber model
P_ATM = 101325.0                 # Pa
P_VAC_MIN = 30000.0              # Pa
P_VAC_THRESHOLD = 70000.0        # Pa
TAU_VAC = 0.15                   # s

# =====================================================================
# XY10 KINEMATIC SURROGATE
# =====================================================================

class XY10Surrogate:
    def __init__(self):
        self.x_pos = 0.0
        self.z_pos = 0.0
        self.x_v = 0.0
        self.z_v = 0.0
        self.x_target = 0.0
        self.z_target = 0.0
        self.vacuum_cmd = False
        self.vacuum_p = P_ATM
        self.gripper_attached = False

    def step(self, dt):
        x_err = self.x_target - self.x_pos
        x_v_des = np.clip(x_err / XY10_X_TIMECONST, -XY10_X_MAX_VEL, XY10_X_MAX_VEL)
        self.x_v = x_v_des
        self.x_pos += self.x_v * dt

        z_err = self.z_target - self.z_pos
        z_v_des = np.clip(z_err / XY10_Z_TIMECONST, -XY10_Z_MAX_VEL, XY10_Z_MAX_VEL)
        self.z_v = z_v_des
        self.z_pos += self.z_v * dt

        p_target = P_VAC_MIN if self.vacuum_cmd else P_ATM
        self.vacuum_p += (p_target - self.vacuum_p) / TAU_VAC * dt

        self.gripper_attached = self.vacuum_p < P_VAC_THRESHOLD


# =====================================================================
# MAIN SIMULATION
# =====================================================================

def main():
    print("=" * 70)
    print("ALIX Digital Twin — End-to-End Simulation")
    print("=" * 70)
    print()

    # ------------- Load conveyor FMU -------------
    print(f"Loading conveyor FMU: {CONVEYOR_FMU}")
    conv = FMUWrapper(CONVEYOR_FMU, instance_name="conv_main")
    conv.initialize(start_time=0.0, stop_time=T_END)
    print(f"  Conveyor FMU initialized.")

    # ------------- Build subsystems -------------
    sensors = default_alix_sensors()
    print(f"  Sensor array: {len(sensors.sensors)} sensors")
    for s in sensors.sensors:
        print(f"    {s.id}: x = {s.x*1000:.0f} mm")

    xy10 = XY10Surrogate()
    sm = ALIXStateMachine()
    print(f"  XY10 surrogate ready, state machine initialized.")
    print()

    # ------------- Set up logging -------------
    n_steps = int(T_END / DT)
    log = {
        "t":          np.zeros(n_steps),
        "x_belt":     np.zeros(n_steps),
        "v_belt":     np.zeros(n_steps),
        "P_conv":     np.zeros(n_steps),
        "i_conv":     np.zeros(n_steps),
        "x_xy10":     np.zeros(n_steps),
        "z_xy10":     np.zeros(n_steps),
        "vacuum_p":   np.zeros(n_steps),
        "gripper":    np.zeros(n_steps, dtype=bool),
        "conveyor_run":  np.zeros(n_steps, dtype=bool),
        "S1":         np.zeros(n_steps, dtype=bool),
        "S2":         np.zeros(n_steps, dtype=bool),
        "S3":         np.zeros(n_steps, dtype=bool),
        "S4":         np.zeros(n_steps, dtype=bool),
        "state":      np.zeros(n_steps, dtype=int),
        "cycle":      np.zeros(n_steps, dtype=int),
    }

    pallet_x = 0.0
    last_x_belt = 0.0
    n_resets = 0

    # ------------- Run loop -------------
    print(f"Running co-simulation: {n_steps} steps of {DT*1000:.1f} ms = {T_END:.0f} s total")
    print()

    for k in range(n_steps):
        t = k * DT

        # 1) Step the conveyor FMU
        conv.do_step(DT)
        x_belt = conv.get_real("x_belt")
        v_belt = conv.get_real("v_belt")
        P_elec = conv.get_real("P_elec")
        i_phase = conv.get_real("i_phase")

        # 2) Update logical pallet position (only moves when conveyor_run)
        d_belt = x_belt - last_x_belt
        last_x_belt = x_belt
        if sm.io.conveyor_run:
            pallet_x += d_belt

        # 3) Pallet reset: when state machine returns to IDLE for a new cycle
        # (after at least one cycle has run), reset pallet to x=0 to
        # represent a new pallet entering the line.
        if sm.state == State.IDLE and pallet_x > 0.05 and sm.io.cycle_count > n_resets:
            sensors.reset_all()
            pallet_x = 0.0
            n_resets += 1

        # 4) Update sensors with pallet position
        sensor_states = sensors.update_all(t, pallet_x)
        sm.io.s1_input    = sensor_states["S1_input"]
        sm.io.s2_assembly = sensor_states["S2_assembly"]
        sm.io.s3_vision   = sensor_states["S3_vision"]
        sm.io.s4_quality  = sensor_states["S4_quality"]

        # 5) Step XY10 surrogate
        xy10.x_target = sm.io.xy10_x_target
        xy10.z_target = sm.io.xy10_z_target
        xy10.vacuum_cmd = sm.io.xy10_vacuum_cmd
        xy10.step(DT)
        sm.io.gripper_attached = xy10.gripper_attached

        # 6) Step the state machine
        sm.step(t, DT)

        # 7) Log everything
        log["t"][k] = t
        log["x_belt"][k] = pallet_x
        log["v_belt"][k] = v_belt
        log["P_conv"][k] = P_elec
        log["i_conv"][k] = i_phase
        log["x_xy10"][k] = xy10.x_pos
        log["z_xy10"][k] = xy10.z_pos
        log["vacuum_p"][k] = xy10.vacuum_p
        log["gripper"][k] = xy10.gripper_attached
        log["conveyor_run"][k] = sm.io.conveyor_run
        log["S1"][k] = sm.io.s1_input
        log["S2"][k] = sm.io.s2_assembly
        log["S3"][k] = sm.io.s3_vision
        log["S4"][k] = sm.io.s4_quality
        log["state"][k] = sm.state.value
        log["cycle"][k] = sm.io.cycle_count

        # Progress
        if k % int(5.0/DT) == 0 and k > 0:
            print(f"  t = {t:5.1f} s  state = {sm.state.name:20s}  "
                  f"pallet_x = {pallet_x*1000:6.0f} mm  "
                  f"cycle_count = {sm.io.cycle_count}")

    conv.close()
    print()
    print("Simulation finished.")
    print(f"Total cycles completed: {sm.io.cycle_count}")
    print(f"Pallet resets: {n_resets}")
    print()

    # ------------- Print state log -------------
    print("=" * 70)
    print("STATE TRANSITIONS")
    print("=" * 70)
    for et, ev in sm.get_event_log():
        print(f"  t = {et:6.2f} s : {ev}")
    print()

    # ------------- Plot results -------------
    print("Generating plots...")
    fig, axes = plt.subplots(6, 1, figsize=(13, 13), sharex=True)
    fig.suptitle("ALIX Digital Twin — End-to-End Multi-Cycle Simulation",
                 fontsize=14, weight="bold")

    # Pallet position + sensor positions
    axes[0].plot(log["t"], log["x_belt"]*1000, "b-", lw=1.5, label="Pallet position")
    for s in sensors.sensors:
        axes[0].axhline(s.x*1000, color="gray", ls=":", lw=0.7, alpha=0.7)
        axes[0].text(T_END*1.005, s.x*1000, s.id, fontsize=8, va="center")
    axes[0].set_ylabel("Pallet x [mm]")
    axes[0].grid(True); axes[0].legend(loc="upper left")

    # Sensor activations as bars
    for i, sid in enumerate(["S1", "S2", "S3", "S4"]):
        active_idx = np.where(log[sid])[0]
        for idx in active_idx:
            axes[1].axvspan(log["t"][idx], log["t"][idx]+DT,
                            ymin=i/4.0, ymax=(i+1)/4.0, color=f"C{i}", alpha=0.7)
    axes[1].set_yticks([0.125, 0.375, 0.625, 0.875])
    axes[1].set_yticklabels(["S1", "S2", "S3", "S4"])
    axes[1].set_ylabel("Sensors")
    axes[1].grid(True)
    axes[1].set_ylim(0, 1)

    # Conveyor power and current
    ax2 = axes[2]
    ax2b = ax2.twinx()
    ax2.plot(log["t"], log["P_conv"], "m-", lw=1.0, label="P_elec")
    ax2.set_ylabel("P_conv [W]", color="m")
    ax2.tick_params(axis="y", labelcolor="m")
    ax2b.plot(log["t"], log["i_conv"], "c-", lw=1.0, label="i_phase")
    ax2b.set_ylabel("i_phase [A]", color="c")
    ax2b.tick_params(axis="y", labelcolor="c")
    ax2.grid(True)

    # XY10 positions
    axes[3].plot(log["t"], log["x_xy10"]*1000, "b-", label="X")
    axes[3].plot(log["t"], log["z_xy10"]*1000, "r-", label="Z")
    axes[3].set_ylabel("XY10 [mm]")
    axes[3].grid(True); axes[3].legend(loc="upper left")

    # Vacuum
    axes[4].plot(log["t"], log["vacuum_p"]/1000, "c-", label="vacuum_p")
    axes[4].axhline(P_VAC_THRESHOLD/1000, color="orange", ls="--", lw=0.7,
                     label=f"Threshold {P_VAC_THRESHOLD/1000:.0f} kPa")
    axes[4].set_ylabel("Vacuum [kPa]")
    axes[4].grid(True); axes[4].legend(loc="upper left")

    # State timeline
    state_names = [s.name for s in State]
    state_colors = plt.cm.tab20(np.linspace(0, 1, len(state_names)))
    state_to_idx = {s.value: i for i, s in enumerate(State)}
    prev = log["state"][0]
    block_start = 0
    for k in range(1, n_steps):
        if log["state"][k] != prev or k == n_steps - 1:
            color = state_colors[state_to_idx[prev]]
            axes[5].axvspan(log["t"][block_start], log["t"][k],
                             color=color, alpha=0.7)
            prev = log["state"][k]
            block_start = k
    axes[5].set_yticks([])
    axes[5].set_ylabel("State")
    axes[5].set_xlabel("Time [s]")
    axes[5].grid(True, axis="x")
    handles = [mpatches.Patch(color=state_colors[i], label=name)
               for i, name in enumerate(state_names)]
    axes[5].legend(handles=handles, loc="upper center",
                   bbox_to_anchor=(0.5, -0.5), ncol=6, fontsize=7)

    plt.tight_layout()
    out_path = os.path.join(HERE, "results", "alix_full_cycle.png")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    plt.savefig(out_path, dpi=120, bbox_inches="tight")
    print(f"Plot saved to: {out_path}")
    print()

    # ------------- Summary metrics for cycle 1 -------------
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
        travel_S1_S2 = t_s2 - t_s1
        dist_S1_S2 = sensors["S2_assembly"].x - sensors["S1_input"].x
        v_avg = dist_S1_S2 / travel_S1_S2
        print(f"\n  Travel time S1 -> S2:    {travel_S1_S2:.2f} s")
        print(f"  Distance S1 -> S2:        {dist_S1_S2*1000:.0f} mm")
        print(f"  Average belt speed:       {v_avg*1000:.0f} mm/s = {v_avg:.3f} m/s")
        print(f"    (Conveyor model predicts ~196 mm/s at no/light load)")

    # Also report cycle times
    print()
    print("=" * 70)
    print("PER-CYCLE TIMING")
    print("=" * 70)
    # Find COMPLETE entry events from event log
    completes = [(et, ev) for et, ev in sm.get_event_log() if "-> COMPLETE" in ev]
    starts = [(et, ev) for et, ev in sm.get_event_log() if "IDLE -> CONVEYOR_START" in ev]
    for i, (t_complete, _) in enumerate(completes):
        if i < len(starts):
            t_start = starts[i][0]
            duration = t_complete - t_start
            print(f"  Cycle {i+1}: start = {t_start:6.2f} s, complete = {t_complete:6.2f} s, "
                  f"duration = {duration:5.2f} s")
    print()

    plt.show()


if __name__ == "__main__":
    main()