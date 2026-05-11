"""
ALIX TDMS comprehensive visualization and disaggregation
========================================================
Creates publication-quality visualizations and exports CSV data
in a format compatible with time-series labelling tools
(Delabeye/timeseries-labelling-tool, Label Studio, TRAINSET, etc.)

Strategy:
1. Load all TDMS files
2. Compute envelopes (RMS power, RMS currents)
3. Detect events automatically (start/stop edges)
4. Classify events into operating regimes
5. Export CSV format compatible with labeling tools
6. Generate consistent visualization for all files
"""
import os
import json
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from nptdms import TdmsFile

TDMS_DIR = "/home/claude/tdms"
OUT_DIR = "/home/claude/labelling"
os.makedirs(OUT_DIR, exist_ok=True)

FS = 6000.2  # Hz

# Color scheme for subsystem labels (matches ALIX)
SUBSYSTEM_COLORS = {
    "idle":          "#cccccc",  # light gray - everything off
    "MI00_conveyor": "#1f77b4",  # blue
    "XY10_gantry":   "#ff7f0e",  # orange
    "MD20_dobot":    "#2ca02c",  # green
    "AG10_agv":      "#d62728",  # red
    "UC53_quality":  "#9467bd",  # purple
    "multi_machine": "#8c564b",  # brown - multiple active
    "transient":     "#e377c2",  # pink - startup/shutdown
}


def load_tdms_decimated(path, decimation=10):
    """Load TDMS and decimate to manageable size."""
    with TdmsFile.open(path) as tdms:
        grp = tdms["SIGNAUX"]
        gu = float(grp.properties["GAIN U 0"])
        gi = float(grp.properties["GAIN I 0"])
        u0 = grp["U0"][:] * gu
        u1 = grp["U1"][:] * gu
        i0 = grp["I0"][:] * gi
        i1 = grp["I1"][:] * gi
    
    # Remove DC offsets on currents
    i0 -= np.mean(i0)
    i1 -= np.mean(i1)
    
    # Reconstruct missing channels (assuming balanced 3-phase)
    u2 = -(u0 + u1)
    i2 = -(i0 + i1)
    
    # Block-average to 1 grid cycle (120 samples = 20 ms)
    cycle = 120
    n = len(u0)
    nb = n // cycle
    
    p_inst = u0*i0 + u1*i1 + u2*i2
    
    p_blocks = p_inst[:nb*cycle].reshape(nb, cycle).mean(axis=1)
    i0_rms = np.sqrt((i0[:nb*cycle].reshape(nb, cycle)**2).mean(axis=1))
    i1_rms = np.sqrt((i1[:nb*cycle].reshape(nb, cycle)**2).mean(axis=1))
    u0_rms = np.sqrt((u0[:nb*cycle].reshape(nb, cycle)**2).mean(axis=1))
    
    t_blocks = np.arange(nb) * (cycle / FS)
    
    # Sign-correct power if needed (some current sensors are inverted)
    if np.mean(p_blocks) < 0:
        p_blocks = -p_blocks
    
    # Further smoothing for visualization (1-second window)
    smooth = 50
    p_smooth = np.convolve(p_blocks, np.ones(smooth)/smooth, mode='same')
    
    return {
        "t": t_blocks,
        "p_blocks": p_blocks,
        "p_smooth": p_smooth,
        "i0_rms": i0_rms,
        "i1_rms": i1_rms,
        "u0_rms": u0_rms,
        "n_samples": n,
        "duration": t_blocks[-1] if nb > 0 else 0,
    }


def detect_events_advanced(data):
    """Detect significant events: start, stop, level changes."""
    p = data["p_smooth"]
    t = data["t"]
    
    # First derivative (1-second smoothed power change)
    dp = np.diff(p)
    
    # Threshold: 50% of std deviation
    threshold = max(15, 0.5 * np.std(dp) * 5)
    
    rising_idx = []
    falling_idx = []
    last_event_idx = -100
    
    for i, d in enumerate(dp):
        if i - last_event_idx < 100:  # ~2 seconds at 50 cycles/sec
            continue
        if d > threshold:
            rising_idx.append(i)
            last_event_idx = i
        elif d < -threshold:
            falling_idx.append(i)
            last_event_idx = i
    
    rising_times = [t[i] for i in rising_idx]
    falling_times = [t[i] for i in falling_idx]
    
    # Compute power level changes at each event
    events = []
    for i in rising_idx:
        before = np.mean(p[max(0,i-50):i])
        after = np.mean(p[i:min(len(p),i+50)])
        events.append({
            "type": "rising",
            "time": float(t[i]),
            "before_W": float(before),
            "after_W": float(after),
            "delta_W": float(after - before),
        })
    for i in falling_idx:
        before = np.mean(p[max(0,i-50):i])
        after = np.mean(p[i:min(len(p),i+50)])
        events.append({
            "type": "falling",
            "time": float(t[i]),
            "before_W": float(before),
            "after_W": float(after),
            "delta_W": float(after - before),
        })
    
    events.sort(key=lambda x: x["time"])
    return events


def classify_segments(data, events):
    """Classify each time segment into a likely operating regime.
    
    Heuristic based on power level:
    - Below 30 W:        idle
    - 30-150 W:          single small machine (likely conveyor or one stepper)
    - 150-300 W:         single large machine OR two small
    - 300-500 W:         multiple machines
    - Above 500 W:       full line operation
    """
    t = data["t"]
    p = data["p_smooth"]
    
    segments = []
    
    # Build segment boundaries from events
    boundaries = [0] + [e["time"] for e in events] + [t[-1]]
    
    for i in range(len(boundaries) - 1):
        t_start = boundaries[i]
        t_end = boundaries[i+1]
        
        # Get average power in this segment
        mask = (t >= t_start) & (t < t_end)
        if not np.any(mask):
            continue
        p_avg = float(np.mean(p[mask]))
        p_std = float(np.std(p[mask]))
        
        # Classify
        if abs(p_avg) < 30:
            label = "idle"
        elif abs(p_avg) < 150:
            label = "MI00_conveyor"  # small machine
        elif abs(p_avg) < 300:
            label = "XY10_gantry"  # medium-power, maybe stepper bursts
        elif abs(p_avg) < 500:
            label = "multi_machine"
        else:
            label = "full_line"
        
        # Adjust for variability (high std = transient)
        if p_std > 0.4 * abs(p_avg) and abs(p_avg) > 50:
            label = "transient"
        
        segments.append({
            "t_start": float(t_start),
            "t_end": float(t_end),
            "duration": float(t_end - t_start),
            "p_avg_W": p_avg,
            "p_std_W": p_std,
            "label": label,
        })
    
    return segments


def generate_visualization(data, segments, events, name, save_path):
    """Generate a high-quality multi-panel visualization."""
    t = data["t"]
    
    fig, axes = plt.subplots(4, 1, figsize=(14, 11), sharex=True,
                             gridspec_kw={'height_ratios':[3, 2, 2, 1]})
    
    # ==========================================================
    # Panel 1: Power with segments colored by label
    # ==========================================================
    ax = axes[0]
    
    # Colored backgrounds for each segment
    for seg in segments:
        color = SUBSYSTEM_COLORS.get(seg["label"], "#999999")
        ax.axvspan(seg["t_start"], seg["t_end"], alpha=0.25, color=color)
    
    ax.plot(t, data["p_smooth"], 'k-', lw=0.6, label="Smoothed power")
    ax.plot(t, data["p_blocks"], 'k-', lw=0.2, alpha=0.3, label="Instantaneous")
    
    # Event markers
    for e in events[:50]:  # cap at 50 events
        symbol = '↑' if e["type"]=="rising" else '↓'
        color = 'green' if e["type"]=="rising" else 'red'
        ax.axvline(e["time"], color=color, alpha=0.3, lw=0.5)
    
    ax.set_ylabel("Power [W]")
    ax.set_title(f"{name}: Power consumption with subsystem labels (heuristic)\n"
                 f"Duration {t[-1]:.0f}s, avg={np.mean(data['p_smooth']):.0f}W, "
                 f"peak={np.max(data['p_smooth']):.0f}W")
    ax.grid(alpha=0.3)
    
    # Legend for labels
    legend_handles = []
    seen_labels = set()
    for seg in segments:
        if seg["label"] not in seen_labels:
            legend_handles.append(Patch(color=SUBSYSTEM_COLORS.get(seg["label"], "#999999"),
                                         alpha=0.4, label=seg["label"]))
            seen_labels.add(seg["label"])
    if legend_handles:
        ax.legend(handles=legend_handles, loc='upper right', ncol=3, fontsize=8)
    
    # ==========================================================
    # Panel 2: Phase currents
    # ==========================================================
    ax = axes[1]
    ax.plot(t, data["i0_rms"], 'b-', lw=0.6, label="I0 RMS")
    ax.plot(t, data["i1_rms"], 'r-', lw=0.6, label="I1 RMS", alpha=0.7)
    ax.set_ylabel("Current RMS [A]")
    ax.legend(loc='upper right', fontsize=9)
    ax.grid(alpha=0.3)
    
    # ==========================================================
    # Panel 3: Voltage RMS (should be constant ~240V)
    # ==========================================================
    ax = axes[2]
    ax.plot(t, data["u0_rms"], 'g-', lw=0.6)
    ax.set_ylabel("Voltage RMS [V]")
    ax.axhline(238, color='gray', ls='--', alpha=0.5, label='Expected ~238V')
    ax.legend(fontsize=9)
    ax.grid(alpha=0.3)
    
    # ==========================================================
    # Panel 4: Label timeline (visual segment overview)
    # ==========================================================
    ax = axes[3]
    for seg in segments:
        color = SUBSYSTEM_COLORS.get(seg["label"], "#999999")
        ax.barh(0, seg["duration"], left=seg["t_start"], height=0.8, 
                color=color, edgecolor='k', linewidth=0.3)
    ax.set_yticks([])
    ax.set_xlabel("Time [s]")
    ax.set_ylabel("Labels")
    ax.set_title("Auto-classified subsystem timeline (verify and refine in labeling tool)")
    
    fig.tight_layout()
    fig.savefig(save_path, dpi=120, bbox_inches='tight')
    plt.close(fig)


def export_for_labeling_tool(data, segments, name, out_dir):
    """Export CSV in format compatible with TRAINSET / Delabeye tool."""
    t = data["t"]
    p = data["p_smooth"]
    i0 = data["i0_rms"]
    i1 = data["i1_rms"]
    
    # Create label column from segments
    labels = ["idle"] * len(t)
    for seg in segments:
        idx = (t >= seg["t_start"]) & (t < seg["t_end"])
        for i, m in enumerate(idx):
            if m:
                labels[i] = seg["label"]
    
    # Write CSV
    csv_path = os.path.join(out_dir, f"{name}_for_labeling.csv")
    with open(csv_path, 'w') as f:
        # Header expected by most labeling tools
        f.write("time_s,power_W,I0_rms_A,I1_rms_A,label\n")
        for i in range(len(t)):
            f.write(f"{t[i]:.3f},{p[i]:.2f},{i0[i]:.3f},{i1[i]:.3f},{labels[i]}\n")
    
    return csv_path


def analyze_file(path):
    name = os.path.splitext(os.path.basename(path))[0]
    print(f"\n=== {name} ===", flush=True)
    
    # Load data
    data = load_tdms_decimated(path)
    print(f"  Loaded {data['n_samples']:,} samples ({data['duration']:.0f}s)", flush=True)
    
    # Detect events
    events = detect_events_advanced(data)
    print(f"  Detected {len(events)} events", flush=True)
    
    # Classify segments
    segments = classify_segments(data, events)
    print(f"  Created {len(segments)} segments", flush=True)
    
    # Generate visualization
    plot_path = os.path.join(OUT_DIR, f"{name}_labeled.png")
    generate_visualization(data, segments, events, name, plot_path)
    print(f"  Saved: {plot_path}", flush=True)
    
    # Export labeling-tool-compatible CSV
    csv_path = export_for_labeling_tool(data, segments, name, OUT_DIR)
    print(f"  Saved: {csv_path}", flush=True)
    
    # Summary stats
    p_distribution = {}
    for seg in segments:
        if seg["label"] not in p_distribution:
            p_distribution[seg["label"]] = []
        p_distribution[seg["label"]].append({
            "duration_s": seg["duration"],
            "p_avg_W": seg["p_avg_W"],
        })
    
    return {
        "file": name,
        "duration_s": float(data["duration"]),
        "n_events": len(events),
        "n_segments": len(segments),
        "label_distribution": {
            label: {
                "total_duration_s": sum(s["duration_s"] for s in segs),
                "avg_power_W": float(np.mean([s["p_avg_W"] for s in segs])),
                "n_segments": len(segs),
            }
            for label, segs in p_distribution.items()
        },
        "csv_path": csv_path,
        "plot_path": plot_path,
    }


if __name__ == "__main__":
    summaries = []
    for f in sorted(os.listdir(TDMS_DIR)):
        if f.endswith(".tdms"):
            try:
                summary = analyze_file(os.path.join(TDMS_DIR, f))
                summaries.append(summary)
            except Exception as e:
                print(f"  ERROR: {e}")
                import traceback
                traceback.print_exc()
    
    # Save complete metadata
    with open(os.path.join(OUT_DIR, "_summary.json"), 'w') as f:
        json.dump(summaries, f, indent=2)
    
    # Print final summary
    print(f"\n\n{'='*70}\nFINAL SUMMARY\n{'='*70}")
    for s in summaries:
        print(f"\n{s['file']}: {s['duration_s']:.0f}s, {s['n_events']} events, {s['n_segments']} segments")
        print(f"  Labels found:")
        for label, info in s["label_distribution"].items():
            print(f"    {label}: {info['total_duration_s']:.0f}s ({info['avg_power_W']:.0f}W avg)")
