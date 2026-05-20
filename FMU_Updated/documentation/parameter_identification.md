# Parameter Identification — Conveyor Model

## Methodology

Formal optimization loop for the conveyor model parameter `load_force_const`,
targeting agreement between simulated and measured steady-state current.

- **Free parameter:** `load_force_const` — Resistive force opposing belt motion (belt friction + parts + tension)
- **Search range:** 1.0 to 15.0 N
- **Measurement target:** TDMS-measured average current = 1.62 A (RMS)
- **Cost function:** Squared error between simulated steady-state i_phase and measurement
- **Optimizer:** scipy.optimize.minimize_scalar, Brent's bounded method

## Result

- **Best-fit `load_force_const`:** 12.954 N
- **Simulated current at optimum:** 1.6285 A
- **Residual error:** 0.0085 A (0.52%)
- **Original guess (used in all earlier results):** 5.0 N

## Observability finding (preliminary DoE result)

Initial attempt to identify `damper_d` (mechanical viscous damping) showed that
damping has negligible influence on steady-state current in this operating regime:
at the operating belt velocity (0.196 m/s), the damping force (~ d × v) is small
compared to the constant resistive load. Therefore `damper_d` is **not observable**
from steady-state current alone, and a transient observation (acceleration or
deceleration) would be required to identify it. This is documented in the DoE
methodology as motivation for transient measurement campaigns.

By contrast, `load_force_const` is directly observable from steady-state current,
as demonstrated by the monotonic calibration curve above.

## Methodology extension (future work)

The same approach can be applied to multiple free parameters simultaneously
(e.g., {Rs_motor, load_force_const, Lsigma_motor}) using
scipy.optimize.minimize with vector cost functions combining current, belt speed,
and power factor measurements. This forms the basis of the formal Design of
Experiments methodology planned for the final phase.
