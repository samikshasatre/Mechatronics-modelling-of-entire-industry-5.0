
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

GAIN_U = 200.0
GAIN_I = 10.0
FS = 6000.2


def analyze(rec, name, channel):
    sig = rec[channel]
    mean = np.mean(sig)
    std = np.std(sig)
    min_v = np.min(sig)
    max_v = np.max(sig)
    pk_to_pk = max_v - min_v
    print(f"\n  {name} channel {channel}:")
    print(f"    mean  = {mean:.3f}")
    print(f"    std   = {std:.3f}")
    print(f"    min   = {min_v:.3f}")
    print(f"    max   = {max_v:.3f}")
    print(f"    p-p   = {pk_to_pk:.3f}")
    if abs(mean) > 3 * std:
        print(f"    >> Signal has strong DC offset; not centered on zero")
    if min_v >= 0:
        print(f"    >> Signal is positive-only — possibly rectified or magnitude")
    if max_v <= 0:
        print(f"    >> Signal is negative-only — sign convention reversed")

    centered = sig - mean
    zero_crossings = np.where(np.diff(np.sign(centered)))[0]
    if len(zero_crossings) >= 4:
        n_periods = len(zero_crossings) / 2
        duration = len(sig) / FS
        f_est = n_periods / duration
        print(f"    >> Estimated frequency (after DC removal): {f_est:.1f} Hz")
    else:
        print(f"    >> No clear oscillation pattern in this window")


def load_tdms(filename):
    tdms = TdmsFile.read(os.path.join(TDMS_DIR, filename))
    return {
        't':  np.arange(len(tdms['SIGNAUX']['U0'])) / FS,
        'U0': tdms['SIGNAUX']['U0'][:] * GAIN_U,
        'U1': tdms['SIGNAUX']['U1'][:] * GAIN_U,
        'I0': tdms['SIGNAUX']['I0'][:] * GAIN_I,
        'I1': tdms['SIGNAUX']['I1'][:] * GAIN_I,
    }


def main():
    print("=" * 70)
    print("TDMS CHANNEL DIAGNOSIS")
    print("=" * 70)

    rec_first = load_tdms('first.tdms')
    rec_four  = load_tdms('four.tdms')

    print(f"\nfirst.tdms duration: {len(rec_first['I1'])/FS:.1f} s, {len(rec_first['I1'])} samples")
    print(f"four.tdms  duration: {len(rec_four['I1'])/FS:.1f} s, {len(rec_four['I1'])} samples")

    print("\n" + "=" * 70)
    print("first.tdms @ t=100s — 200 ms window (line operating, conveyor running)")
    print("=" * 70)
    s_idx = int(100.0 * FS)
    e_idx = s_idx + int(0.2 * FS)
    win = {k: rec_first[k][s_idx:e_idx] for k in ['U0','U1','I0','I1']}
    for ch in ['U0','U1','I0','I1']:
        analyze(win, 'first.tdms', ch)

    print("\n" + "=" * 70)
    print("four.tdms @ t=20s — 200 ms window (line operating, conveyor running)")
    print("=" * 70)
    s_idx = int(20.0 * FS)
    e_idx = s_idx + int(0.2 * FS)
    win = {k: rec_four[k][s_idx:e_idx] for k in ['U0','U1','I0','I1']}
    for ch in ['U0','U1','I0','I1']:
        analyze(win, 'four.tdms', ch)

    fig, axes = plt.subplots(4, 2, figsize=(14, 10))
    fig.suptitle("TDMS channel diagnosis — first.tdms (left), four.tdms (right)\n"
                 "Identify which channel actually contains the 50 Hz AC line current",
                 fontsize=12, weight="bold")

    win_n = int(0.1 * FS)  # 100 ms
    t_ms = np.arange(win_n) / FS * 1000

    s_idx = int(100.0 * FS)
    for i, ch in enumerate(['U0','U1','I0','I1']):
        ax = axes[i, 0]
        ax.plot(t_ms, rec_first[ch][s_idx:s_idx+win_n], 'b-', lw=0.8)
        ax.set_ylabel(ch)
        ax.set_title(f"first.tdms — {ch}", fontsize=9)
        ax.grid(True)
        ax.axhline(0, color='gray', lw=0.5)
    axes[3, 0].set_xlabel('Time [ms]')

    s_idx = int(20.0 * FS)
    for i, ch in enumerate(['U0','U1','I0','I1']):
        ax = axes[i, 1]
        ax.plot(t_ms, rec_four[ch][s_idx:s_idx+win_n], 'g-', lw=0.8)
        ax.set_ylabel(ch)
        ax.set_title(f"four.tdms — {ch}", fontsize=9)
        ax.grid(True)
        ax.axhline(0, color='gray', lw=0.5)
    axes[3, 1].set_xlabel('Time [ms]')

    plt.tight_layout()
    out = os.path.join(HERE, "results", "tdms_diagnosis.png")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    plt.savefig(out, dpi=130, bbox_inches="tight")
    print(f"\nDiagnostic figure saved: {out}")
    plt.show()


if __name__ == "__main__":
    main()