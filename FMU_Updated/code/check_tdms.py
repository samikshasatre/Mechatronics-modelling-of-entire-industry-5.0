"""
check_tdms.py
=============
Verify what channels are in first.tdms and what their actual values look like.
"""

import numpy as np
from nptdms import TdmsFile

TDMS_PATH = r"C:\Users\satres\Documents\ALIX\FMU_Updated\TDMS\first.tdms"

print("=" * 70)
print(f"Reading: {TDMS_PATH}")
print("=" * 70)

tdms = TdmsFile.read(TDMS_PATH)

for group in tdms.groups():
    print(f"\nGROUP: {group.name}")
    for ch in group.channels():
        data = np.asarray(ch[:])
        try:
            dt = ch.properties["wf_increment"]
            rate = 1.0 / dt
        except KeyError:
            dt = None
            rate = None

        print(f"\n  CHANNEL: {ch.name}")
        print(f"    samples : {len(data):,}")
        print(f"    rate    : {rate:.0f} Hz" if rate else "    rate    : (not set)")
        print(f"    duration: {len(data)*dt:.1f} s" if dt else "")
        print(f"    raw min : {data.min():+.4f}")
        print(f"    raw max : {data.max():+.4f}")
        print(f"    raw RMS : {np.sqrt(np.mean(data**2)):.4f}")

        # Try common gains
        print(f"    With gain x10  → RMS = {np.sqrt(np.mean(data**2))*10:.3f}")
        print(f"    With gain x200 → RMS = {np.sqrt(np.mean(data**2))*200:.3f}")

        # In the middle of the file
        if len(data) > 1000:
            mid = len(data) // 2
            seg = data[mid:mid+1000]
            print(f"    middle 1000 samples: min={seg.min():+.4f}, "
                  f"max={seg.max():+.4f}, RMS={np.sqrt(np.mean(seg**2)):.4f}")