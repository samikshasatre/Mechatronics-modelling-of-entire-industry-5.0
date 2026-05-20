"""
inspect_I0.py — Close inspection of first.tdms channel I0.

I0 has p-p of 3 A and crosses zero — most AC content of any current channel.
Diagnose whether it can be used directly, or after DC-offset removal,
to compare against the FMU's i_phase_inst output.
"""
import os, sys
import numpy as np
import matplotlib.pyplot as plt
from nptdms import TdmsFile

HERE = os.path.dirname(os.path.abspath(__file__))
TDMS_DIR = None
for c in [os.path.join(HERE, "..", "tdms"),
          r"C:\Users\satres\Documents\ALIX\tdms"]:
    if os.path.isdir(c):
        TDMS_DIR = c; break

FS = 6000.2
GAIN_I = 10.0

def main():
    tdms = TdmsFile.read(os.path.join(TDMS_DIR, 'first.tdms'))
    I0 = tdms['SIGNAUX']['I0'][:] * GAIN_I

    # Try several windows during line-running portion
    windows = [50.0, 100.0, 150.0, 200.0, 300.0]  # seconds
    fig, axes = plt.subplots(len(windows), 2, figsize=(14, 12))
    fig.suptitle("first.tdms I0 — different windows during line operation\n"
                 "Left: raw signal · Right: signal with DC offset removed",
                 fontsize=12, weight="bold")

    for i, t0 in enumerate(windows):
        s_idx = int(t0 * FS)
        n_win = int(0.1 * FS)  # 100 ms
        sig = I0[s_idx:s_idx+n_win]
        t_ms = np.arange(n_win) / FS * 1000

        # Raw
        axes[i, 0].plot(t_ms, sig, 'b-', lw=0.6)
        axes[i, 0].axhline(0, color='gray', lw=0.5)
        axes[i, 0].axhline(np.mean(sig), color='red', lw=0.5, ls='--', label=f"mean = {np.mean(sig):.2f} A")
        axes[i, 0].set_ylabel(f"I0 [A]\n@ t = {t0} s")
        axes[i, 0].set_title(f"Raw (mean = {np.mean(sig):.2f} A, p-p = {np.ptp(sig):.2f} A)", fontsize=9)
        axes[i, 0].legend(fontsize=7)
        axes[i, 0].grid(True)

        # DC removed
        sig_centered = sig - np.mean(sig)
        axes[i, 1].plot(t_ms, sig_centered, 'b-', lw=0.6)
        axes[i, 1].axhline(0, color='gray', lw=0.5)
        axes[i, 1].set_title(f"After DC removal (RMS = {np.sqrt(np.mean(sig_centered**2)):.2f} A)", fontsize=9)
        axes[i, 1].grid(True)

        # Estimate frequency by zero crossings
        zc = np.where(np.diff(np.sign(sig_centered)))[0]
        if len(zc) >= 4:
            n_periods = len(zc) / 2
            duration = n_win / FS
            f_est = n_periods / duration
            print(f"t={t0}s: mean={np.mean(sig):.2f} A, p-p={np.ptp(sig):.2f} A, "
                  f"f_est(after DC removal)={f_est:.1f} Hz")
        else:
            print(f"t={t0}s: mean={np.mean(sig):.2f} A, p-p={np.ptp(sig):.2f} A, "
                  f"no clean oscillation")

        axes[i, 1].set_xlabel('Time [ms]' if i == len(windows)-1 else '')
        axes[i, 0].set_xlabel('Time [ms]' if i == len(windows)-1 else '')

    plt.tight_layout()
    out = os.path.join(HERE, "results", "I0_inspection.png")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    plt.savefig(out, dpi=130, bbox_inches="tight")
    print(f"\nFigure saved: {out}")
    plt.show()


if __name__ == "__main__":
    main()