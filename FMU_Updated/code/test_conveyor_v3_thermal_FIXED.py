"""
test_conveyor_v3_thermal_FIXED.py - Fixed version of the v3 thermal verification.

FIX (vs original): Panel 2 (P_elec) now skips the startup transient (first 1 s)
and uses a tight y-axis range (105-115 W) so the steady-state value is clearly
visible alongside the 3DEXPERIENCE reference line.

All other panels are unchanged.
"""

import os
import numpy as np
import matplotlib.pyplot as plt
from fmpy import read_model_description, extract
from fmpy.fmi2 import FMU2Slave

HERE = os.path.dirname(os.path.abspath(__file__))


def find_fmu(name):
    for p in [os.path.join(HERE, name),
              os.path.join(HERE, "..", "FMUS", name),
              os.path.join(HERE, "FMUS", name)]:
        if os.path.exists(p):
            return os.path.abspath(p)
    return None


def main():
    fmu_path = find_fmu("Conveyor_updated_v3.fmu")
    if fmu_path is None:
        print("ERROR: Conveyor_updated_v3.fmu not found.")
        return

    print("=" * 70)
    print("CONVEYOR V3 THERMAL FMU VERIFICATION - FIXED PLOT")
    print("=" * 70)

    md = read_model_description(fmu_path)
    print(f"Model: {md.modelName}  |  FMI {md.fmiVersion}")
    print()

    track = ["T_motor", "i_phase", "i_phase_inst", "P_elec", "w_motor"]
    vr = {v.name: v.valueReference for v in md.modelVariables if v.name in track}

    unzipdir = extract(fmu_path)
    fmu = FMU2Slave(
        guid=md.guid,
        unzipDirectory=unzipdir,
        modelIdentifier=md.coSimulation.modelIdentifier,
        instanceName="conveyor_v3_test"
    )
    fmu.instantiate()
    fmu.setupExperiment(startTime=0.0, stopTime=60.0)
    fmu.enterInitializationMode()
    fmu.exitInitializationMode()

    t_end = 60.0
    dt = 0.01
    n = int(t_end / dt)

    t_log = np.zeros(n)
    T_motor = np.zeros(n)
    i_phase_inst = np.zeros(n)
    P_elec = np.zeros(n)

    print("Running 60s simulation at dt=0.01s...")
    t = 0.0
    for k in range(n):
        fmu.doStep(currentCommunicationPoint=t, communicationStepSize=dt)
        t += dt
        t_log[k] = t
        T_motor[k] = fmu.getReal([vr["T_motor"]])[0]
        i_phase_inst[k] = fmu.getReal([vr["i_phase_inst"]])[0]
        P_elec[k] = fmu.getReal([vr["P_elec"]])[0]

    fmu.terminate()
    fmu.freeInstance()
    print("Done.\n")

    # ---------- Plot ----------
    fig, axes = plt.subplots(3, 1, figsize=(12, 10))
    fig.suptitle("Conveyor V3 Thermal FMU Verification - 60s Simulation",
                 fontsize=13, weight="bold")

    # Panel 1: Temperature rise (unchanged from before)
    axes[0].plot(t_log, T_motor - 273.15, 'r-', lw=2.0, label='Motor body temperature')
    axes[0].axhline(20, color='gray', ls='--', lw=0.8, label='Ambient (20 degC)')
    axes[0].set_xlabel('Time [s]')
    axes[0].set_ylabel('Temperature [degC]')
    axes[0].set_title('Panel 1: Motor body temperature rise (thermal coupling)')
    axes[0].grid(True)
    axes[0].legend(loc='lower right')
    axes[0].text(0.02, 0.95,
                 f'Final T_motor: {T_motor[-1]-273.15:.2f} degC\n'
                 f'Rise: {T_motor[-1]-293.15:.2f} K in 60s\n'
                 f'Asymptotic: ~{(P_elec[-1]/1.5):.1f} K (tau=333s)',
                 transform=axes[0].transAxes, fontsize=9,
                 verticalalignment='top',
                 bbox=dict(facecolor='lightyellow', edgecolor='gray', alpha=0.9))


    skip = int(1.0 / dt)  # skip first 1 second of transient
    axes[1].plot(t_log[skip:], P_elec[skip:], 'b-', lw=1.2,
                 label='P_elec (steady-state region)')
    axes[1].axhline(107.96, color='red', ls='--', lw=1.0,
                    label='3DEXPERIENCE reference (107.96 W)')
    axes[1].set_xlabel('Time [s]')
    axes[1].set_ylabel('P_elec [W]')
    axes[1].set_title('Panel 2: Electrical input power (steady state, transient cropped)')
    axes[1].grid(True)
    axes[1].legend(loc='lower right')
    axes[1].set_ylim(105, 115)  # tight range around 108 W
    axes[1].set_xlim(1, 60)
    # =================================================================

    # Panel 3: AC current waveform (unchanged)
    zoom_n = int(0.1 / dt)
    z_t = t_log[-zoom_n:]
    z_i = i_phase_inst[-zoom_n:]
    axes[2].plot(z_t, z_i, 'g-', lw=1.0)
    axes[2].axhline(0, color='gray', lw=0.5)
    axes[2].set_xlabel('Time [s]')
    axes[2].set_ylabel('i_phase_inst [A]')
    axes[2].set_title(f'Panel 3: Instantaneous phase A current (last 100 ms, peak ~{np.max(np.abs(z_i)):.2f} A)')
    axes[2].grid(True)

    plt.tight_layout()
    out_path = os.path.join(HERE, "results", "conveyor_v3_thermal_test_FIXED.png")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    plt.savefig(out_path, dpi=140, bbox_inches="tight")
    print(f"Figure saved: {out_path}")
    plt.show()


if __name__ == "__main__":
    main()