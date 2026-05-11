"""
sensor_model.py — Logical models of SICK photoelectric sensors used on the ALIX line.

A photoelectric sensor (SICK GTB-6 type) fires when an object (pallet, part) crosses
its detection beam. We model this purely logically based on the geometric position
of the moving object on the conveyor:

  - The sensor has a fixed position x_sensor along the belt.
  - The detection beam has a small width (detection_range, ~10 mm).
  - The sensor is "active" (output=True) when |x_object - x_sensor| < detection_range/2.
  - A small response delay (~3 ms) is applied to the rising/falling edges to match
    real photoelectric sensor latency.
  - Optional miss probability (default 0) can be added to model unreliable detection.

This is a logical/discrete model — no physics inside the sensor itself, only the
mapping from physical position to Boolean output.
"""

import random


class PhotoelectricSensor:
    """
    Logical SICK photoelectric sensor.

    Triggers when the object crosses its position within detection_range.
    Includes response delay and optional miss probability.
    """

    def __init__(self, sensor_id: str, position_x_m: float,
                 detection_range_m: float = 0.010,
                 response_time_s: float = 0.003,
                 miss_prob: float = 0.0):
        """
        Args:
            sensor_id: human-readable label, e.g. "S1_input"
            position_x_m: location along the belt, in meters from belt start
            detection_range_m: beam width (detection zone), in meters
            response_time_s: rising/falling edge delay, in seconds
            miss_prob: probability of a missed detection (0.0 = perfect)
        """
        self.id = sensor_id
        self.x = position_x_m
        self.r = detection_range_m
        self.tau = response_time_s
        self.miss_prob = miss_prob

        # Internal state
        self._raw_state = False     # instantaneous (no delay)
        self._delayed_state = False # what the PLC sees
        self._t_last_change = 0.0   # when the raw state last changed

    def update(self, t: float, object_x: float) -> bool:
        """
        Update the sensor with the current object position and return its output.

        Args:
            t: simulation time (s)
            object_x: position of the object on the belt (m)

        Returns:
            Boolean output of the sensor (True = object detected)
        """
        # Instantaneous detection
        new_raw = abs(object_x - self.x) < (self.r / 2.0)

        # Edge detection
        if new_raw != self._raw_state:
            self._raw_state = new_raw
            self._t_last_change = t

        # Apply response delay
        if (t - self._t_last_change) >= self.tau:
            # Optional miss probability on rising edge
            if self._raw_state and random.random() < self.miss_prob:
                self._delayed_state = False  # miss
            else:
                self._delayed_state = self._raw_state

        return self._delayed_state

    @property
    def state(self) -> bool:
        """Current Boolean output (without re-updating)."""
        return self._delayed_state

    def reset(self):
        """Reset internal state to no detection."""
        self._raw_state = False
        self._delayed_state = False
        self._t_last_change = 0.0

    def __repr__(self):
        return (f"PhotoelectricSensor(id='{self.id}', x={self.x*1000:.0f}mm, "
                f"state={self._delayed_state})")


class SensorArray:
    """
    Convenience container for multiple sensors along a conveyor.
    Allows updating all sensors in one call.
    """

    def __init__(self, sensors: list = None):
        self.sensors = sensors or []
        # Build a lookup by id
        self._by_id = {s.id: s for s in self.sensors}

    def add(self, sensor: PhotoelectricSensor):
        """Add a sensor to the array."""
        self.sensors.append(sensor)
        self._by_id[sensor.id] = sensor

    def update_all(self, t: float, object_x: float) -> dict:
        """
        Update all sensors with the same object position.

        Returns:
            Dict {sensor_id: bool}
        """
        return {s.id: s.update(t, object_x) for s in self.sensors}

    def __getitem__(self, sensor_id: str) -> PhotoelectricSensor:
        return self._by_id[sensor_id]

    def reset_all(self):
        for s in self.sensors:
            s.reset()


# ---------------------------------------------------------------------------
# Default sensor layout for ALIX line
# ---------------------------------------------------------------------------
# These positions are starting estimates. Update with measured values from
# the lab session (see assumptions.md for details).
#
# Layout (from belt start to belt end, x in meters):
#   S1 at 0.10 m — pallet input detection
#   S2 at 0.65 m — pallet at assembly station (XY10)
#   S3 at 1.10 m — pallet at vision station
#   S4 at 1.65 m — pallet at quality control

def default_alix_sensors() -> SensorArray:
    """Build the standard ALIX sensor layout."""
    arr = SensorArray()
    arr.add(PhotoelectricSensor("S1_input",    position_x_m=0.10))
    arr.add(PhotoelectricSensor("S2_assembly", position_x_m=0.65))
    arr.add(PhotoelectricSensor("S3_vision",   position_x_m=1.10))
    arr.add(PhotoelectricSensor("S4_quality",  position_x_m=1.65))
    return arr


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Quick test: simulate a pallet moving from x=0 to x=2.0 at v=0.2 m/s over 10s
    print("Running sensor self-test...")
    arr = default_alix_sensors()

    dt = 0.001
    v = 0.2
    print(f"\n{'t (s)':>6} {'x (mm)':>8} {'S1':>4} {'S2':>4} {'S3':>4} {'S4':>4}")
    for k in range(0, 10001, 500):  # print every 0.5 s
        t = k * dt
        x = v * t
        states = arr.update_all(t, x)
        print(f"{t:6.2f} {x*1000:8.0f} "
              f"{int(states['S1_input']):>4} "
              f"{int(states['S2_assembly']):>4} "
              f"{int(states['S3_vision']):>4} "
              f"{int(states['S4_quality']):>4}")

    print("\nSensor self-test passed if you saw 1's appear at the expected positions:")
    print("  S1 around t=0.5 s (x=100mm)")
    print("  S2 around t=3.25 s (x=650mm)")
    print("  S3 around t=5.5 s (x=1100mm)")
    print("  S4 around t=8.25 s (x=1650mm)")
