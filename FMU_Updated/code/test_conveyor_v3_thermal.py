"""
test_conveyor_v3_thermal.py - Verify Conveyor_updated_v3.fmu thermal coupling.

Validates the v3 thermal extension:
  - Confirms T_motor is exposed as FMU output
  - Runs 60s simulation matching 3DEXPERIENCE conditions
  - Plots T_motor rise, P_elec, i_phase_inst
  - Compares final values against 3DEXPERIENCE reference at t=60s

Reference values from 3DEXPERIENCE simulation at t=60s:
  T_motor      = 305.097 K (31.95 degC)
  i_phase      = 1.62856 A
  P_elec       = 107.962 W
  i_phase_inst = AC sinusoid, peak +-2.30 A
"""

import os
import sys
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
        print("Place the exported FMU in FMUS/ folder.")
        return

    print("=" * 70)
    print("CONVEYOR V3 THERMAL FMU VERIFICATION")
    print("=" * 70)
    print(f"FMU path: {fmu_path}")
    print()

    # ---------- Inspect FMU ----------
    md = read_model_description(fmu_path)
    print(f"Model name:      {md.modelName}")
    print(f"FMI version:     {md.fmiVersion}")
    print(f"Generation tool: {md.generationTool}")
    print()

    outputs = [v for v in md.modelVariables if v.causality == "output"]
    output_names = [v.name for v in outputs]
    print(f"FMU Outputs ({len(outputs)}):")
    for v in outputs:
        new_tag = "  <-- NEW v3 thermal" if v.name == "T_motor" else ""
        print(f"  {v.name:25s} ({v.type}, {v.unit or '-'}){new_tag}")
    print()

    if "T_motor" not in output_names:
        print("ERROR: T_motor not exposed in FMU.")
        print("Re-export with useThermalPort=true and TemperatureSensor connected.")
        return

    # ---------- Build value reference map ----------
    track = ["T_motor", "i_phase", "i_phase_inst", "P_elec",
             "w_motor", "tau_shaft", "v_belt"]
    vr = {v.name: v.valueReference for v in md.modelVariables if v.name in track}
    missing = [n for n in track if n not in vr]
    if missing:
        print(f"WARNING: missing variables: {missing}")

    # ---------- Setup and initialize ----------
    print("Setting up FMU instance...")
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

    # ---------- Run 60s simulation ----------
    print("Running 60s simulation at dt=0.01s...")
    t_end = 60.0
    dt = 0.01
    n = int(t_end / dt)

    t_log = np.zeros(n)
    T_motor = np.zeros(n)
    i_phase = np.zeros(n)
    i_phase_inst = np.zeros(n)
    P_elec = np.zeros(n)
    w_motor = np.zeros(n)

    t = 0.0
    for k in range(n):
        fmu.doStep(currentCommunicationPoint=t, communicationStepSize=dt)
        t += dt
        t_log[k] = t
        T_motor[k] = fmu.getReal([vr["T_motor"]])[0]
        i_phase[k] = fmu.getReal([vr["i_phase"]])[0]
        i_phase_inst[k] = fmu.getReal([vr["i_phase_inst"]])[0]
        P_elec[k] = fmu.getReal([vr["P_elec"]])[0]
        w_motor[k] = fmu.getReal([vr["w_motor"]])[0]

    fmu.terminate()
    fmu.freeInstance()
    print("Simulation complete.")
    print()

    # ---------- Compare to 3DEXPERIENCE reference ----------
    ref = {
        "T_motor":      (305.097, "K"),
        "i_phase":      (1.62856, "A"),
        "P_elec":       (107.962, "W"),
    }
    actual = {
        "T_motor":      T_motor[-1],
        "i_phase":      i_phase[-1],
        "P_elec":       P_elec[-1],
    }

    print("=" * 70)
    print("FINAL VALUES AT t=60s - PYTHON FMU vs 3DEXPERIENCE")
    print("=" * 70)
    print(f"{'Variable':15s} {'Python':>14s} {'3DEXPERIENCE':>14s} {'Diff':>10s}  Status")
    print("-" * 70)
    all_ok = True
    for name, (ref_val, unit) in ref.items():
        act = actual[name]
        diff = act - ref_val
        rel = abs(diff) / abs(ref_val) * 100 if ref_val != 0 else 0
        status = "OK" if rel < 1.0 else "CHECK"
        if status == "CHECK":
            all_ok = False
        print(f"{name:15s} {act:14.4f} {ref_val:14.4f} {diff:10.4f}  {status} ({rel:.2f}%)")
    print()

    # Sanity checks
    print("PHYSICAL SANITY CHECKS:")

    # 1. Temperature is rising
    dT = T_motor[-1] - T_motor[0]
    if dT > 0:
        print(f"  [OK] Temperature rose by {dT:.2f} K (thermal coupling active)")
    else:
        print(f"  [FAIL] Temperature did not rise - check thermal connections")

    # 2. AC waveform is sinusoidal (last 0.5s)
    zoom_start = int(58.0 / dt)
    ac_window = i_phase_inst[zoom_start:]
    ac_peak = np.max(np.abs(ac_window))
    ac_mean = np.mean(ac_window)
    if abs(ac_mean) < 0.1 and ac_peak > 1.5:
        print(f"  [OK] i_phase_inst is symmetric AC: peak {ac_peak:.2f} A, mean {ac_mean:.3f} A")
    else:
        print(f"  [CHECK] i_phase_inst: peak {ac_peak:.2f} A, mean {ac_mean:.3f} A")

    # 3. Energy balance
    P_mech = w_motor[-1] * 0.0065  # very rough, tau approx
    P_loss_asymp = P_elec[-1] - P_mech
    dT_asymp_predicted = P_loss_asymp / 1.5  # G = 1.5 W/K
    print(f"  [INFO] Asymptotic temperature rise predicted: {dT_asymp_predicted:.1f} K")
    print(f"  [INFO] At t=60s should be ~16.5% of that = {dT_asymp_predicted * 0.165:.1f} K")
    print(f"  [INFO] Actual rise at 60s: {dT:.2f} K")
    print()

    if all_ok:
        print("RESULT: FMU verified - thermal coupling working correctly.")
    else:
        print("RESULT: Some values differ from reference. Check setup.")
    print()

    # ---------- Plot ----------
    fig, axes = plt.subplots(3, 1, figsize=(12, 10))
    fig.suptitle("Conveyor V3 Thermal FMU Verification - 60s Simulation",
                 fontsize=13, weight="bold")

    # Panel 1: Temperature rise
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

    # Panel 2: Electrical input power
    axes[1].plot(t_log, P_elec, 'b-', lw=1.2)
    axes[1].axhline(107.96, color='red', ls='--', lw=0.8, alpha=0.7,
                    label='3DEXPERIENCE reference (107.96 W)')
    axes[1].set_xlabel('Time [s]')
    axes[1].set_ylabel('P_elec [W]')
    axes[1].set_title('Panel 2: Electrical input power (preserved from v2)')
    axes[1].grid(True)
    axes[1].legend(loc='lower right')
    axes[1].set_ylim(0, 200)

    # Panel 3: AC current waveform (last 100 ms zoom)
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
    out_path = os.path.join(HERE, "results", "conveyor_v3_thermal_test.png")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    plt.savefig(out_path, dpi=140, bbox_inches="tight")
    print(f"Figure saved: {out_path}")
    plt.show()


if __name__ == "__main__":
    main()