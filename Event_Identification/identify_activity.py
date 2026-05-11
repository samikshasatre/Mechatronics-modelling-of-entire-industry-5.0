"""
ALIX Subsystem Activity Identification (NILM-style disaggregation)
==================================================================

Goal: Identify which subsystem was active, at what time, and for how long.

Method:
1. Detect power-level steps (rises and falls) in aggregate signal
2. Quantize step magnitudes to identify discrete machine activations
3. Track which machines are "ON" at each time
4. Output activity timeline (per-subsystem table + visualization)

Hypotheses about machine power signatures (will be refined with labels):
- MI00 conveyor: 80-120 W (small motor, light load)
- XY10 gantry steppers: 30-60 W idle, 100-200 W during motion
- MD20 Dobot CR5: 50-100 W idle, 150-300 W during arm motion
- AG10 MiR100 + UR5e: 100-200 W idle, 300-500 W during motion
- UC53 Quality station: 10-30 W (just computer + sensors)
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
OUT_DIR = "/home/claude/activity"
os.makedirs(OUT_DIR, exist_ok=True)

FS = 6000.2

# Power signatures: (typical_power_W, label, color)
# Order matters: largest steps first
SIGNATURES = [
    {"power": 200, "label": "MD20_dobot",     "color": "#2ca02c", "tolerance": 80},
    {"power": 150, "label": "AG10_agv",       "color": "#d62728", "tolerance": 60},
    {"power": 100, "label": "MI00_conveyor",  "color": "#1f77b4", "tolerance": 40},
    {"power": 80,  "label": "XY10_gantry",    "color": "#ff7f0e", "tolerance": 40},
    {"power": 30,  "label": "UC53_quality",   "color": "#9467bd", "tolerance": 20},
]


def load_and_smooth(path):
    """Load TDMS, compute smoothed power signal."""
    name = os.path.splitext(os.path.basename(path))[0]
    print(f"\n=== Processing {name} ===", flush=True)
    
    with TdmsFile.open(path) as tdms:
        grp = tdms["SIGNAUX"]
        gu = float(grp.properties["GAIN U 0"])
        gi = float(grp.properties["GAIN I 0"])
        u0 = grp["U0"][:] * gu
        u1 = grp["U1"][:] * gu
        i0 = grp["I0"][:] * gi
        i1 = grp["I1"][:] * gi
    
    # Remove DC offsets
    i0 -= np.mean(i0)
    i1 -= np.mean(i1)
    
    # Reconstruct phase 3
    u2 = -(u0 + u1)
    i2 = -(i0 + i1)
    
    # Instantaneous power
    p_inst = u0*i0 + u1*i1 + u2*i2
    
    # Block-average to 1 grid cycle
    cycle = 120
    n = len(u0)
    nb = n // cycle
    p_blocks = p_inst[:nb*cycle].reshape(nb, cycle).mean(axis=1)
    t_blocks = np.arange(nb) * (cycle / FS)
    
    # Sign correction
    if np.mean(p_blocks) < 0:
        p_blocks = -p_blocks
    
    # Heavy smoothing for step detection (~2 second window)
    smooth_n = 100  # 100 cycles = 2 seconds at 50 cycles/sec
    p_smooth = np.convolve(p_blocks, np.ones(smooth_n)/smooth_n, mode='same')
    
    return name, t_blocks, p_blocks, p_smooth


def detect_power_steps(t, p_smooth, min_step_W=20, min_separation_s=3.0):
    """Detect significant power-level changes.
    
    A step is detected when |dP| exceeds threshold.
    Returns list of {time, before_W, after_W, delta_W, type}.
    """
    # Compute differences over a window
    dt = t[1] - t[0]
    window_size = int(min_separation_s / dt / 2)  # half-window
    
    steps = []
    last_step_idx = -window_size * 2
    
    for i in range(window_size, len(p_smooth) - window_size):
        if i - last_step_idx < window_size * 2:
            continue
        
        # Compare averages before and after
        before = np.mean(p_smooth[i-window_size:i])
        after = np.mean(p_smooth[i:i+window_size])
        delta = after - before
        
        if abs(delta) > min_step_W:
            steps.append({
                "time": float(t[i]),
                "before_W": float(before),
                "after_W": float(after),
                "delta_W": float(delta),
                "type": "rising" if delta > 0 else "falling",
            })
            last_step_idx = i
    
    return steps


def match_step_to_machine(delta_W):
    """Assign a step magnitude to a likely machine.
    Returns the matching signature (or None if no match)."""
    abs_delta = abs(delta_W)
    
    # Check each signature, pick the closest match within tolerance
    best_match = None
    best_distance = float('inf')
    
    for sig in SIGNATURES:
        distance = abs(abs_delta - sig["power"])
        if distance < sig["tolerance"] and distance < best_distance:
            best_match = sig
            best_distance = distance
    
    return best_match


def build_activity_timeline(t, p_smooth, steps):
    """Build per-subsystem activity timeline based on detected steps.
    
    Returns:
        active_machines: dict mapping subsystem -> list of (start_time, end_time)
        segments: list of {t_start, t_end, active_set, total_power}
    """
    active_machines = {sig["label"]: [] for sig in SIGNATURES}
    
    # Process steps chronologically
    current_active = set()  # which machines are currently ON
    
    # Track machine activations (start time when ON)
    activation_times = {sig["label"]: None for sig in SIGNATURES}
    
    for step in steps:
        match = match_step_to_machine(step["delta_W"])
        if match is None:
            continue
        
        machine = match["label"]
        
        if step["type"] == "rising":
            # Machine turning ON
            if machine not in current_active:
                current_active.add(machine)
                activation_times[machine] = step["time"]
        else:  # falling
            # Machine turning OFF
            if machine in current_active:
                current_active.remove(machine)
                if activation_times[machine] is not None:
                    active_machines[machine].append((
                        activation_times[machine],
                        step["time"]
                    ))
                    activation_times[machine] = None
    
    # Close any still-active machines at end of recording
    end_time = t[-1]
    for machine in list(current_active):
        if activation_times[machine] is not None:
            active_machines[machine].append((activation_times[machine], end_time))
    
    # Build segment list (each time the active set changes)
    return active_machines


def build_segments_from_intervals(active_machines, total_duration):
    """Build a sequential segment list showing exact active set at each time."""
    # Collect all transition times
    transitions = set([0.0, total_duration])
    for machine, intervals in active_machines.items():
        for start, end in intervals:
            transitions.add(start)
            transitions.add(end)
    transitions = sorted(transitions)
    
    segments = []
    for i in range(len(transitions) - 1):
        t_start = transitions[i]
        t_end = transitions[i+1]
        if t_end - t_start < 0.5:  # skip very short
            continue
        
        active_set = []
        for machine, intervals in active_machines.items():
            for start, end in intervals:
                if start <= t_start + 0.1 and end >= t_end - 0.1:
                    active_set.append(machine)
                    break
        
        segments.append({
            "t_start": float(t_start),
            "t_end": float(t_end),
            "duration": float(t_end - t_start),
            "active": active_set,
            "active_str": " + ".join(active_set) if active_set else "idle",
        })
    
    return segments


def visualize_activity(name, t, p_smooth, steps, active_machines, segments, save_path):
    """Create comprehensive activity visualization."""
    fig = plt.figure(figsize=(15, 10))
    gs = fig.add_gridspec(4, 1, height_ratios=[3, 1.5, 0.6, 0.6])
    
    # Panel 1: Power with detected steps
    ax1 = fig.add_subplot(gs[0])
    ax1.plot(t, p_smooth, 'k-', lw=0.8, label="Smoothed power")
    
    for step in steps:
        match = match_step_to_machine(step["delta_W"])
        if match:
            color = match["color"]
            label_text = f"{'+' if step['type']=='rising' else '-'}{match['label']}"
        else:
            color = 'gray'
            label_text = f"{step['delta_W']:+.0f}W"
        ax1.axvline(step["time"], color=color, alpha=0.4, lw=0.7)
        ax1.text(step["time"], step["after_W"], label_text, 
                rotation=90, fontsize=6, va='bottom', alpha=0.7)
    
    ax1.set_ylabel("Power [W]")
    ax1.set_title(f"{name}: Aggregate power consumption with detected machine events\n"
                  f"Duration: {t[-1]:.0f}s, peak: {np.max(p_smooth):.0f}W")
    ax1.grid(alpha=0.3)
    
    # Panel 2: Per-machine activity bars
    ax2 = fig.add_subplot(gs[1], sharex=ax1)
    machine_list = list(active_machines.keys())
    y_positions = list(range(len(machine_list)))
    
    for y, machine in zip(y_positions, machine_list):
        # Find color
        color = "#999999"
        for sig in SIGNATURES:
            if sig["label"] == machine:
                color = sig["color"]
                break
        
        intervals = active_machines[machine]
        for start, end in intervals:
            ax2.barh(y, end - start, left=start, height=0.7, 
                    color=color, edgecolor='k', linewidth=0.3)
    
    ax2.set_yticks(y_positions)
    ax2.set_yticklabels(machine_list)
    ax2.set_ylabel("Subsystem")
    ax2.set_title("Per-subsystem activity timeline (when each was ON)")
    ax2.grid(alpha=0.3, axis='x')
    
    # Panel 3: Combined active-set timeline (which combinations active)
    ax3 = fig.add_subplot(gs[2], sharex=ax1)
    for seg in segments:
        # Color based on number of active machines
        n_active = len(seg["active"])
        if n_active == 0:
            color = "#cccccc"
        elif n_active == 1:
            for sig in SIGNATURES:
                if sig["label"] == seg["active"][0]:
                    color = sig["color"]
                    break
            else:
                color = "#999999"
        else:
            color = "#8c564b"  # brown for multi
        
        ax3.barh(0, seg["duration"], left=seg["t_start"], height=0.8,
                color=color, edgecolor='k', linewidth=0.2)
    
    ax3.set_yticks([])
    ax3.set_ylabel("Active set")
    
    # Panel 4: Time axis annotation
    ax4 = fig.add_subplot(gs[3], sharex=ax1)
    ax4.set_ylim(0, 1)
    ax4.set_yticks([])
    ax4.set_xlabel("Time [s]")
    
    # Show segment text annotations
    for seg in segments:
        if seg["duration"] > 20:  # only annotate longer segments
            mid = (seg["t_start"] + seg["t_end"]) / 2
            ax4.text(mid, 0.5, seg["active_str"][:30], 
                    rotation=0, fontsize=7, ha='center', va='center',
                    bbox=dict(boxstyle='round,pad=0.2', facecolor='white', 
                            edgecolor='gray', alpha=0.7))
    
    plt.tight_layout()
    fig.savefig(save_path, dpi=110, bbox_inches='tight')
    plt.close(fig)


def export_activity_table(name, segments, active_machines, out_path):
    """Export structured activity table (CSV + JSON)."""
    # CSV format
    csv_path = out_path.replace(".json", ".csv")
    with open(csv_path, "w") as f:
        f.write("subsystem,start_time_s,end_time_s,duration_s\n")
        for machine, intervals in active_machines.items():
            for start, end in intervals:
                f.write(f"{machine},{start:.2f},{end:.2f},{end-start:.2f}\n")
    
    # JSON format with full info
    output = {
        "file": name,
        "total_duration_s": segments[-1]["t_end"] if segments else 0,
        "subsystem_intervals": {
            machine: [{"start_s": s, "end_s": e, "duration_s": e-s} 
                     for s, e in intervals]
            for machine, intervals in active_machines.items()
        },
        "segments": segments,
        "summary": {
            machine: {
                "total_active_s": sum(e - s for s, e in intervals),
                "n_activations": len(intervals),
            }
            for machine, intervals in active_machines.items()
        }
    }
    
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)
    
    return csv_path, out_path


def analyze(path):
    name, t, p_blocks, p_smooth = load_and_smooth(path)
    
    # Detect steps
    steps = detect_power_steps(t, p_smooth, min_step_W=20)
    print(f"  Detected {len(steps)} power steps", flush=True)
    
    # Build activity timeline
    active_machines = build_activity_timeline(t, p_smooth, steps)
    
    # Build segments
    segments = build_segments_from_intervals(active_machines, t[-1])
    print(f"  Created {len(segments)} time segments", flush=True)
    
    # Visualize
    plot_path = os.path.join(OUT_DIR, f"{name}_activity.png")
    visualize_activity(name, t, p_smooth, steps, active_machines, segments, plot_path)
    print(f"  Saved plot: {plot_path}", flush=True)
    
    # Export tables
    csv_path, json_path = export_activity_table(
        name, segments, active_machines,
        os.path.join(OUT_DIR, f"{name}_activity.json")
    )
    print(f"  Saved data: {csv_path}, {json_path}", flush=True)
    
    # Print summary table
    print(f"\n  ACTIVITY SUMMARY for {name}:")
    print(f"  {'Subsystem':<20} {'Total active (s)':<20} {'# activations':<15}")
    print(f"  {'-'*55}")
    for machine, intervals in active_machines.items():
        total = sum(e - s for s, e in intervals)
        if total > 0:
            print(f"  {machine:<20} {total:<20.1f} {len(intervals):<15}")
    
    return {
        "name": name,
        "active_machines": active_machines,
        "segments": segments,
        "steps": steps,
    }


if __name__ == "__main__":
    results = []
    for f in sorted(os.listdir(TDMS_DIR)):
        if f.endswith(".tdms"):
            try:
                r = analyze(os.path.join(TDMS_DIR, f))
                results.append(r)
            except Exception as e:
                print(f"  ERROR: {e}")
                import traceback
                traceback.print_exc()
    
    print(f"\n\n{'='*60}")
    print("ALL FILES PROCESSED")
    print(f"{'='*60}")
    for r in results:
        print(f"\n{r['name']}: {len(r['segments'])} segments, "
              f"{len(r['steps'])} steps detected")
