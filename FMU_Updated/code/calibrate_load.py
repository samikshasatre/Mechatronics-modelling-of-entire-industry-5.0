"""
calibrate_load.py
=================
Sweep load_force_const and damper_d — parameters that affect
load torque and therefore should be sensitive at this operating point.
"""

import numpy as np
import matplotlib.pyplot as plt
from fmpy import simulate_fmu
from nptdms import TdmsFile

FMU_PATH  = r"C:\Users\satres\Documents\ALIX\FMU_Updated\FMUS\Conveyor_updated_v3.fmu"
TDMS_PATH = r"C:\Users\satres\Documents\ALIX\FMU_Updated\TDMS\first.tdms"

T_END     = 2.0
DT        = 1e-4
WIN_START = 1.5
WIN_END   = 2.0

# Load measured current
tdms = TdmsFile.read(TDMS_PATH)
g = tdms.groups()[0]
ch = [c.name for c in g.channels()][0]
i_meas = np.asarray(g[ch][:]) * 10.0
try:
    dt_tdms = g[ch].properties["wf_increment"]
except KeyError:
    dt_tdms = 1.0 / 6000.0
t_tdms = np.arange(len(i_meas)) * dt_tdms
mask = (t_tdms >= 150.0) & (t_tdms <= 250.0)
I_meas_rms = float(np.sqrt(np.mean(i_meas[mask] ** 2)))
print(f"Measured I_RMS: {I_meas_rms:.3f} A")

# Sweep load parameters
sweeps = {
    "load_force_const": [1.0, 3.0, 5.0, 10.0, 20.0, 40.0, 80.0],
    "damper_d":         [0.1, 0.5, 1.0, 5.0, 10.0, 20.0, 50.0],
}

fig, axes = plt.subplots(1, 2, figsize=(14, 5))

for ax, (pname, vals) in zip(axes, sweeps.items()):
    print(f"\nSweeping {pname}...")
    rms_list = []
    for v in vals:
        try:
            r = simulate_fmu(filename=FMU_PATH, start_time=0.0,
                             stop_time=T_END, output_interval=DT,
                             start_values={pname: v})
            t = r["time"]
            i = r["i_phase"]
            m = (t >= WIN_START) & (t <= WIN_END)
            rms = float(np.sqrt(np.mean(i[m] ** 2)))
            err = (rms - I_meas_rms) / I_meas_rms * 100
            rms_list.append(rms)
            print(f"  {pname}={v:6.2f}  I_rms={rms:.3f} A  err={err:+6.1f}%")
        except Exception as e:
            print(f"  {pname}={v}: ERROR {e}")
            rms_list.append(None)

    valid = [(v, r) for v, r in zip(vals, rms_list) if r is not None]
    if valid:
        v_plot = [x[0] for x in valid]
        r_plot = [x[1] for x in valid]
        ax.semilogx(v_plot, r_plot, "o-", color="#1F618D", lw=2.5, markersize=10)
        ax.axhline(I_meas_rms, color="#E07B47", ls="--", lw=2.5,
                   label=f"Measured = {I_meas_rms:.3f} A")
        ax.set_xlabel(pname, fontsize=11)
        ax.set_ylabel("Model I_RMS (A)", fontsize=11)
        ax.set_title(f"Sweep of {pname}", fontsize=11, fontweight="bold")
        ax.legend(); ax.grid(alpha=0.3, which="both")

plt.tight_layout()
plt.savefig(r"C:\Users\satres\Documents\ALIX\FMU_Updated\calibration_load.png",
            dpi=200, bbox_inches="tight")
plt.show()
print("Saved: calibration_load.png")