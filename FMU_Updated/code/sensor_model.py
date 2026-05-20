"""
sensor_model.py — Logical photoelectric sensor models for the ALIX line.

Models the SICK GTB-6 family of through-beam/diffuse photoelectric sensors
used throughout the line. Each sensor has:
  - A position x (in meters) along the conveyor
  - A detection range (meters) — pallet must be within this range
  - A response time (seconds) — minimum dwell time to trigger
  - Optional miss probability (for noise simulation)

The SensorArray container holds the 4 standard ALIX line sensors:
  - S1_input    at x = 100 mm (input)
  - S2_assembly at x = 650 mm (XY10 pick position)
  - S3_vision   at x = 1100 mm (vision inspection)
  - S4_quality  at x = 1650 mm (quality check)

Sensor states are read by process_state_machine.py to trigger transitions.
"""

import random
from dataclasses import dataclass, field


@dataclass
class PhotoelectricSensor:
    """One photoelectric sensor at a fixed position on the conveyor."""
    id: str
    x: float                        # sensor position [m]
    range_m: float = 0.010          # detection half-width [m] (10 mm)
    response_time: float = 0.003    # minimum dwell time [s] (3 ms)
    miss_prob: float = 0.0          # noise: probability of false negative

    # State (internal)
    _last_state: bool = False
    _entry_time: float = -1.0       # time the pallet first entered the range

    def update(self, t: float, pallet_x: float) -> bool:
        """
        Update sensor state at time t given pallet position pallet_x (in m).
        Returns True if sensor is currently activated (pallet in range).
        """
        in_range = abs(pallet_x - self.x) <= self.range_m

        if in_range:
            if self._entry_time < 0:
                self._entry_time = t
            dwell = t - self._entry_time
            if dwell >= self.response_time:
                # Apply miss probability for noise simulation
                if self.miss_prob > 0 and random.random() < self.miss_prob:
                    self._last_state = False
                else:
                    self._last_state = True
            else:
                self._last_state = False
        else:
            self._entry_time = -1.0
            self._last_state = False

        return self._last_state

    def reset(self):
        """Reset sensor internal state (between pallet cycles)."""
        self._last_state = False
        self._entry_time = -1.0


class SensorArray:
    """A collection of sensors that can all be updated in one call."""

    def __init__(self, sensors: list):
        self.sensors = sensors
        self._id_to_sensor = {s.id: s for s in sensors}

    def __getitem__(self, sensor_id: str) -> PhotoelectricSensor:
        return self._id_to_sensor[sensor_id]

    def update_all(self, t: float, pallet_x: float) -> dict:
        """
        Update all sensors at time t with pallet position pallet_x (in m).
        Returns dict {sensor_id: bool_state}.
        """
        return {s.id: s.update(t, pallet_x) for s in self.sensors}

    def reset_all(self):
        """Reset all sensors (call when starting a new pallet cycle)."""
        for s in self.sensors:
            s.reset()


def default_alix_sensors() -> SensorArray:
    """
    Build the standard ALIX line sensor configuration.
    Positions are in METERS (S.I. units, consistent with the rest of the toolchain).
    """
    return SensorArray([
        PhotoelectricSensor(id="S1_input",    x=0.100),  # 100 mm
        PhotoelectricSensor(id="S2_assembly", x=0.650),  # 650 mm
        PhotoelectricSensor(id="S3_vision",   x=1.100),  # 1100 mm
        PhotoelectricSensor(id="S4_quality",  x=1.650),  # 1650 mm
    ])


# =====================================================================
# SELF-TEST
# =====================================================================
if __name__ == "__main__":
    print("Running sensor self-test...")
    print("(pallet moves from 0 to 2000 mm at 200 mm/s)")
    print()
    sensors = default_alix_sensors()

    # Use a small time step so the sensor's response_time (3 ms) is satisfied
    # within a few samples. Self-test at 10 ms steps for 10 s = 1000 samples.
    dt = 0.01            # 10 ms time step
    t_end = 10.0
    v = 0.200            # pallet velocity, 200 mm/s
    n_steps = int(t_end / dt)

    print(f"{'t (s)':>6}  {'x (mm)':>7}  {'S1':>3}  {'S2':>3}  {'S3':>3}  {'S4':>3}")
    print("-" * 40)

    # Print every 0.25 s for readability
    print_every = int(0.25 / dt)

    fired = {"S1_input": False, "S2_assembly": False,
             "S3_vision": False, "S4_quality": False}

    for k in range(n_steps):
        t = k * dt
        pallet_x = v * t                          # in meters
        states = sensors.update_all(t, pallet_x)

        # Track first firing of each sensor
        for sid, st in states.items():
            if st and not fired[sid]:
                fired[sid] = True
                print(f"  *** {sid} fired at t = {t:.2f} s, pallet_x = {pallet_x*1000:.0f} mm")

        # Periodic table print
        if k % print_every == 0:
            s1 = int(states["S1_input"])
            s2 = int(states["S2_assembly"])
            s3 = int(states["S3_vision"])
            s4 = int(states["S4_quality"])
            print(f"  {t:5.2f}  {pallet_x*1000:6.0f}    {s1}    {s2}    {s3}    {s4}")

    print()
    print("Sensor self-test summary:")
    print(f"  S1_input    fired: {fired['S1_input']}    (expected around t=0.5 s, x=100 mm)")
    print(f"  S2_assembly fired: {fired['S2_assembly']} (expected around t=3.25 s, x=650 mm)")
    print(f"  S3_vision   fired: {fired['S3_vision']}   (expected around t=5.5 s, x=1100 mm)")
    print(f"  S4_quality  fired: {fired['S4_quality']}  (expected around t=8.25 s, x=1650 mm)")

    if all(fired.values()):
        print("\n  ✅ All 4 sensors fired correctly. Sensor model works.")
    else:
        print("\n  ❌ One or more sensors did not fire. Check positions and units.")