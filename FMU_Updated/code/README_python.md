# ALIX Digital Twin — Python FMU Validation

This folder contains the Python code that closes the
**3DEXPERIENCE → FMU → Python** toolchain for the ALIX digital twin.

## Files

| File                | Purpose                                                  |
|---------------------|----------------------------------------------------------|
| `fmu_manager.py`    | Generic FMI 2.0 Co-Simulation wrapper class             |
| `test_conveyor.py`  | Loads `Conveyor_updated.fmu`, runs 5-s test, plots       |
| `test_xy10.py`      | Loads `XY10Station.fmu`, runs 10-s pick-and-place test   |

## Required folder layout

Place all four files together in one folder:

```
ALIX_DigitalTwin/
├── fmu_manager.py
├── test_conveyor.py
├── test_xy10.py
├── Conveyor_updated.fmu      <-- exported from 3DEXPERIENCE
├── XY10Station.fmu           <-- exported from 3DEXPERIENCE
└── results/                  <-- created automatically, holds plots
```

## One-time setup (Windows)

Open a terminal (PowerShell or Anaconda Prompt) and run:

```
pip install fmpy numpy matplotlib
```

That installs FMPy (the FMI master toolkit), NumPy, and Matplotlib.

## Running the tests

From the same folder:

```
python test_conveyor.py
python test_xy10.py
```

Each script will:

1. Open the FMU and print its variable map
2. Run a co-simulation in lockstep with `dt = 1 ms`
3. Log all output channels at every step
4. Print final values vs. the 3DEXPERIENCE reference
5. Save a multi-panel plot to `results/`
6. Show the plot interactively

## Expected outputs

### test_conveyor.py

* All six output channels reproduce the values seen in 3DEXPERIENCE:
  * `w_motor` settles at ~156.7 rad/s (1497 rpm)
  * `tau_shaft` ~0.0065 N·m
  * `i_phase` ~1.6 A
  * `P_elec` ~108 W
  * `v_belt` ~0.196 m/s
  * `x_belt` reaches ~0.98 m at t = 5 s
* RESULT line says: ✅ toolchain closed.

### test_xy10.py

* X axis steps to 200 mm at t = 1 s, Z to 50 mm at t = 4 s.
* Vacuum pulls the chamber to ~30 kPa starting at t = 5 s.
* `gripper_attached` becomes `True` shortly after t = 5 s.
* Peak `i_x` ≈ 1.85 A, peak `i_z` ≈ 1.09 A, peak `P_elec` ≈ 87 W.
* RESULT line says: ✅ TDMS-validated and Python-callable.

## Known limitation of the current XY10 FMU

The XY10 FMU was exported from the **DynamicTest** version of the model,
which has the test sequence baked in (`t_x_step=1.0 s`, `t_z_step=4.0 s`,
`t_vac_step=5.0 s`, with `x_target=0.20 m` and `z_target=0.05 m`). The
parameters `x_target` and `z_target` are tunable from Python, but the
**timing is fixed inside the FMU**.

For the integration phase (Python state-machine driving the XY10 in
real time), we will need to re-export the XY10 from a version that has
`RealInput x_cmd, RealInput z_cmd, BooleanInput vacuum_cmd` declared as
top-level connectors. That is a 5-minute change in the Modelica model
plus a re-export.

## Next steps after this validation passes

1. Re-export the XY10 with proper FMI inputs for state-machine control.
2. Build the `process_state_machine.py` (PLC emulator).
3. Build `sensor_model.py` (logical SICK photoelectric sensors).
4. Build `main_alix_simulation.py` that wires conveyor + XY10 + state
   machine + sensors into one end-to-end run.
