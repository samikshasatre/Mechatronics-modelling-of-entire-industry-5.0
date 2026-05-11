"""
process_state_machine.py — PLC-emulating finite-state machine for the ALIX line.

This module implements the same sequencing logic that runs on the real Siemens
S7-1200 PLC, but in Python so it can drive the digital twin in simulation.

The state machine is event-driven:
  - Sensor events (rising edges) trigger transitions
  - Timers handle waits between sub-states
  - Output commands tell the FMUs and physics models what to do

States (simplified single-pallet cycle):
    IDLE                  -> wait for work order
    CONVEYOR_START        -> turn motor on, wait for pallet at S1
    PALLET_TRANSPORT      -> conveyor running, pallet moving toward XY10
    PALLET_AT_XY10        -> pallet at S2, stop conveyor
    XY10_PICK             -> command XY10 to pick (Z down, vacuum on, Z up)
    XY10_PLACE            -> command XY10 to place at destination
    CONVEYOR_RESTART      -> resume conveyor, pallet moves to vision
    PALLET_AT_VISION      -> pallet at S3
    INSPECTION            -> simulate inspection delay
    PALLET_AT_QUALITY     -> pallet at S4
    COMPLETE              -> log cycle, return to IDLE
    FAULT                 -> any subsystem error
"""

from enum import Enum, auto
from dataclasses import dataclass, field


class State(Enum):
    IDLE = auto()
    CONVEYOR_START = auto()
    PALLET_TRANSPORT = auto()
    PALLET_AT_XY10 = auto()
    XY10_PICK = auto()
    XY10_PLACE = auto()
    CONVEYOR_RESTART = auto()
    PALLET_AT_VISION = auto()
    INSPECTION = auto()
    PALLET_AT_QUALITY = auto()
    COMPLETE = auto()
    FAULT = auto()


@dataclass
class IO:
    """All sensor inputs and actuator outputs of the line."""
    # Sensor inputs (Boolean) — set by sensor_model
    s1_input: bool = False
    s2_assembly: bool = False
    s3_vision: bool = False
    s4_quality: bool = False

    # Actuator outputs (commands to FMUs / physics)
    conveyor_run: bool = False
    xy10_x_target: float = 0.0
    xy10_z_target: float = 0.0
    xy10_vacuum_cmd: bool = False
    xy10_pick_active: bool = False
    xy10_place_active: bool = False

    # Status flags from XY10 model
    gripper_attached: bool = False
    xy10_at_pick_pos: bool = False
    xy10_at_place_pos: bool = False
    xy10_at_home: bool = True

    # Logical events
    inspection_done: bool = False
    quality_pass: bool = True

    # Cycle counter
    cycle_count: int = 0


class ALIXStateMachine:
    """
    Single-pallet, single-cycle state machine for the ALIX line.
    """

    def __init__(self):
        self.state = State.IDLE
        self.io = IO()
        self.t = 0.0
        self._t_state_entered = 0.0
        self._state_log = []
        self._event_log = []
        self._counted_this_cycle = False  # cycle-count guard

    def _enter(self, new_state: State):
        """Transition to a new state and log it."""
        if new_state != self.state:
            self._event_log.append((self.t, f"{self.state.name} -> {new_state.name}"))
            self.state = new_state
            self._t_state_entered = self.t
            # Clear the cycle-counted flag whenever we enter a new state.
            # When COMPLETE is entered, the counter increments once and the
            # flag is set; on transition out of COMPLETE (to IDLE) it is
            # cleared, ready for the next cycle.
            self._counted_this_cycle = False
        self._state_log.append((self.t, self.state.name))

    def time_in_state(self) -> float:
        """Time elapsed since entering the current state."""
        return self.t - self._t_state_entered

    def step(self, t: float, dt: float):
        """Advance the state machine by dt seconds."""
        self.t = t
        s = self.state

        # ---- IDLE ----
        if s == State.IDLE:
            self.io.conveyor_run = False
            self.io.xy10_pick_active = False
            self.io.xy10_place_active = False
            self.io.xy10_vacuum_cmd = False
            if self.time_in_state() > 0.5:
                self._enter(State.CONVEYOR_START)

        # ---- CONVEYOR_START ----
        elif s == State.CONVEYOR_START:
            self.io.conveyor_run = True
            if self.io.s1_input:
                self._enter(State.PALLET_TRANSPORT)

        # ---- PALLET_TRANSPORT ----
        elif s == State.PALLET_TRANSPORT:
            self.io.conveyor_run = True
            if self.io.s2_assembly:
                self._enter(State.PALLET_AT_XY10)

        # ---- PALLET_AT_XY10 ----
        elif s == State.PALLET_AT_XY10:
            self.io.conveyor_run = False
            if self.time_in_state() > 0.3:
                self._enter(State.XY10_PICK)

        # ---- XY10_PICK ----
        elif s == State.XY10_PICK:
            self.io.xy10_pick_active = True
            self.io.xy10_x_target = 0.10
            self.io.xy10_z_target = 0.05
            self.io.xy10_vacuum_cmd = True
            if self.io.gripper_attached and self.time_in_state() > 1.5:
                self._enter(State.XY10_PLACE)

        # ---- XY10_PLACE ----
        elif s == State.XY10_PLACE:
            self.io.xy10_pick_active = False
            self.io.xy10_place_active = True
            self.io.xy10_x_target = 0.20
            self.io.xy10_z_target = 0.0
            if self.time_in_state() > 1.5:
                self.io.xy10_vacuum_cmd = False
                if self.time_in_state() > 2.0:
                    self._enter(State.CONVEYOR_RESTART)

        # ---- CONVEYOR_RESTART ----
        elif s == State.CONVEYOR_RESTART:
            self.io.xy10_place_active = False
            self.io.conveyor_run = True
            if self.io.s3_vision:
                self._enter(State.PALLET_AT_VISION)

        # ---- PALLET_AT_VISION ----
        elif s == State.PALLET_AT_VISION:
            self.io.conveyor_run = False
            if self.time_in_state() > 0.3:
                self._enter(State.INSPECTION)

        # ---- INSPECTION ----
        elif s == State.INSPECTION:
            if self.time_in_state() > 0.5:
                self.io.inspection_done = True
                self._enter(State.PALLET_AT_QUALITY)

        # ---- PALLET_AT_QUALITY ----
        elif s == State.PALLET_AT_QUALITY:
            self.io.conveyor_run = True
            if self.io.s4_quality:
                self._enter(State.COMPLETE)

        # ---- COMPLETE ----
        elif s == State.COMPLETE:
            self.io.conveyor_run = False
            # Increment cycle count exactly once on entry to this state.
            # The flag is cleared by _enter() when we leave COMPLETE,
            # so the next time we reach COMPLETE we count again.
            if not self._counted_this_cycle:
                self.io.cycle_count += 1
                self._counted_this_cycle = True
            if self.time_in_state() > 0.5:
                self._enter(State.IDLE)

        # ---- FAULT ----
        elif s == State.FAULT:
            self.io.conveyor_run = False
            self.io.xy10_vacuum_cmd = False

    def get_state_log(self) -> list:
        return self._state_log

    def get_event_log(self) -> list:
        return self._event_log


if __name__ == "__main__":
    print("Running state machine self-test (target = 2 cycles)...")
    sm = ALIXStateMachine()
    dt = 0.005
    t = 0.0
    while sm.io.cycle_count < 2 and t < 60:
        cycle_t = t % 15.0
        sm.io.s1_input    = (1.0  <= cycle_t < 1.05)
        sm.io.s2_assembly = (5.0  <= cycle_t < 5.05)
        sm.io.s3_vision   = (12.0 <= cycle_t < 12.05)
        sm.io.s4_quality  = (14.95 <= cycle_t < 15.0) or (0.0 <= cycle_t < 0.05)
        sm.io.gripper_attached = (sm.state == State.XY10_PICK
                                   and sm.time_in_state() > 0.5)
        sm.step(t, dt)
        t += dt
    print(f"\nReached cycle_count = {sm.io.cycle_count} at t = {t:.2f} s\n")
    print("State transitions:")
    for et, ev in sm.get_event_log():
        print(f"  t={et:6.2f}s : {ev}")