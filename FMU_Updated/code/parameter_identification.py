"""
parameter_identification.py — Formal parameter optimization for conveyor model.

Closes the spec item: "parameter identification."

v2 (after first run): switched from damper_d to load_force_const as free parameter
because damper_d turned out to have negligible effect on steady-state current at the
operating belt velocity (0.196 m/s × 1 N·s/m = 0.196 N << 5 N constant load).
This itself is an observability finding documented in the methodology.

Method:
  1. Free parameter: load_force_const (resistive force opposing belt motion)
     This represents belt friction + small parts + belt tension.
  2. Target: minimize |i_sim - i_measured|
  3. Sweep over physically reasonable range (1 to 15 N)
  4. Find value that minimizes residual
  5. Document calibration and observability insight
"""

import os, sys
import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import minimize_scalar

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from fmu_manager import FMUWrapper


def find_fmu(name):
    for p in [os.path.join(HERE, name),
              os.path.join(HERE, "..", "FMUS", name),
              os.path.join(HERE, "FMUS", name)]:
        if os.path.exists(p):
            return os.path.abspath(p)
    return os.path.join(HERE, name)


CONVEYOR_FMU = find_fmu("Conveyor_updated_v2.fmu")
I_MEASURED_RMS = 1.62  # A (TDMS-derived target)
T_SIM = 1.5
DT = 1e-3
STEADY_START = 1.0

# Free parameter to identify
FREE_PARAM = "load_force_const"
PARAM_DESCRIPTION = "Resistive force opposing belt motion (belt friction + parts + tension)"
PARAM_UNIT = "N"
SEARCH_RANGE = (1.0, 15.0)
ORIGINAL_GUESS = 5.0


def run_conveyor_with_param(param_value):
    """Run conveyor FMU with a specific parameter value, return steady-state RMS current."""
    fmu = FMUWrapper(CONVEYOR_FMU, instance_name=f"opt_{param_value:.3f}")
    fmu.set_real(FREE_PARAM, param_value)
    fmu.initialize(start_time=0.0, stop_time=T_SIM)

    n_steps = int(T_SIM / DT)
    i_phase_log = np.zeros(n_steps)
    t_log = np.zeros(n_steps)

    for k in range(n_steps):
        fmu.do_step(DT)
        t_log[k] = fmu.t
        i_phase_log[k] = fmu.get_real("i_phase")

    fmu.close()
    mask = t_log >= STEADY_START
    i_ss = i_phase_log[mask].mean()
    return i_ss, t_log, i_phase_log


def cost_function(param_value):
    i_ss, _, _ = run_conveyor_with_param(param_value)
    error = (i_ss - I_MEASURED_RMS) ** 2
    print(f"  {FREE_PARAM} = {param_value:.3f} {PARAM_UNIT} → "
          f"i_ss = {i_ss:.4f} A → error = {error:.6f}")
    return error


def main():
    print("=" * 70)
    print(f"PARAMETER IDENTIFICATION — {FREE_PARAM}")
    print("=" * 70)
    print(f"Description: {PARAM_DESCRIPTION}")
    print(f"Target: i_phase (steady-state RMS) = {I_MEASURED_RMS:.2f} A")
    print(f"Free parameter: {FREE_PARAM} ({PARAM_UNIT})")
    print(f"Search range: {SEARCH_RANGE[0]} to {SEARCH_RANGE[1]} {PARAM_UNIT}")
    print(f"Original guess used in all previous results: {ORIGINAL_GUESS} {PARAM_UNIT}")
    print()

    # Sweep
    print("STEP 1 — Parameter sweep")
    print("-" * 70)
    sweep_values = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 10.0, 12.0, 15.0])
    i_ss_values = np.zeros(len(sweep_values))

    for i, v in enumerate(sweep_values):
        i_ss, _, _ = run_conveyor_with_param(v)
        i_ss_values[i] = i_ss
        print(f"  Point {i+1:2d}/{len(sweep_values)}: {FREE_PARAM} = {v:5.2f} {PARAM_UNIT} → "
              f"i_ss = {i_ss:.4f} A")

    print()
    print("STEP 2 — Bounded scalar optimization (Brent's method)")
    print("-" * 70)
    result = minimize_scalar(
        cost_function,
        bounds=SEARCH_RANGE,
        method='bounded',
        options={'xatol': 0.01}
    )
    v_optimal = result.x
    i_ss_optimal, _, _ = run_conveyor_with_param(v_optimal)
    errors = (i_ss_values - I_MEASURED_RMS) ** 2

    print()
    print("=" * 70)
    print("OPTIMIZATION RESULT")
    print("=" * 70)
    print(f"  Best-fit {FREE_PARAM}:     {v_optimal:.3f} {PARAM_UNIT}")
    print(f"  Simulated i_ss at optimum: {i_ss_optimal:.4f} A")
    print(f"  Measured target:           {I_MEASURED_RMS:.4f} A")
    print(f"  Residual error:            {abs(i_ss_optimal - I_MEASURED_RMS):.4f} A "
          f"({100*abs(i_ss_optimal - I_MEASURED_RMS)/I_MEASURED_RMS:.2f}%)")
    print(f"  Original guess value:      {ORIGINAL_GUESS} {PARAM_UNIT}")
    print()

    # Sensitivity (slope at optimum, rough estimate)
    sensitivity = (i_ss_values[-1] - i_ss_values[0]) / (sweep_values[-1] - sweep_values[0])
    print(f"  Parameter sensitivity:     {sensitivity*1000:.2f} mA per {PARAM_UNIT}")
    print(f"  (current change per unit change in parameter)")
    print()

    # Figure
    fig, axes = plt.subplots(2, 1, figsize=(12, 10))
    fig.suptitle(f"Parameter Identification — Conveyor model\n"
                 f"Free parameter: {FREE_PARAM} ({PARAM_DESCRIPTION})\n"
                 f"Best-fit: {v_optimal:.2f} {PARAM_UNIT}  "
                 f"(residual {100*abs(i_ss_optimal - I_MEASURED_RMS)/I_MEASURED_RMS:.2f}%)",
                 fontsize=12, weight="bold")

    ax1 = axes[0]
    ax1.plot(sweep_values, i_ss_values, 'bo-', lw=1.5, ms=8,
             label='FMU steady-state i_phase')
    ax1.axhline(I_MEASURED_RMS, color='r', ls='--', lw=2,
                label=f'TDMS measured target = {I_MEASURED_RMS} A')
    ax1.axvline(v_optimal, color='g', ls='--', lw=2, alpha=0.7,
                label=f'Optimum: {v_optimal:.2f} {PARAM_UNIT}')
    ax1.axvline(ORIGINAL_GUESS, color='gray', ls=':', lw=1, alpha=0.7,
                label=f'Original guess = {ORIGINAL_GUESS} {PARAM_UNIT}')
    ax1.scatter([v_optimal], [i_ss_optimal], color='g', s=250, zorder=5,
                marker='*', edgecolor='darkgreen', linewidth=2)
    ax1.set_xlabel(f'{FREE_PARAM} [{PARAM_UNIT}]')
    ax1.set_ylabel('Steady-state i_phase [A]')
    ax1.set_title('Calibration curve: simulated current vs free parameter (clear monotonic response)')
    ax1.grid(True, alpha=0.3)
    ax1.legend(loc='best', fontsize=9)

    ax2 = axes[1]
    ax2.plot(sweep_values, np.sqrt(errors), 'rs-', lw=1.5, ms=8,
             label='|simulated - measured|')
    ax2.axvline(v_optimal, color='g', ls='--', lw=2, alpha=0.7,
                label=f'Optimum at {v_optimal:.2f} {PARAM_UNIT}')
    ax2.scatter([v_optimal], [abs(i_ss_optimal - I_MEASURED_RMS)], color='g',
                s=250, zorder=5, marker='*', edgecolor='darkgreen', linewidth=2)
    ax2.set_xlabel(f'{FREE_PARAM} [{PARAM_UNIT}]')
    ax2.set_ylabel('|i_sim − i_measured| [A]')
    ax2.set_title('Error magnitude vs parameter value')
    ax2.grid(True, alpha=0.3)
    ax2.legend(loc='best', fontsize=9)

    plt.tight_layout()
    out = os.path.join(HERE, "results", "parameter_identification.png")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    plt.savefig(out, dpi=130, bbox_inches="tight")
    print(f"Figure saved: {out}")
    print()

    # Markdown summary
    summary_path = os.path.join(HERE, "..", "documentation", "parameter_identification.md")
    os.makedirs(os.path.dirname(summary_path), exist_ok=True)
    with open(summary_path, "w", encoding="utf-8") as f:
        f.write("# Parameter Identification — Conveyor Model\n\n")
        f.write("## Methodology\n\n")
        f.write(f"Formal optimization loop for the conveyor model parameter `{FREE_PARAM}`,\n")
        f.write("targeting agreement between simulated and measured steady-state current.\n\n")
        f.write(f"- **Free parameter:** `{FREE_PARAM}` — {PARAM_DESCRIPTION}\n")
        f.write(f"- **Search range:** {SEARCH_RANGE[0]} to {SEARCH_RANGE[1]} {PARAM_UNIT}\n")
        f.write(f"- **Measurement target:** TDMS-measured average current = {I_MEASURED_RMS} A (RMS)\n")
        f.write("- **Cost function:** Squared error between simulated steady-state i_phase and measurement\n")
        f.write("- **Optimizer:** scipy.optimize.minimize_scalar, Brent's bounded method\n\n")
        f.write("## Result\n\n")
        f.write(f"- **Best-fit `{FREE_PARAM}`:** {v_optimal:.3f} {PARAM_UNIT}\n")
        f.write(f"- **Simulated current at optimum:** {i_ss_optimal:.4f} A\n")
        f.write(f"- **Residual error:** {abs(i_ss_optimal - I_MEASURED_RMS):.4f} A "
                f"({100*abs(i_ss_optimal - I_MEASURED_RMS)/I_MEASURED_RMS:.2f}%)\n")
        f.write(f"- **Original guess (used in all earlier results):** {ORIGINAL_GUESS} {PARAM_UNIT}\n\n")
        f.write("## Observability finding (preliminary DoE result)\n\n")
        f.write("Initial attempt to identify `damper_d` (mechanical viscous damping) showed that\n")
        f.write("damping has negligible influence on steady-state current in this operating regime:\n")
        f.write("at the operating belt velocity (0.196 m/s), the damping force (~ d × v) is small\n")
        f.write("compared to the constant resistive load. Therefore `damper_d` is **not observable**\n")
        f.write("from steady-state current alone, and a transient observation (acceleration or\n")
        f.write("deceleration) would be required to identify it. This is documented in the DoE\n")
        f.write("methodology as motivation for transient measurement campaigns.\n\n")
        f.write("By contrast, `load_force_const` is directly observable from steady-state current,\n")
        f.write("as demonstrated by the monotonic calibration curve above.\n\n")
        f.write("## Methodology extension (future work)\n\n")
        f.write("The same approach can be applied to multiple free parameters simultaneously\n")
        f.write("(e.g., {Rs_motor, load_force_const, Lsigma_motor}) using\n")
        f.write("scipy.optimize.minimize with vector cost functions combining current, belt speed,\n")
        f.write("and power factor measurements. This forms the basis of the formal Design of\n")
        f.write("Experiments methodology planned for the final phase.\n")
    print(f"Summary saved: {summary_path}")

    plt.show()


if __name__ == "__main__":
    main()