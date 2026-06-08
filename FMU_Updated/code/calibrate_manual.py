"""
calibrate_manual.py
===================
Manual parameter sweep for conveyor FMU.
Sweeps Rs_motor across a range and finds the value that best matches
the measured TDMS current.
"""

import numpy as np
import matplotlib.pyplot as plt
from fmpy import simulate_fmu
from nptdms import TdmsFile

# =============== CONFIG ===============
FMU_PATH  = r"C:\Users\satres\Documents\ALIX\FMU_Updated\FMUS\Conveyor_updated_v3.fmu"
TDMS_PATH = r"C:\Users\satres\Documents\ALIX\FMU_Updated\TDMS\first.tdms"

T_END     = 2.0           # 2 s — enough for induction motor to reach steady
DT        = 1e-4
WIN_START = 1.5           # take RMS in last 0.5 s of FMU simulation
WIN_END   = 2.0

# TDMS window — known clean steady-state region of first.tdms
TDMS_WIN_START = 150.0
TDMS_WIN_END   = 250.0

# =============== STEP 1 — load measured current ===============
print("Loading TDMS measurement...")
tdms = TdmsFile.read(TDMS_PATH)
group = tdms.groups()[0]

# List channels to find the current one
channel_names = [ch.name for ch in group.channels()]
print(f"  TDMS channels available: {channel_names}")

# Try common current channel names in order of likelihood
i_channel = None
for candidate in ["I0", "I1", "I2", "Current", "i_phase", channel_names[0]]:
    if candidate in channel_names:
        i_channel = candidate
        break

if i_channel is None:
    raise RuntimeError(f"Could not find current channel. Names: {channel_names}")
print(f"  Using current channel: {i_channel}")

# Load the current data
i_meas_raw = np.asarray(group[i_channel][:])

# Apply gain (transducer scaling)
GAIN_I = 10.0
i_meas_full = i_meas_raw * GAIN_I

# Get time step
try:
    dt_tdms = group[i_channel].properties["wf_increment"]
except KeyError:
    dt_tdms = 1.0 / 6000.0    # fallback to 6 kHz
print(f"  TDMS time step: {dt_tdms*1e6:.1f} us  (rate = {1/dt_tdms:.0f} Hz)")

t_tdms = np.arange(len(i_meas_full)) * dt_tdms

# Compute RMS in the clean steady window
mask_m = (t_tdms >= TDMS_WIN_START) & (t_tdms <= TDMS_WIN_END)
i_meas_window = i_meas_full[mask_m]
I_meas_rms = float(np.sqrt(np.mean(i_meas_window ** 2)))
I_meas_peak = float(np.max(np.abs(i_meas_window)))
print(f"\nMeasured steady state (window {TDMS_WIN_START}-{TDMS_WIN_END} s):")
print(f"  I_RMS  = {I_meas_rms:.3f} A")
print(f"  I_peak = {I_meas_peak:.3f} A")

# =============== STEP 2 — parameter sweep ===============
parameter_name = "Rs_motor"
sweep_values = [6.0, 8.0, 10.0, 12.0, 14.0, 16.0]
print(f"\nSweeping {parameter_name} over {sweep_values} ...")
print(f"FMU initial {parameter_name} = 12.0 ohm (datasheet)\n")

results = []
for val in sweep_values:
    print(f"  Running FMU with {parameter_name} = {val:5.2f} ohm  ...", end="", flush=True)
    try:
        result = simulate_fmu(
            filename        = FMU_PATH,
            start_time      = 0.0,
            stop_time       = T_END,
            output_interval = DT,
            start_values    = {parameter_name: val},
        )
        t_fmu = result["time"]

        # Get current — try 'i_phase' first, fall back to other names
        i_fmu = None
        for out_name in ["i_phase", "i_phase_inst"]:
            if out_name in result.dtype.names:
                i_fmu = result[out_name]
                break
        if i_fmu is None:
            i_fmu = result[result.dtype.names[1]]

        mask = (t_fmu >= WIN_START) & (t_fmu <= WIN_END)
        I_fmu_rms = float(np.sqrt(np.mean(i_fmu[mask] ** 2)))
        err = (I_fmu_rms - I_meas_rms) / I_meas_rms * 100.0
        results.append({"val": val, "I_rms": I_fmu_rms, "err_pct": err,
                        "t": t_fmu, "i": i_fmu})
        print(f"  I_rms = {I_fmu_rms:.3f} A   err = {err:+6.1f} %")
    except Exception as e:
        print(f"  ERROR: {e}")

if not results:
    raise RuntimeError("All FMU runs failed. Check FMU + parameter names.")

# Best match
best = min(results, key=lambda r: abs(r["err_pct"]))
print(f"\n{'='*60}")
print(f"BEST FIT: {parameter_name} = {best['val']} ohm")
print(f"  Original (datasheet, 12 ohm): err = {[r for r in results if r['val']==12.0][0]['err_pct']:+.1f}%")
print(f"  Best fit:                     err = {best['err_pct']:+.1f}%")
print(f"  Improvement: residual reduced from "
      f"{abs([r for r in results if r['val']==12.0][0]['err_pct']):.1f}% "
      f"to {abs(best['err_pct']):.1f}%")
print(f"{'='*60}")

# =============== STEP 3 — plot results ===============
fig, axes = plt.subplots(1, 2, figsize=(13, 5))

# Panel 1: model RMS vs sweep value
ax = axes[0]
vals  = [r["val"]   for r in results]
i_rms = [r["I_rms"] for r in results]
ax.plot(vals, i_rms, "o-", color="#1F618D", lw=2.5, markersize=10)
ax.axhline(I_meas_rms, color="#E07B47", ls="--", lw=2.5,
           label=f"Measured = {I_meas_rms:.3f} A")
ax.set_xlabel(f"{parameter_name}  (ohm)", fontsize=11)
ax.set_ylabel("Model I_RMS  (A)", fontsize=11)
ax.set_title(f"Sweep of {parameter_name} — model vs measurement",
             fontsize=11, fontweight="bold")
ax.annotate(f"Best fit\n{parameter_name} = {best['val']} ohm",
            xy=(best["val"], best["I_rms"]),
            xytext=(best["val"]+1.5, best["I_rms"]+0.15),
            arrowprops=dict(arrowstyle="->", color="green", lw=1.5),
            fontsize=10, color="green", fontweight="bold",
            bbox=dict(boxstyle="round,pad=0.3", fc="#E8F5E9", ec="green"))
ax.legend(fontsize=10)
ax.grid(alpha=0.3)

# Panel 2: error percentage curve
ax = axes[1]
errs = [r["err_pct"] for r in results]
ax.plot(vals, errs, "o-", color="#A93226", lw=2.5, markersize=10)
ax.axhline(0, color="grey", ls="-", lw=1)
ax.fill_between(vals, [-5]*len(vals), [5]*len(vals),
                color="green", alpha=0.1, label="±5 % band")
ax.set_xlabel(f"{parameter_name}  (ohm)", fontsize=11)
ax.set_ylabel("Error vs measurement  (%)", fontsize=11)
ax.set_title("Calibration error — find the minimum",
             fontsize=11, fontweight="bold")
ax.legend(fontsize=10)
ax.grid(alpha=0.3)

plt.tight_layout()
out_path = r"C:\Users\satres\Documents\ALIX\FMU_Updated\calibration_sweep.png"
plt.savefig(out_path, dpi=200, bbox_inches="tight")
print(f"\nPlot saved: {out_path}")
plt.show()

# =============== STEP 4 — save summary to text ===============
summary_path = r"C:\Users\satres\Documents\ALIX\FMU_Updated\calibration_summary.txt"
with open(summary_path, "w") as f:
    f.write("CONVEYOR FMU CALIBRATION — MANUAL PARAMETER SWEEP\n")
    f.write("="*60 + "\n\n")
    f.write(f"FMU:  {FMU_PATH}\n")
    f.write(f"TDMS: {TDMS_PATH}\n")
    f.write(f"TDMS channel: {i_channel}, gain = {GAIN_I}\n\n")
    f.write(f"Measured I_RMS in steady window ({TDMS_WIN_START}-{TDMS_WIN_END} s): "
            f"{I_meas_rms:.3f} A\n")
    f.write(f"Measured I_peak: {I_meas_peak:.3f} A\n\n")
    f.write(f"Sweep parameter: {parameter_name}\n\n")
    f.write(f"{'Value (ohm)':<12} {'I_RMS (A)':<12} {'Error (%)':<12}\n")
    f.write("-"*40 + "\n")
    for r in results:
        f.write(f"{r['val']:<12.2f} {r['I_rms']:<12.3f} {r['err_pct']:<+12.2f}\n")
    f.write("\n")
    f.write(f"BEST FIT: {parameter_name} = {best['val']} ohm, "
            f"residual = {best['err_pct']:+.2f}%\n")
print(f"Summary saved: {summary_path}")