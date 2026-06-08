"""
validation_dynamic_v8_FIXED.py - Validation plot with Panel 4 corrected.

FIX (vs v7.1): Panel 4 used to overlay two physically unrelated signals
(TDMS chopper envelope at +-20 A and FMU DC-equivalent at +-3 A) on dual y-axes,
which violated Romain's principle of axis-correct plotting.

The corrected version replaces Panel 4 with TWO SIDE-BY-SIDE panels:
  - Panel 4a: TDMS chopper envelope    (left, +-20 A axis)
  - Panel 4b: FMU DC-equivalent        (right, +-3 A axis)
plus an honest written note that these are different abstractions and the
valid level of comparison is energy/RMS (Panel C of energy analysis), not
the time-domain waveform.

Panels 1, 2a, 2b, 3 are UNCHANGED - those were already axis-correct.

DATA INPUTS:
This script expects TDMS-derived arrays and FMU outputs. Adjust the
LOAD DATA section below to match how your original validation script
reads the data. The Panel 4 fix is in the PLOT section.
"""

import os
import numpy as np
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))

# =====================================================================
# LOAD DATA - replace this block to match your actual data source
# =====================================================================
# Your original v7.1 script likely loaded:
#   - TDMS U0 voltage  (Panel 1)
#   - TDMS I0 raw current  (Panel 2a)
#   - TDMS I0 filtered 50 Hz fundamental  (Panel 2b)
#   - FMU i_phase_inst  (Panel 2b)
#   - TDMS I1 raw chopper signature  (Panel 3)
#   - TDMS envelope (rolling max-abs)  (Panel 4a)
#   - FMU stepper i_x step response  (Panel 4b)
#
# Plug in your real arrays below. Stub data shown for shape:

# --- Panel 1: voltage ---
t_volt_ms = np.linspace(0, 60, 600)
v_tdms = 345 * np.sin(2*np.pi*50*t_volt_ms/1000) + 15*np.random.randn(600)*np.sin(2*np.pi*50*t_volt_ms/1000)
v_model = 244*np.sqrt(2) * np.sin(2*np.pi*50*t_volt_ms/1000)

# --- Panel 2a: raw line-side current ---
t_curr_ms = np.linspace(0, 140, 1400)
i_tdms_raw = 1.05 + 2.0*np.sin(2*np.pi*50*t_curr_ms/1000) + 1.5*np.sin(2*np.pi*150*t_curr_ms/1000)

# --- Panel 2b: filtered TDMS vs FMU ---
t_filt_ms = np.linspace(0, 140, 1400)
i_tdms_filt = 1.91 * np.sin(2*np.pi*50*t_filt_ms/1000 + 0.4)
i_fmu_inst = 2.30 * np.sin(2*np.pi*50*t_filt_ms/1000)

# --- Panel 3: XY10 stepper raw chopper ---
t_chop = np.linspace(0, 0.7, 4200)
i_tdms_chopper = np.zeros_like(t_chop)
# simulate chopper bursts
for start, peak in [(0.08, 3), (0.10, -5), (0.15, -12), (0.18, 18),
                     (0.20, 18), (0.25, 13), (0.28, -10)]:
    idx = (t_chop > start) & (t_chop < start + 0.005)
    i_tdms_chopper[idx] = peak

# --- Panel 4a: TDMS envelope (10 ms rolling max-abs) ---
t_env = np.linspace(0, 0.7, 4200)
i_tdms_envelope = np.zeros_like(t_env)
for start, end, amp in [(0.07, 0.09, 4), (0.10, 0.13, 12), (0.14, 0.17, 14),
                          (0.18, 0.21, 19), (0.24, 0.27, 14), (0.27, 0.30, 13)]:
    idx = (t_env > start) & (t_env < end)
    i_tdms_envelope[idx] = amp

# --- Panel 4b: FMU step response ---
t_fmu = np.linspace(0, 0.7, 4200)
i_fmu_step = np.zeros_like(t_fmu)
mask_pulse = (t_fmu > 0.08) & (t_fmu < 0.12)
i_fmu_step[mask_pulse] = 2.5 * np.exp(-(t_fmu[mask_pulse] - 0.08) / 0.005) * np.sin(2*np.pi*500*(t_fmu[mask_pulse]-0.08))
# =====================================================================

# ============== PLOT ==============
fig = plt.figure(figsize=(13, 18))
fig.suptitle("Dynamic signal validation v8 - axis-corrected (Romain feedback)\n"
             "Conveyor: FMU AC current overlaid with TDMS 50 Hz fundamental (edge-cropped)",
             fontsize=12, weight="bold")

gs = fig.add_gridspec(6, 2, height_ratios=[1, 1, 1.2, 1, 1, 0.4], hspace=0.55, wspace=0.30)

# ---------- Panel 1: voltage (UNCHANGED, full width) ----------
ax1 = fig.add_subplot(gs[0, :])
ax1.plot(t_volt_ms, v_tdms, lw=1.0, color="#1f77b4",
         label="TDMS U0 measured (raw 6 kHz)")
ax1.plot(t_volt_ms, v_model, lw=1.5, ls="--", color="red",
         label="Model: 244 V RMS x sqrt(2) x sin(2*pi*50*t)")
ax1.set_xlabel("Time [ms]")
ax1.set_ylabel("Voltage [V]")
ax1.set_title("Panel 1: SUPPLY VOLTAGE - TDMS measurement overlaid with model sinusoid")
ax1.legend(loc="upper right", fontsize=9)
ax1.grid(True, alpha=0.4)

ax2a = fig.add_subplot(gs[1, :])
ax2a.plot(t_curr_ms, i_tdms_raw, lw=0.8, color="#5b9bd5",
          label=f"TDMS I0 raw (first.tdms @ 50 s, peak-peak={np.ptp(i_tdms_raw):.2f} A)")
ax2a.axhline(np.mean(i_tdms_raw), color="gray", ls=":", lw=0.8,
             label=f"mean = {np.mean(i_tdms_raw):.2f} A (sensor DC offset)")
ax2a.set_xlabel("Time [ms]")
ax2a.set_ylabel("Current [A]")
ax2a.set_title("Panel 2a: MEASURED LINE-SIDE CURRENT (raw) - controller rectifier harmonics visible\n"
               "50 Hz fundamental + diode-bridge harmonics + PWM switching ripple")
ax2a.legend(loc="upper right", fontsize=8)
ax2a.grid(True, alpha=0.4)

ax2b = fig.add_subplot(gs[2, :])
ax2b.plot(t_filt_ms, i_tdms_filt, lw=2.0, color="#1f77b4",
          label=f"TDMS I0 - 50 Hz fundamental after band-pass (peak={np.max(np.abs(i_tdms_filt)):.2f} A)")
ax2b.plot(t_filt_ms, i_fmu_inst, lw=1.5, color="red",
          label=f"FMU i_phase_inst - modelled motor terminal current (peak={np.max(np.abs(i_fmu_inst)):.2f} A)")
ax2b.set_xlabel("Time [ms]")
ax2b.set_ylabel("Current [A]")
ax2b.set_title("Panel 2b: 50 Hz FUNDAMENTAL - TDMS band-passed vs FMU simulated\n"
               "Both real 50 Hz sinusoids overlaid, edge-cropped, phase-aligned via cross-correlation")
ax2b.legend(loc="upper right", fontsize=8)
ax2b.grid(True, alpha=0.4)
ax2b.text(0.01, 0.02,
          "Scope note: FMU models the motor as directly grid-connected (no rectifier/inverter).\n"
          "TDMS measures line-side current after the motor controller's diode bridge.\n"
          "The 50 Hz components agree (FMU 2.30 A vs TDMS 1.99 A peak); higher harmonics in the raw\n"
          "measurement (Panel 2a) reflect power electronics not in the current model scope.",
          transform=ax2b.transAxes, fontsize=8, style="italic",
          verticalalignment="bottom",
          bbox=dict(facecolor="lightyellow", edgecolor="gray", alpha=0.9))

ax3 = fig.add_subplot(gs[3, :])
ax3.plot(t_chop, i_tdms_chopper, lw=0.6, color="#5b9bd5",
         label="TDMS I1 raw 6 kHz (four.tdms @ t=145.1 s)")
ax3.set_xlabel("Time [s, aligned to burst start at t=0.1]")
ax3.set_ylabel("Current [A]")
ax3.set_title("Panel 3: XY10 STEPPER - RAW CHOPPER SIGNATURE (single isolated burst)")
ax3.set_ylim(-25, 25)
ax3.legend(loc="upper right", fontsize=8)
ax3.grid(True, alpha=0.4)



ax4a = fig.add_subplot(gs[4, 0])
ax4a.plot(t_env, i_tdms_envelope, lw=1.3, color="#1f77b4",
          label="TDMS envelope (10 ms rolling max-abs)")
ax4a.set_xlabel("Time [s]")
ax4a.set_ylabel("Measured current [A]")
ax4a.set_title("Panel 4a: TDMS chopper envelope\n(measured, real waveform peaks)")
ax4a.set_ylim(-25, 25)
ax4a.legend(loc="upper right", fontsize=8)
ax4a.grid(True, alpha=0.4)

ax4b = fig.add_subplot(gs[4, 1])
ax4b.plot(t_fmu, i_fmu_step, lw=1.3, color="red",
          label="FMU i_x - DC-equivalent driving lead-screw")
ax4b.set_xlabel("Time [s]")
ax4b.set_ylabel("Simulated current [A]")
ax4b.set_title("Panel 4b: FMU step response\n(simulated, DC-equivalent abstraction)")
ax4b.set_ylim(-3, 3)
ax4b.legend(loc="upper right", fontsize=8)
ax4b.grid(True, alpha=0.4)

# ---------- Honest note below Panel 4 ----------
ax_note = fig.add_subplot(gs[5, :])
ax_note.axis("off")
ax_note.text(0.5, 0.5,
             "Panel 4 scope note: TDMS (4a) shows the stepper drive's chopper switching current "
             "at the instantaneous level (peaks +-20 A).\n"
             "The FMU (4b) models the same stepper as a DC-equivalent driver, abstracting the "
             "chopper into its time-averaged current (peaks +-3 A).\n"
             "These two signals are NOT directly comparable in the time domain - they represent "
             "the same physical actuator at different levels of abstraction.\n"
             "Comparison is valid at the energy/RMS level (Panel C of energy analysis), not the "
             "instantaneous waveform.",
             transform=ax_note.transAxes,
             fontsize=9, style="italic",
             verticalalignment="center", horizontalalignment="center",
             bbox=dict(facecolor="lightyellow", edgecolor="gray", alpha=0.95))

fig.subplots_adjust(top=0.95, hspace=0.7, wspace=0.35)  
out_path = os.path.join(HERE, "validation_dynamic_v8_FIXED.png")
plt.savefig(out_path, dpi=140, bbox_inches="tight")
print(f"Figure saved: {out_path}")
plt.show()