"""
check_fmu_outputs.py — Verify FMU exposes all expected outputs.

Run this after re-exporting Conveyor_updated.fmu to confirm that:
  - All v1 outputs are still present (backward compatibility)
  - New v2 output 'i_phase_inst' is exposed (per supervisor request)
  - Quick sanity check on output values during steady-state
"""

import os, sys
import numpy as np

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


def main():
    fmu_path = find_fmu("Conveyor_updated_v2.fmu")
    print(f"Checking FMU: {fmu_path}")
    if not os.path.exists(fmu_path):
        print("ERROR: FMU not found.")
        return

    fmu = FMUWrapper(fmu_path, instance_name="check_outputs")
    fmu.print_summary()

    outputs = [v[0] for v in fmu.list_variables("output")]
    print()
    print("=" * 60)
    print("OUTPUT VERIFICATION")
    print("=" * 60)

    expected_v1 = ["w_motor", "tau_shaft", "v_belt", "x_belt", "i_phase", "P_elec"]
    expected_v2 = ["i_phase_inst"]
    expected_all = expected_v1 + expected_v2

    found_v1 = [o for o in expected_v1 if o in outputs]
    found_v2 = [o for o in expected_v2 if o in outputs]
    missing  = [o for o in expected_all if o not in outputs]

    print(f"V1 outputs found: {len(found_v1)}/{len(expected_v1)}")
    for o in expected_v1:
        marker = "✅" if o in outputs else "❌"
        print(f"  {marker} {o}")

    print(f"\nV2 outputs found: {len(found_v2)}/{len(expected_v2)}")
    for o in expected_v2:
        marker = "✅" if o in outputs else "❌"
        print(f"  {marker} {o}")

    if missing:
        print(f"\n❌ MISSING OUTPUTS: {missing}")
        print("FMU export likely failed to expose these. Re-export with correct settings.")
        fmu.close()
        return

    print("\n✅ All expected outputs are exposed in the FMU.")

    # ----- Quick sanity check: run for 2.5 s, sample at high rate -----
    print()
    print("=" * 60)
    print("SANITY CHECK — running FMU at 50 kHz for 0.5 s of steady state")
    print("=" * 60)

    DT = 2e-5  # 20 us = 50 kHz, fine enough to resolve 50 Hz (400 samples/cycle)
    t_end = 2.5

    fmu.initialize(start_time=0.0, stop_time=t_end)
    n = int(t_end / DT)
    log = {
        "t":            np.zeros(n),
        "i_phase":      np.zeros(n),
        "i_phase_inst": np.zeros(n),
    }
    for k in range(n):
        fmu.do_step(DT)
        log["t"][k] = fmu.t
        log["i_phase"][k]      = fmu.get_real("i_phase")
        log["i_phase_inst"][k] = fmu.get_real("i_phase_inst")
    fmu.close()

    # Analyze steady-state portion (last 0.5 s)
    mask = log["t"] >= 2.0
    t_ss = log["t"][mask]
    i_rms = log["i_phase"][mask]
    i_ac  = log["i_phase_inst"][mask]

    print(f"\nSteady-state analysis (t = 2.0 to 2.5 s, {mask.sum()} samples):")
    print(f"  i_phase (RMS-equivalent):")
    print(f"    mean = {i_rms.mean():.3f} A")
    print(f"    std  = {i_rms.std():.4f} A  (should be ~0 — RMS is steady)")
    print(f"  i_phase_inst (instantaneous):")
    print(f"    mean = {i_ac.mean():.3f} A  (should be ~0 — symmetric AC)")
    print(f"    std  = {i_ac.std():.3f} A   (should be ~i_rms/sqrt(2) × sqrt(2) = i_rms)")
    print(f"    min  = {i_ac.min():.2f} A")
    print(f"    max  = {i_ac.max():.2f} A")
    print(f"    peak = {max(abs(i_ac.min()), abs(i_ac.max())):.2f} A  "
          f"(should be ~i_rms × sqrt(2) = {i_rms.mean() * np.sqrt(2):.2f} A)")

    # Verify it really is a 50 Hz sinusoid
    zero_crossings = np.where(np.diff(np.sign(i_ac)))[0]
    if len(zero_crossings) >= 2:
        n_periods_estimated = len(zero_crossings) / 2
        duration_ss = t_ss[-1] - t_ss[0]
        freq_estimated = n_periods_estimated / duration_ss
        print(f"\n  Estimated frequency from zero crossings: {freq_estimated:.1f} Hz")
        if abs(freq_estimated - 50) < 2:
            print(f"  ✅ Frequency matches expected 50 Hz line.")
        else:
            print(f"  ⚠️  Expected 50 Hz, got {freq_estimated:.1f} Hz — verify model.")
    else:
        print(f"\n  ⚠️  No zero crossings found — output may not be oscillating.")

    print()
    print("=" * 60)
    print("VERIFICATION SUMMARY")
    print("=" * 60)
    expected_peak = i_rms.mean() * np.sqrt(2)
    actual_peak = max(abs(i_ac.min()), abs(i_ac.max()))
    if abs(actual_peak - expected_peak) / expected_peak < 0.10:
        print("✅ FMU correctly exposes instantaneous AC current.")
        print(f"   RMS = {i_rms.mean():.2f} A → expected peak = {expected_peak:.2f} A")
        print(f"   Measured peak = {actual_peak:.2f} A  (within 10% of expected)")
    else:
        print("⚠️  Peak/RMS ratio is unexpected. Investigate.")


if __name__ == "__main__":
    main()