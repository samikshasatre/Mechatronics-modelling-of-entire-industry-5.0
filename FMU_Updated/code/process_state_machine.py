"""
process_state_machine.py — PLC emulator for the ALIX line.

Emulates the Siemens S7-1200 logic of the XY10 station, with explicit
modeling of:
  - Continuously-running conveyor (PLC output Q2.0 Marche_Conv_U2)
  - Pneumatic indexer cylinders that physically stop containers on the
    moving belt (YV4 Indexeur, YV3 Séparateur, YV2 Bloqueur magasin)

This matches the real ALIX architecture documented in the ERM dossier
(DTXY1000003D, DTXY1000010C). The belt motor runs continuously throughout
production; containers/pallets are stopped at workstations by retractable
pneumatic cylinders, not by stopping the belt.
"""

from enum import IntEnum
from dataclasses import dataclass, field


class State(IntEnum):
    IDLE = 0
    CONVEYOR_START = 1
    PALLET_TRANSPORT = 2
    PALLET_AT_XY10 = 3
    XY10_PICK = 4
    XY10_PLACE = 5
    CONVEYOR_RESTART = 6   # kept for backward compat with state names, but no conveyor toggle now
    PALLET_AT_VISION = 7
    INSPECTION = 8
    PALLET_AT_QUALITY = 9
    COMPLETE = 10
    FAULT = 11


@dataclass
class ALIXIO:
    """All signals exchanged between PLC, sensors, and actuators."""
    # ---- Sensor inputs (from sensor_model.py) ----
    s1_input: bool = False
    s2_assembly: bool = False
    s3_vision: bool = False
    s4_quality: bool = False

    # ---- Conveyor (continuous in real line) ----
    conveyor_run: bool = False
    conveyor_speed_setpoint: float = 0.196  # m/s (matches model steady-state)

    # ---- Pneumatic indexer cylinders (NEW) ----
    # These physically stop containers on the moving belt
    indexer_pickup_extended: bool = False   # YV4 — holds container at XY10 pickup
    separator_extended: bool = False        # YV3 — holds product at separator
    magazine_blocker_extended: bool = True  # YV2 — default extended (holds magazine)

    # ---- XY10 robot commands ----
    xy10_x_target: float = 0.0
    xy10_z_target: float = 0.0
    xy10_vacuum_cmd: bool = False
    xy10_pick_active: bool = False
    xy10_place_active: bool = False

    # ---- XY10 status feedback ----
    gripper_attached: bool = False

    # ---- Cycle tracking ----
    cycle_count: int = 0


class ALIXStateMachine:
    """The PLC state machine. Drives all command signals based on sensor inputs."""

    # Time durations for each state (seconds)
    PICK_DURATION = 1.5
    PLACE_DURATION = 2.0
    INSPECTION_DURATION = 0.5
    RELEASE_DURATION = 0.05   # brief magazine release pulse

    def __init__(self):
        self.io = ALIXIO()
        self.state = State.IDLE
        self.state_entry_time = 0.0
        self._counted_this_cycle = False
        self._event_log = []

    def get_event_log(self):
        return list(self._event_log)

    def time_in_state(self):
        return self._now - self.state_entry_time

    def _enter(self, new_state, t):
        """Record state transition."""
        old = self.state.name
        new = new_state.name
        self._event_log.append((t, f"{old} -> {new}"))
        self.state = new_state
        self.state_entry_time = t
        self._counted_this_cycle = False

    def step(self, t, dt):
        """Advance the state machine one tick."""
        self._now = t
        time_in = self.time_in_state()

        # ===============================================================
        # CONVEYOR CONTROL — continuous during production (per ERM dossier)
        # The conveyor is ON for all states except IDLE-before-first-cycle
        # and FAULT. It does NOT toggle on/off within a cycle.
        # ===============================================================
        if self.state == State.IDLE and self.io.cycle_count == 0:
            self.io.conveyor_run = False
        elif self.state == State.FAULT:
            self.io.conveyor_run = False
        else:
            self.io.conveyor_run = True

        # ===============================================================
        # PNEUMATIC INDEXER CONTROL — these stop containers on moving belt
        # ===============================================================

        # Magazine blocker: extended by default, briefly retracted to release
        # a container during PALLET_TRANSPORT (a brief pulse at state entry)
        if self.state == State.PALLET_TRANSPORT and time_in < self.RELEASE_DURATION:
            self.io.magazine_blocker_extended = False  # releasing
        else:
            self.io.magazine_blocker_extended = True

        # Indexer pickup (YV4): holds container at XY10 pickup position
        # Extended during PALLET_AT_XY10 + XY10_PICK + XY10_PLACE
        # Retracted (container released) when pick-place complete
        self.io.indexer_pickup_extended = (
            self.state in (State.PALLET_AT_XY10,
                           State.XY10_PICK,
                           State.XY10_PLACE)
        )

        # Separator (YV3): briefly extended during pick to separate product
        self.io.separator_extended = (self.state == State.XY10_PICK)

        # ===============================================================
        # XY10 ROBOT CONTROL
        # ===============================================================

        # Reset XY10 commands by default
        if self.state in (State.IDLE, State.CONVEYOR_START,
                          State.PALLET_TRANSPORT, State.PALLET_AT_XY10,
                          State.CONVEYOR_RESTART, State.PALLET_AT_VISION,
                          State.INSPECTION, State.PALLET_AT_QUALITY,
                          State.COMPLETE, State.FAULT):
            self.io.xy10_pick_active = False
            self.io.xy10_place_active = False

        # XY10_PICK: move to pickup, go down, attach
        if self.state == State.XY10_PICK:
            self.io.xy10_pick_active = True
            self.io.xy10_x_target = 0.10   # to pickup column
            self.io.xy10_z_target = 0.05   # down to pickup
            self.io.xy10_vacuum_cmd = True  # vacuum ON

        # XY10_PLACE: move to place column, drop part, go up
        elif self.state == State.XY10_PLACE:
            self.io.xy10_place_active = True
            self.io.xy10_x_target = 0.20   # to placement column
            self.io.xy10_z_target = 0.0    # up
            if time_in > 1.0:
                self.io.xy10_vacuum_cmd = False  # release at end

        else:
            # All other states: XY10 returns to home, vacuum off
            self.io.xy10_x_target = 0.0
            self.io.xy10_z_target = 0.0
            self.io.xy10_vacuum_cmd = False

        # ===============================================================
        # STATE TRANSITIONS
        # ===============================================================
        if self.state == State.IDLE:
            if time_in >= 0.5:
                self._enter(State.CONVEYOR_START, t)

        elif self.state == State.CONVEYOR_START:
            if time_in >= 0.5:
                self._enter(State.PALLET_TRANSPORT, t)

        elif self.state == State.PALLET_TRANSPORT:
            if self.io.s2_assembly:
                self._enter(State.PALLET_AT_XY10, t)

        elif self.state == State.PALLET_AT_XY10:
            if time_in >= 0.3:
                self._enter(State.XY10_PICK, t)

        elif self.state == State.XY10_PICK:
            if self.io.gripper_attached and time_in >= self.PICK_DURATION:
                self._enter(State.XY10_PLACE, t)

        elif self.state == State.XY10_PLACE:
            if time_in >= self.PLACE_DURATION:
                self._enter(State.CONVEYOR_RESTART, t)

        elif self.state == State.CONVEYOR_RESTART:
            # Conveyor is already running; this state just releases the
            # indexer and waits for the pallet to reach the next sensor.
            # (Name kept for backward compatibility with logs.)
            if self.io.s3_vision:
                self._enter(State.PALLET_AT_VISION, t)

        elif self.state == State.PALLET_AT_VISION:
            if time_in >= 0.3:
                self._enter(State.INSPECTION, t)

        elif self.state == State.INSPECTION:
            if time_in >= self.INSPECTION_DURATION:
                self._enter(State.PALLET_AT_QUALITY, t)

        elif self.state == State.PALLET_AT_QUALITY:
            if self.io.s4_quality:
                self._enter(State.COMPLETE, t)

        elif self.state == State.COMPLETE:
            if not self._counted_this_cycle:
                self.io.cycle_count += 1
                self._counted_this_cycle = True
            if time_in >= 0.5:
                self._enter(State.IDLE, t)


# =====================================================================
# Self-test
# =====================================================================
if __name__ == "__main__":
    sm = ALIXStateMachine()
    print(f"Initial state: {sm.state.name}")
    print(f"Initial conveyor_run: {sm.io.conveyor_run}")
    print(f"Initial indexer_pickup_extended: {sm.io.indexer_pickup_extended}")
    # Simulate forward
    dt = 0.005
    for k in range(int(30 / dt)):
        t = k * dt
        # Fake sensor inputs to drive transitions
        if 0.5 < t < 1.0: sm.io.s1_input = True
        if 3.8 < t < 4.0: sm.io.s2_assembly = True
        if 5.0 < t < 6.0: sm.io.gripper_attached = True
        if 9.8 < t < 10.0: sm.io.s3_vision = True
        if 13.4 < t < 13.6: sm.io.s4_quality = True
        sm.step(t, dt)
    print(f"\nAfter 30 s simulation:")
    print(f"  Final state: {sm.state.name}")
    print(f"  Cycles completed: {sm.io.cycle_count}")
    print(f"  Event log: {len(sm.get_event_log())} transitions")