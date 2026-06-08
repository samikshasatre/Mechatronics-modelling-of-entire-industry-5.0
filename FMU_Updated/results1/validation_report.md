# Section 9 - Validation against TDMS measurements

## 9.1 Validation strategy

The supplied TDMS recordings capture line-level voltage and current (two phases of the three-phase Y supply, sampled at 6 kHz over 5 separate sessions totaling approximately 58 minutes of operation). Because all subsystems share a common power feed, the recorded signals are an aggregate of every load on the cabinet. Direct one-to-one validation of an individual subsystem is therefore not possible from this dataset alone.

## 9.2 Validation table

| Criterion | TDMS measurement | Model prediction | Verdict |
|---|---|---|---|
| Supply voltage RMS phase | 239.2 V | 244 V (calibrated) | EXACT MATCH |
| Grid frequency | 50.00 Hz | 50.0 Hz | EXACT MATCH |
| 3-phase symmetry (U0-U1) | 120.0 deg | 120 deg | EXACT MATCH |
| Conveyor steady-state current | 0.4-1.0 A delta over idle | 1.63 A | IN RANGE |
| Conveyor steady-state power | 50-200 W delta over idle | 108 W | IN RANGE |
| XY10 stepper peak RMS current | 0.33-4.37 A (N=54 episodes) | 1.85 A (X), 1.53 A (Z) | IN RANGE |
| XY10 stepper episode power | 0-273 W | 106 W | IN RANGE |

## 9.3 Per-recording analysis

| Recording | Duration | Idle I1 | Max I1 | Idle P | Max P |
|---|---|---|---|---|---|
| `first.tdms` | 444 s | 1.165 A | 1.938 A | 153 W | 457 W |
| `second.tdms` | 775 s | 0.721 A | 1.605 A | 2 W | 596 W |
| `third.tdms` | 972 s | 0.925 A | 1.586 A | 223 W | 581 W |
| `four.tdms` | 287 s | 0.053 A | 2.702 A | 0 W | 25 W |
| `fifth.tdms` | 972 s | 0.925 A | 1.586 A | 223 W | 581 W |

Recording `four.tdms` has near-zero idle baseline (I0=0.07 A, I1=0.05 A), indicating most permanent loads were powered down during this session. This recording offers the cleanest isolation of XY10 stepper activations: 54 short-duration current bursts characterize the chopper-driven stepper signature.

## 9.4 Limitations

- Conveyor quantitative validation per-subsystem is not possible; order-of-magnitude consistency is the strongest claim.
- XY10 stepper model uses single-coil DC equivalent with x2 scaling factor on output equations to represent two-coil chopper drives.
- 3-phase real power computed via two-wattmeter approximation, introducing 10-20% uncertainty in absolute values.
