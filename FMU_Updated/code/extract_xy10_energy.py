"""
extract_xy10_energy.py
----------------------
Extract XY10 stepper energy from four.tdms using baseline subtraction.

Strategy:
  1. Auto-discover the TDMS structure (groups, channel names)
  2. Apply transducer gains (U x200, I x10)
  3. Compute instantaneous three-phase power p(t) = u0*i0 + u1*i1 + u2*i2
  4. Plot p(t) over the full recording so you can identify the XY10 burst visually
  5. Compute baseline (quiet) power and burst power
  6. XY10 energy = (burst power - baseline power) x burst duration

You can run this in two modes:
  - Mode 'explore' : just shows you the file structure + a full power plot
  - Mode 'extract' : computes the XY10 energy using the windows you set
"""

import sys
import numpy as np
import matplotlib.pyplot as plt
from nptdms import TdmsFile

# =========================================================================
# CONFIGURATION
# =========================================================================
TDMS_PATH = "four.tdms"          # path to your TDMS file - change if needed
GAIN_U = 200.0                    # voltage transducer gain
GAIN_I = 10.0                     # current transducer gain
SAMPLE_RATE_FALLBACK = 6000.0     # used only if dt cannot be inferred from TDMS

# Set MODE to 'explore' first to see the structure + the power-vs-time plot
# Then switch to 'extract' once you've chosen baseline and burst windows
MODE = "extract"

# These two windows are used ONLY in 'extract' mode
# Adjust them after looking at the plot from 'explore' mode
BASELINE_WINDOW = (50.0, 60.0)      # seconds - a quiet stretch where XY10 is idle
BURST_WINDOW    = (85.0, 100.0)   # seconds - the XY10 burst

# =========================================================================
# STEP 1 - Open the TDMS and discover its structure
# =========================================================================
print("=" * 70)
print(f"Opening {TDMS_PATH}")
print("=" * 70)

try:
    tdms = TdmsFile.read(TDMS_PATH)
except FileNotFoundError:
    print(f"ERROR: file not found at {TDMS_PATH}")
    print("Edit TDMS_PATH at the top of the script to the correct path.")
    sys.exit(1)

groups = tdms.groups()
print(f"\nFound {len(groups)} group(s):\n")
for g in groups:
    channels = g.channels()
    print(f"  Group: '{g.name}'  ({len(channels)} channel(s))")
    for c in channels:
        n_samples = len(c)
        print(f"      Channel: '{c.name}'  (n_samples = {n_samples})")

# =========================================================================
# STEP 2 - Pick the channels we need
# =========================================================================
# Try to find U0, U1, U2, I0, I1, I2 - they may be named differently
# Adjust this section if your channel names don't match
group = groups[0]                                   # assume one group
ch_names = [c.name for c in group.channels()]

def find_channel(needles):
    """Find the first channel whose name contains one of the needle strings (case insensitive)."""
    for name in ch_names:
        low = name.lower()
        for needle in needles:
            if needle.lower() in low:
                return name
    return None

ch_u0 = find_channel(["U0", "u0", "voltage0", "v0"])
ch_u1 = find_channel(["U1", "u1", "voltage1", "v1"])
ch_u2 = find_channel(["U2", "u2", "voltage2", "v2"])
ch_i0 = find_channel(["I0", "i0", "current0"])
ch_i1 = find_channel(["I1", "i1", "current1"])
ch_i2 = find_channel(["I2", "i2", "current2"])

print(f"\nChannels auto-detected:")
print(f"  U0 -> {ch_u0}    U1 -> {ch_u1}    U2 -> {ch_u2}")
print(f"  I0 -> {ch_i0}    I1 -> {ch_i1}    I2 -> {ch_i2}")

if None in (ch_u0, ch_u1, ch_u2, ch_i0, ch_i1, ch_i2):
    print("\nERROR: could not auto-detect all six channels.")
    print("Edit the find_channel(...) calls above to match your actual channel names")
    print(f"from the list: {ch_names}")
    sys.exit(1)

# =========================================================================
# STEP 3 - Read the data, apply gains, build the time vector
# =========================================================================
u0 = np.asarray(group[ch_u0][:]) * GAIN_U
u1 = np.asarray(group[ch_u1][:]) * GAIN_U
u2 = np.asarray(group[ch_u2][:]) * GAIN_U
i0 = np.asarray(group[ch_i0][:]) * GAIN_I
i1 = np.asarray(group[ch_i1][:]) * GAIN_I
i2 = np.asarray(group[ch_i2][:]) * GAIN_I

n = min(len(u0), len(u1), len(u2), len(i0), len(i1), len(i2))
u0, u1, u2 = u0[:n], u1[:n], u2[:n]
i0, i1, i2 = i0[:n], i1[:n], i2[:n]

# Build time vector - try to use TDMS time properties first
try:
    t_inc = group[ch_u0].properties["wf_increment"]
    t_start = group[ch_u0].properties.get("wf_start_offset", 0.0)
    t = t_start + np.arange(n) * t_inc
    fs = 1.0 / t_inc
    print(f"\nTime vector built from TDMS properties: dt = {t_inc:.6f} s  ->  fs = {fs:.1f} Hz")
except KeyError:
    t = np.arange(n) / SAMPLE_RATE_FALLBACK
    fs = SAMPLE_RATE_FALLBACK
    print(f"\nWARNING: time properties not in TDMS - using fallback {SAMPLE_RATE_FALLBACK} Hz")

print(f"Recording length: {n} samples = {t[-1]:.2f} s")

# =========================================================================
# STEP 4 - Compute instantaneous three-phase power
# =========================================================================
# =========================================================================
# STEP 4 - Compute apparent + active power using RMS sliding window
# =========================================================================
# Cycle length at 50 Hz = 20 ms = 120 samples at 6 kHz
cycle_samples = max(1, int(0.020 * fs))

def rms(x, win):
    """Root mean square over a sliding window."""
    return np.sqrt(np.convolve(x ** 2, np.ones(win) / win, mode="same"))

# RMS of each phase voltage and current (50 Hz cycle window)
U0_rms = rms(u0, cycle_samples)
U1_rms = rms(u1, cycle_samples)
U2_rms = rms(u2, cycle_samples)
I0_rms = rms(i0, cycle_samples)
I1_rms = rms(i1, cycle_samples)
I2_rms = rms(i2, cycle_samples)

# APPARENT power per phase = U_rms * I_rms (always positive)
S_phase0 = U0_rms * I0_rms
S_phase1 = U1_rms * I1_rms
S_phase2 = U2_rms * I2_rms

# Total apparent power (this is what we'll use as the envelope)
p_smooth = S_phase0 + S_phase1 + S_phase2

# Also compute the line current RMS for the second plot
i_rms_smooth = (I0_rms + I1_rms + I2_rms) / 3.0

# Keep p_inst defined so the plotting code further down doesn't break
# (instantaneous active power = u*i, summed across phases)
p_inst = u0 * i0 + u1 * i1 + u2 * i2

print(f"\nMean apparent power over full recording: {np.mean(p_smooth):.1f} VA")
print(f"Peak apparent power during recording:    {np.max(p_smooth):.1f} VA")

# =========================================================================
# STEP 5 - Plot the full recording so you can pick windows
# =========================================================================
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 7), sharex=True)

ax1.plot(t, p_inst, color="0.7", lw=0.4, label="Instantaneous")
ax1.plot(t, p_smooth, color="#2E75B6", lw=1.5, label="20 ms moving average")
ax1.set_ylabel("Three-phase apparent power (VA)", fontsize=11)
ax1.set_title(
    f"{TDMS_PATH} - three-phase apparent power (U_rms * I_rms per phase)\n"
    f"Look for the XY10 burst as a power increase above the baseline",
    fontsize=11,
    fontweight="bold"
)
ax1.legend(loc="upper right", fontsize=10)
ax1.grid(alpha=0.3)

# Highlight the configured windows (so you can visually check them)
ax1.axvspan(BASELINE_WINDOW[0], BASELINE_WINDOW[1], alpha=0.15, color="green", label="baseline")
ax1.axvspan(BURST_WINDOW[0],    BURST_WINDOW[1],    alpha=0.15, color="orange", label="burst")
ax1.text(np.mean(BASELINE_WINDOW), ax1.get_ylim()[1] * 0.9, "BASELINE",
         ha="center", color="green", fontweight="bold", fontsize=9)
ax1.text(np.mean(BURST_WINDOW),    ax1.get_ylim()[1] * 0.9, "BURST",
         ha="center", color="orange", fontweight="bold", fontsize=9)

# Lower plot - RMS current as another way to see the burst
i_rms = np.sqrt((i0 ** 2 + i1 ** 2 + i2 ** 2) / 3.0)
kernel = np.ones(cycle_samples) / cycle_samples
i_rms_smooth = np.convolve(i_rms, kernel, mode="same")
ax2.plot(t, i_rms, color="0.7", lw=0.4)
ax2.plot(t, i_rms_smooth, color="#E06C5C", lw=1.5)
ax2.set_xlabel("Time (s)", fontsize=11)
ax2.set_ylabel("RMS line current (A)", fontsize=11)
ax2.set_title("Line current envelope (alternative view of the burst)", fontsize=10)
ax2.grid(alpha=0.3)

plt.tight_layout()
out_png = "xy10_power_overview.png"
plt.savefig(out_png, dpi=150, bbox_inches="tight")
print(f"\nOverview plot saved to: {out_png}")
plt.show()

if MODE == "explore":
    print("\n" + "=" * 70)
    print("EXPLORE MODE COMPLETE")
    print("=" * 70)
    print("Look at xy10_power_overview.png and identify:")
    print("  1. A QUIET stretch where XY10 is idle - this is the BASELINE")
    print("  2. The XY10 BURST - a clear power increase above baseline")
    print("\nThen edit at the top of this script:")
    print("    BASELINE_WINDOW = (start_seconds, end_seconds)")
    print("    BURST_WINDOW    = (start_seconds, end_seconds)")
    print("    MODE = 'extract'")
    print("And run the script again.")
    sys.exit(0)

# =========================================================================
# STEP 6 - Extract baseline + burst powers and compute XY10 energy
# =========================================================================
print("\n" + "=" * 70)
print("EXTRACT MODE - computing XY10 energy")
print("=" * 70)

mask_baseline = (t >= BASELINE_WINDOW[0]) & (t <= BASELINE_WINDOW[1])
mask_burst    = (t >= BURST_WINDOW[0])    & (t <= BURST_WINDOW[1])

n_baseline = int(np.sum(mask_baseline))
n_burst    = int(np.sum(mask_burst))

if n_baseline == 0:
    print(f"ERROR: BASELINE_WINDOW {BASELINE_WINDOW} contains no samples")
    sys.exit(1)
if n_burst == 0:
    print(f"ERROR: BURST_WINDOW {BURST_WINDOW} contains no samples")
    sys.exit(1)

p_baseline_mean = float(np.mean(p_smooth[mask_baseline]))
p_burst_mean    = float(np.mean(p_smooth[mask_burst]))
duration_burst  = BURST_WINDOW[1] - BURST_WINDOW[0]

p_xy10 = p_burst_mean - p_baseline_mean
e_xy10 = p_xy10 * duration_burst

print(f"\nBaseline window: {BASELINE_WINDOW[0]:.1f} - {BASELINE_WINDOW[1]:.1f} s  ({n_baseline} samples)")
print(f"  Mean apparent power:    {p_baseline_mean:.2f} VA")
print(f"\nBurst window:    {BURST_WINDOW[0]:.1f} - {BURST_WINDOW[1]:.1f} s  ({n_burst} samples)")
print(f"  Mean apparent power:    {p_burst_mean:.2f} VA")
print(f"  Duration:      {duration_burst:.2f} s")

print(f"\n--- XY10 RESULT (baseline-subtracted) ---")
print(f"  XY10 average power:    {p_xy10:.2f} W")
print(f"  XY10 energy in burst:  {e_xy10:.2f} J")
print(f"\n  Equivalent over a 30 s cycle: {p_xy10 * 30:.2f} J  ({100*(p_xy10*30)/3645:.1f}% of 3645 J)")

# Also report the model's prediction vs measurement
print(f"\n--- COMPARISON WITH MODEL ---")
print(f"  Model prediction (XY10 = i^2 R + F v) :  ~ 0 J / cycle")
print(f"  TDMS measurement (this script)        :  {p_xy10 * 30:.1f} J / cycle")
print(f"  Gap:  this is the holding current + driver electronics")
print(f"        not captured by the DC-equivalent abstraction")

# =========================================================================
# STEP 7 - Save a zoom-in plot of the burst window for the slide
# =========================================================================
zoom_start = max(0.0,         BURST_WINDOW[0] - 5.0)
zoom_end   = min(t[-1],       BURST_WINDOW[1] + 5.0)
mask_zoom  = (t >= zoom_start) & (t <= zoom_end)

fig2, ax = plt.subplots(figsize=(10, 4))
ax.plot(t[mask_zoom], p_smooth[mask_zoom], color="#2E75B6", lw=2.0, label="Three-phase power (20 ms avg)")
ax.axhline(p_baseline_mean, color="green", ls="--", lw=1.2, label=f"Baseline {p_baseline_mean:.1f} VA")
ax.axhline(p_burst_mean,    color="orange", ls="--", lw=1.2, label=f"Burst    {p_burst_mean:.1f} W")
ax.axvspan(BURST_WINDOW[0], BURST_WINDOW[1], alpha=0.15, color="orange")
ax.set_xlabel("Time (s)", fontsize=11)
ax.set_ylabel("Apparent Power (VA)", fontsize=11)
ax.set_title(f"XY10 burst in TDMS  -  delta P = {p_xy10:.1f} W  ->  {e_xy10:.1f} J over {duration_burst:.1f} s",
             fontsize=11, fontweight="bold")
ax.legend(loc="upper left", fontsize=10)
ax.grid(alpha=0.3)
plt.tight_layout()
out_png2 = "xy10_burst_zoom.png"
plt.savefig(out_png2, dpi=150, bbox_inches="tight")
print(f"\nBurst zoom plot saved to: {out_png2}")
plt.show()