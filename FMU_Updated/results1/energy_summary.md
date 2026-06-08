# Energy Analysis — ALIX Digital Twin

Total simulation: 30 s (2 production cycles)
Total electrical energy consumed: **3672.6 J = 1.0202 Wh**

## Per-subsystem breakdown

| Subsystem | Energy [J] | % of total | Avg power [W] |
|---|---:|---:|---:|
| Conveyor (induction motor) | 3321.5 | 90.4% | 110.72 |
| Sensors + PLC + HMI | 236.9 | 6.5% | 7.90 |
| Pneumatic (vacuum + cylinders) | 114.1 | 3.1% | 3.80 |
| XY10 Z axis (stepper) | 0.1 | 0.0% | 0.00 |
| XY10 X axis (stepper) | 0.1 | 0.0% | 0.00 |
| XY10 Y axis (stepper) | 0.0 | 0.0% | 0.00 |

## Observations

- **Conveyor (induction motor)** dominates the energy budget at 90% of total.
- The XY10 stepper motors contribute only marginally over a full cycle.
- The conveyor is the largest steady consumer.

## Energy efficiency opportunities

1. Conveyor power optimization.
2. Stepper holding current reduction.
3. Pneumatic on-demand control.
