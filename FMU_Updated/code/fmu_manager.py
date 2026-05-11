"""
fmu_manager.py — Generic FMI 2.0 Co-Simulation wrapper for ALIX digital twin.

Loads any FMU exported from 3DEXPERIENCE Behavior Modeling, exposes a clean
get/set/step interface, and translates between human-readable variable names
and FMU value references.

Author: ALIX internship project
Date: 2026-05
"""

from fmpy import read_model_description, extract
from fmpy.fmi2 import FMU2Slave
import shutil


class FMUWrapper:
    """
    Wrapper around an FMI 2.0 Co-Simulation FMU.

    Usage:
        fmu = FMUWrapper("ConveyorMotor.fmu", instance_name="conveyor")
        fmu.initialize(start_time=0.0)
        for k in range(1000):
            fmu.do_step(dt=0.005)
            speed = fmu.get_real("w_motor")
        fmu.close()
    """

    def __init__(self, fmu_path: str, instance_name: str = "fmu_instance"):
        self.fmu_path = fmu_path
        self.instance_name = instance_name

        # Read model description and unpack the FMU
        self.md = read_model_description(fmu_path)
        self.unpack_dir = extract(fmu_path)

        # Build name -> valueReference map
        self.vr_map = {}
        self.causality = {}
        self.types = {}
        self.units = {}
        for v in self.md.modelVariables:
            self.vr_map[v.name] = v.valueReference
            self.causality[v.name] = v.causality
            self.types[v.name] = v.type
            self.units[v.name] = v.unit if v.unit else "-"

        # Instantiate
        self.fmu = FMU2Slave(
            guid=self.md.guid,
            unzipDirectory=self.unpack_dir,
            modelIdentifier=self.md.coSimulation.modelIdentifier,
            instanceName=instance_name,
        )
        self.fmu.instantiate()
        self._t = 0.0
        self._initialized = False

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def initialize(self, start_time: float = 0.0, stop_time: float = None,
                   tolerance: float = 1e-4):
        """Setup experiment, enter and exit initialization mode."""
        self.fmu.setupExperiment(
            tolerance=tolerance,
            startTime=start_time,
            stopTime=stop_time,
        )
        self.fmu.enterInitializationMode()
        self.fmu.exitInitializationMode()
        self._t = start_time
        self._initialized = True

    def do_step(self, dt: float):
        """Advance simulation by dt seconds."""
        if not self._initialized:
            raise RuntimeError("Call initialize() before do_step()")
        self.fmu.doStep(
            currentCommunicationPoint=self._t,
            communicationStepSize=dt,
        )
        self._t += dt

    def close(self):
        """Free FMU instance and clean up unpacked files."""
        try:
            self.fmu.terminate()
        except Exception:
            pass
        try:
            self.fmu.freeInstance()
        except Exception:
            pass
        try:
            shutil.rmtree(self.unpack_dir, ignore_errors=True)
        except Exception:
            pass

    @property
    def t(self) -> float:
        """Current simulation time."""
        return self._t

    # ------------------------------------------------------------------
    # Get / set
    # ------------------------------------------------------------------

    def get_real(self, name: str) -> float:
        """Read a Real variable by name."""
        if name not in self.vr_map:
            raise KeyError(f"Variable '{name}' not in FMU. "
                           f"Available: {list(self.vr_map.keys())[:10]}...")
        return self.fmu.getReal([self.vr_map[name]])[0]

    def get_boolean(self, name: str) -> bool:
        """Read a Boolean variable by name."""
        if name not in self.vr_map:
            raise KeyError(f"Variable '{name}' not in FMU.")
        return bool(self.fmu.getBoolean([self.vr_map[name]])[0])

    def set_real(self, name: str, value: float):
        """Set a Real variable by name (only valid for inputs/parameters before init)."""
        if name not in self.vr_map:
            raise KeyError(f"Variable '{name}' not in FMU.")
        self.fmu.setReal([self.vr_map[name]], [float(value)])

    def set_boolean(self, name: str, value: bool):
        """Set a Boolean variable by name."""
        if name not in self.vr_map:
            raise KeyError(f"Variable '{name}' not in FMU.")
        self.fmu.setBoolean([self.vr_map[name]], [bool(value)])

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    def list_variables(self, causality_filter: str = None):
        """Return list of (name, causality, type, unit) tuples."""
        out = []
        for name, vr in self.vr_map.items():
            caus = self.causality[name]
            if causality_filter and caus != causality_filter:
                continue
            out.append((name, caus, self.types[name], self.units[name]))
        return out

    def print_summary(self):
        """Pretty-print FMU contents."""
        print(f"FMU: {self.fmu_path}")
        print(f"  Model: {self.md.modelName}")
        print(f"  FMI: {self.md.fmiVersion}")
        print(f"  Co-Sim id: {self.md.coSimulation.modelIdentifier}")
        print(f"  Variables: {len(self.vr_map)}")
        for caus in ("input", "output", "parameter"):
            vars_ = self.list_variables(caus)
            if vars_:
                print(f"  {caus.upper()}S ({len(vars_)}):")
                for name, _, type_, unit in vars_:
                    print(f"    {name:30s}  ({type_}, {unit})")
