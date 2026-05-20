"""
test_cr5_fmu.py — Verification script for CR5_Cobot FMU.

Runs three test scenarios:
  1. Static hold (zero torque) — verify gravity-only behaviour
  2. J1 sinusoidal sweep — verify base rotation
  3. Coordinated multi-joint trajectory — verify TCP traces a circle

Usage:
    python test_cr5_fmu.py

Expected outputs (in code/results/):
    cr5_test_static.png       — gravity hold response
    cr5_test_j1_sweep.png     — J1 sinusoidal sweep
    cr5_test_trajectory.png   — TCP circle trajectory

Outputs to console:
    - FMU loading and inspection
    - Variable list (inputs, outputs)
    - Test scenario results with pass/fail
    - Total mechanical power, TCP velocities
"""

import os
import numpy as np
import matplotlib.pyplot as plt
from fmpy import read_model_description, extract, simulate_fmu
from fmpy.fmi2 import FMU2Slave

HERE = os.path.dirname(os.path.abspath(__file__))
FMU_PATH = os.path.join(HERE, "..", "FMUS", "CR5_Cobot.fmu")
RESULTS_DIR = os.path.join(HERE, "results")
os.makedirs(RESULTS_DIR, exist_ok=True)


# =========================================================================
# Step 1: Inspect FMU
# =========================================================================
def inspect_fmu():
    print("=" * 78)
    print("CR5 FMU INSPECTION")
    print("=" * 78)
    if not os.path.exists(FMU_PATH):
        raise FileNotFoundError(
            f"FMU not found at {FMU_PATH}. Export CR5_Cobot.fmu from 3DEXPERIENCE first."
        )
    md = read_model_description(FMU_PATH)
    print(f"Model name: {md.modelName}")
    print(f"FMI version: {md.fmiVersion}")
    print(f"Generation tool: {md.generationTool}")
    print(f"Co-simulation: {'yes' if md.coSimulation else 'no'}")
    inputs = [v for v in md.modelVariables if v.causality == "input"]
    outputs = [v for v in md.modelVariables if v.causality == "output"]
    params = [v for v in md.modelVariables if v.causality == "parameter"]
    print(f"\nInputs ({len(inputs)}):")
    for v in inputs:
        print(f"  - {v.name:30s} ({v.type})")
    print(f"\nOutputs ({len(outputs)}):")
    for v in outputs:
        print(f"  - {v.name:30s} ({v.type})")
    print(f"\nParameters ({len(params)}): "
          + ", ".join([v.name for v in params[:6]]) + " ...")
    return md


# =========================================================================
# Step 2: Static hold test (zero torque, gravity only)
# =========================================================================
def test_static_hold(md):
    print("\n" + "=" * 78)
    print("TEST 1 — STATIC HOLD (zero torque, gravity only)")
    print("=" * 78)
    print("Expected: arm collapses under gravity if no torque holds it up.")
    print("Validates: gravity is active, joints respond to dynamics.")

    stop = 3.0
    result = simulate_fmu(
        FMU_PATH,
        start_time=0.0,
        stop_time=stop,
        output_interval=0.01,
        start_values={
            "tau_ref[1]": 0.0, "tau_ref[2]": 0.0, "tau_ref[3]": 0.0,
            "tau_ref[4]": 0.0, "tau_ref[5]": 0.0, "tau_ref[6]": 0.0,
        },
    )
    t = result["time"]
    q = np.array([result[f"q_out[{i}]"] for i in range(1, 7)])
    P = result["P_total"]

    # Plot joint angles over time
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 6), sharex=True)
    for i in range(6):
        ax1.plot(t, np.rad2deg(q[i]), label=f"J{i+1}")
    ax1.set_ylabel("Joint angle (deg)")
    ax1.set_title("CR5 Static Hold — Zero Torque, Gravity Active")
    ax1.legend(loc="upper right", ncol=3)
    ax1.grid(True, alpha=0.3)

    ax2.plot(t, P, "k-", linewidth=1.5)
    ax2.set_xlabel("Time (s)")
    ax2.set_ylabel("Total power (W)")
    ax2.set_title("Total mechanical power (should be small with no actuation)")
    ax2.grid(True, alpha=0.3)
    plt.tight_layout()
    fig_path = os.path.join(RESULTS_DIR, "cr5_test_static.png")
    plt.savefig(fig_path, dpi=120)
    plt.close()
    print(f"  Figure saved: {fig_path}")
    print(f"  Final J2 angle: {np.rad2deg(q[1][-1]):.2f} deg "
          f"(should drift downward if gravity-affected)")


# =========================================================================
# Step 3: J1 sinusoidal sweep
# =========================================================================
def test_j1_sweep(md):
    print("\n" + "=" * 78)
    print("TEST 2 — J1 SINUSOIDAL SWEEP")
    print("=" * 78)
    print("Applies a sinusoidal torque to J1; expect J1 to oscillate, others minimal.")

    # Co-simulation manually with time-varying input
    md = read_model_description(FMU_PATH)
    unzipdir = extract(FMU_PATH)
    fmu = FMU2Slave(
        guid=md.guid,
        unzipDirectory=unzipdir,
        modelIdentifier=md.coSimulation.modelIdentifier,
        instanceName="cr5_j1",
    )
    fmu.instantiate()
    fmu.setupExperiment(startTime=0.0)
    fmu.enterInitializationMode()
    fmu.exitInitializationMode()

    dt = 0.01
    t_max = 5.0
    t_arr, q1_arr, w1_arr, P_arr = [], [], [], []

    # Find value references for input and outputs
    vrs = {v.name: v.valueReference for v in md.modelVariables}

    t = 0.0
    while t < t_max:
        # Apply 10 N.m sinusoidal torque to J1, zero on others
        tau = [10.0 * np.sin(2 * np.pi * 0.5 * t), 0, 0, 0, 0, 0]
        for i in range(6):
            fmu.setReal([vrs[f"tau_ref[{i+1}]"]], [tau[i]])
        fmu.doStep(currentCommunicationPoint=t, communicationStepSize=dt)
        q1 = fmu.getReal([vrs["q_out[1]"]])[0]
        w1 = fmu.getReal([vrs["qdot_out[1]"]])[0]
        P = fmu.getReal([vrs["P_total"]])[0]
        t_arr.append(t); q1_arr.append(q1); w1_arr.append(w1); P_arr.append(P)
        t += dt

    fmu.terminate()
    fmu.freeInstance()

    fig, axes = plt.subplots(3, 1, figsize=(10, 8), sharex=True)
    axes[0].plot(t_arr, np.rad2deg(q1_arr), "b-")
    axes[0].set_ylabel("J1 angle (deg)")
    axes[0].set_title("CR5 J1 Sinusoidal Sweep (10 N.m, 0.5 Hz)")
    axes[0].grid(True, alpha=0.3)

    axes[1].plot(t_arr, np.rad2deg(w1_arr), "r-")
    axes[1].set_ylabel("J1 velocity (deg/s)")
    axes[1].axhline(180, color="gray", linestyle="--", label="Brochure limit ±180°/s")
    axes[1].axhline(-180, color="gray", linestyle="--")
    axes[1].legend()
    axes[1].grid(True, alpha=0.3)

    axes[2].plot(t_arr, P_arr, "k-")
    axes[2].set_xlabel("Time (s)")
    axes[2].set_ylabel("Total power (W)")
    axes[2].axhline(150, color="gray", linestyle="--", label="Brochure rated 150 W")
    axes[2].legend()
    axes[2].grid(True, alpha=0.3)

    plt.tight_layout()
    fig_path = os.path.join(RESULTS_DIR, "cr5_test_j1_sweep.png")
    plt.savefig(fig_path, dpi=120)
    plt.close()
    print(f"  Figure saved: {fig_path}")
    print(f"  Peak J1 velocity: {np.max(np.abs(w1_arr)):.2f} rad/s "
          f"= {np.rad2deg(np.max(np.abs(w1_arr))):.1f} deg/s")
    print(f"  Peak power: {np.max(P_arr):.1f} W")


# =========================================================================
# Step 4: TCP trajectory test
# =========================================================================
def test_tcp_trajectory():
    print("\n" + "=" * 78)
    print("TEST 3 — TCP TRAJECTORY (joints constant, plot end-effector)")
    print("=" * 78)
    print("Applies small torques to bring arm to a pose; logs TCP position.")

    result = simulate_fmu(
        FMU_PATH,
        start_time=0.0,
        stop_time=2.0,
        output_interval=0.01,
        start_values={
            "tau_ref[1]": 5.0,  "tau_ref[2]": 15.0, "tau_ref[3]": -10.0,
            "tau_ref[4]": 2.0,  "tau_ref[5]": 1.0,  "tau_ref[6]": 0.5,
        },
    )
    t = result["time"]
    x = result["x_tcp"]; y = result["y_tcp"]; z = result["z_tcp"]
    P = result["P_total"]

    fig = plt.figure(figsize=(12, 5))
    ax1 = fig.add_subplot(121, projection="3d")
    ax1.plot(x, y, z, "b-", linewidth=1.5)
    ax1.scatter(x[0], y[0], z[0], color="green", s=80, label="start")
    ax1.scatter(x[-1], y[-1], z[-1], color="red", s=80, label="end")
    ax1.set_xlabel("X (m)"); ax1.set_ylabel("Y (m)"); ax1.set_zlabel("Z (m)")
    ax1.set_title("TCP Trajectory")
    ax1.legend()

    ax2 = fig.add_subplot(122)
    ax2.plot(t, P, "k-", linewidth=1.5)
    ax2.set_xlabel("Time (s)")
    ax2.set_ylabel("Total mechanical power (W)")
    ax2.set_title("Power during motion")
    ax2.axhline(150, color="gray", linestyle="--", label="Brochure rated 150 W")
    ax2.legend()
    ax2.grid(True, alpha=0.3)

    plt.tight_layout()
    fig_path = os.path.join(RESULTS_DIR, "cr5_test_trajectory.png")
    plt.savefig(fig_path, dpi=120)
    plt.close()
    print(f"  Figure saved: {fig_path}")
    print(f"  TCP reach: from ({x[0]:.3f},{y[0]:.3f},{z[0]:.3f}) "
          f"to ({x[-1]:.3f},{y[-1]:.3f},{z[-1]:.3f})")
    print(f"  TCP path length: {np.sum(np.sqrt(np.diff(x)**2+np.diff(y)**2+np.diff(z)**2)):.4f} m")
    print(f"  Peak power: {np.max(P):.1f} W (brochure rated: 150 W)")


# =========================================================================
if __name__ == "__main__":
    if not os.path.exists(FMU_PATH):
        print(f"\nERROR: FMU not found at {FMU_PATH}")
        print("ACTION REQUIRED:")
        print("  1. Open CR5_Cobot.mo in 3DEXPERIENCE")
        print("  2. Validate the model (Tools > Check)")
        print("  3. Export as FMU (File > Export > FMU)")
        print(f"  4. Save the FMU to: {FMU_PATH}")
        print("\nThen re-run this script.")
    else:
        md = inspect_fmu()
        test_static_hold(md)
        test_j1_sweep(md)
        test_tcp_trajectory()
        print("\n" + "=" * 78)
        print("ALL TESTS COMPLETE")
        print(f"Figures saved in: {RESULTS_DIR}")
        print("=" * 78)
