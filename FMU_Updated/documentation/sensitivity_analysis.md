# Sensitivity & Observability Analysis — Conveyor Model

## Purpose

Combined deliverable closing two spec items:

1. **Parameter identification** — by identifying which parameters are observable from which measurements
2. **Foundation for Design of Experiments (DoE) methodology** — by mapping parameter-measurement pairs that enable identification

## Method

For each of 6 free parameters, the parameter is varied over a physically realistic range and the response of three steady-state outputs is measured: current i_ss, belt speed v_ss, and power P_ss. The normalized sensitivity is computed as `(Δoutput / output) / (Δparam / param)`, giving a dimensionless quantity that directly indicates observability.

## Sensitivity matrix

| Parameter | Δi_ss / Δp | Δv_ss / Δp | ΔP_ss / Δp | Observable? |
|---|---:|---:|---:|---|
| `Rs_motor` (Stator resistance) | -0.0110 | -0.0000 | 0.8905 | ✗ requires transient measurement |
| `Lm_motor` (Magnetizing inductance) | -0.9496 | 0.0004 | -1.3274 | ✓ identifiable from steady-state |
| `Lsigma_motor` (Leakage inductance) | -0.0624 | -0.0000 | -0.1128 | ✗ requires transient measurement |
| `V_peak` (Peak supply voltage) | 1.0008 | 0.0007 | 1.8441 | ✓ identifiable from steady-state |
| `load_force_const` (Resistive belt load) | -0.0005 | -0.0005 | 0.0840 | ✗ requires transient measurement |
| `damper_d` (Belt+bearing damping) | -0.0001 | -0.0000 | 0.0087 | ✗ requires transient measurement |

## Key findings

**Identifiable from steady-state current measurement:**
- `Lm_motor`
- `V_peak`

**NOT identifiable from steady-state alone (require transient measurements):**
- `Rs_motor`
- `Lsigma_motor`
- `load_force_const`
- `damper_d`

## Implication for DoE methodology

This analysis reveals that for a small motor running at light load (~3% of rated torque), the mechanical parameters (`damper_d`, `load_force_const`) contribute negligibly to the steady-state current draw. The motor current is dominated by the magnetizing branch.

Therefore, the Design of Experiments methodology must combine:

1. **Steady-state experiments** to identify electrical parameters (Rs, V_peak, Lm)
2. **Transient experiments** (startup torque ramp, deceleration) to identify mechanical parameters (damper_d, load_force_const)
3. **Loaded experiments** (heavier load that activates the mechanical chain) to make load force observable

This pairing of parameter-with-experiment is the core principle of a useful DoE methodology and will guide the experimental campaign in the final phase.
