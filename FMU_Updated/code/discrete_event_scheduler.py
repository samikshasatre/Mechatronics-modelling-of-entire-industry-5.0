"""
discrete_event_scheduler.py
============================
Discrete-event scheduler for the ALIX line.
Models workpiece-driven activation timing and task dependencies.
"""

import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
from heapq import heappush, heappop
from pathlib import Path

OUT_DIR = Path(r"C:\Users\satres\Documents\ALIX\FMU_Updated\orchestration_output")
OUT_DIR.mkdir(exist_ok=True)

# LINE CONFIGURATION
LINE_LENGTH    = 8.4
BELT_SPEED     = 0.196
T_SIM          = 120.0

STATION_X = {
    "ON10": 0.0,
    "CR5":  2.1,
    "XY10": 4.2,
    "DX10": 6.3,
    "VL10": 8.4,
}

TASK_DURATION = {
    "CR5":  5.0,
    "XY10": 10.0,
    "DX10": 2.0,
}

WORKPIECE_SPAWN_INTERVAL = 30.0

# EVENT-DRIVEN SIMULATION
event_queue = []
log = []
station_busy_until = {s: 0.0 for s in TASK_DURATION}
station_queue = {s: [] for s in TASK_DURATION}
workpiece_state = {}

def schedule(t, event_type, wp_id, data=None):
    heappush(event_queue, (t, event_type, wp_id, data))

def log_event(t, wp_id, station, action):
    log.append({"time_s": round(t, 3), "workpiece": wp_id,
                "station": station, "action": action})
    print(f"  t={t:7.2f} s   WP{wp_id:02d}   {station:5s}   {action}")

# EVENT HANDLERS
def handle_spawn(t, wp_id):
    workpiece_state[wp_id] = "WAITING_AT_ON10"
    log_event(t, wp_id, "ON10", "SPAWNED on conveyor")
    travel = (STATION_X["CR5"] - STATION_X["ON10"]) / BELT_SPEED
    schedule(t + travel, "arrive", wp_id, "CR5")

def handle_arrive(t, wp_id, station):
    workpiece_state[wp_id] = f"ARRIVED_AT_{station}"
    log_event(t, wp_id, station, "arrived")
    # VL10 is the exit — no service, just leave
    if station == "VL10":
        workpiece_state[wp_id] = "FINISHED"
        log_event(t, wp_id, "VL10", "EXIT line")
        return
    if station_busy_until[station] > t:
        log_event(t, wp_id, station,
                  f"queued (busy until t={station_busy_until[station]:.2f})")
        station_queue[station].append((t, wp_id))
    else:
        schedule(t, "start_service", wp_id, station)

def handle_start_service(t, wp_id, station):
    duration = TASK_DURATION[station]
    station_busy_until[station] = t + duration
    workpiece_state[wp_id] = f"BEING_SERVICED_AT_{station}"
    log_event(t, wp_id, station, f"START task (duration {duration:.1f} s)")
    schedule(t + duration, "end_service", wp_id, station)

def handle_end_service(t, wp_id, station):
    workpiece_state[wp_id] = f"COMPLETED_AT_{station}"
    log_event(t, wp_id, station, "END task")
    if station_queue[station]:
        _, next_wp = station_queue[station].pop(0)
        schedule(t, "start_service", next_wp, station)
    NEXT = {"CR5": "XY10", "XY10": "DX10", "DX10": "VL10"}
    if station in NEXT:
        next_st = NEXT[station]
        travel = (STATION_X[next_st] - STATION_X[station]) / BELT_SPEED
        schedule(t + travel, "arrive", wp_id, next_st)

# INITIAL EVENTS
print("=" * 75)
print("ALIX LINE - DISCRETE-EVENT SCHEDULER")
print("=" * 75)
print(f"Simulating {T_SIM:.0f} s, spawning 1 piece every "
      f"{WORKPIECE_SPAWN_INTERVAL:.0f} s\n")

n_pieces = int(T_SIM // WORKPIECE_SPAWN_INTERVAL) + 1
for i in range(n_pieces):
    schedule(i * WORKPIECE_SPAWN_INTERVAL, "spawn", i, None)

# MAIN LOOP
while event_queue:
    t, event_type, wp_id, data = heappop(event_queue)
    if t > T_SIM:
        break
    if event_type == "spawn":
        handle_spawn(t, wp_id)
    elif event_type == "arrive":
        handle_arrive(t, wp_id, data)
    elif event_type == "start_service":
        handle_start_service(t, wp_id, data)
    elif event_type == "end_service":
        handle_end_service(t, wp_id, data)

print(f"\n{'='*75}")
print(f"SIMULATION COMPLETE - {len(log)} events logged")
print(f"{'='*75}\n")

# SAVE CSV
df = pd.DataFrame(log)
csv_path = OUT_DIR / "discrete_event_log.csv"
df.to_csv(csv_path, index=False)
print(f"Event log saved: {csv_path} ({len(df)} rows)")

# GANTT CHART
fig, ax = plt.subplots(figsize=(15, 6))
station_y = {"CR5": 3, "XY10": 2, "DX10": 1}
station_color = {"CR5": "#A93226", "XY10": "#27AE60", "DX10": "#8E44AD"}

for ev in log:
    if "START task" in ev["action"]:
        end_time = None
        for ev2 in log:
            if (ev2["workpiece"] == ev["workpiece"]
                and ev2["station"] == ev["station"]
                and "END task" in ev2["action"]
                and ev2["time_s"] > ev["time_s"]):
                end_time = ev2["time_s"]
                break
        if end_time and ev["station"] in station_y:
            ax.barh(station_y[ev["station"]],
                    end_time - ev["time_s"],
                    left=ev["time_s"], height=0.7,
                    color=station_color[ev["station"]],
                    edgecolor="black", lw=0.5, alpha=0.85)
            ax.text(ev["time_s"] + (end_time - ev["time_s"])/2,
                    station_y[ev["station"]],
                    f"WP{ev['workpiece']}",
                    ha="center", va="center", fontsize=8,
                    color="white", fontweight="bold")

ax.set_yticks([1, 2, 3])
ax.set_yticklabels(["DX10\n(inspection)", "XY10\n(pick-place)", "CR5\n(assembly)"])
ax.set_xlabel("Time (s)", fontsize=11)
ax.set_xlim(0, T_SIM)
ax.set_title("ALIX Line - Discrete-Event Gantt Chart "
             f"({n_pieces} workpieces, {WORKPIECE_SPAWN_INTERVAL:.0f}-s cadence)",
             fontsize=13, fontweight="bold")
ax.grid(axis="x", alpha=0.3)

for i in range(n_pieces):
    ax.axvline(i * WORKPIECE_SPAWN_INTERVAL, color="grey", ls=":", alpha=0.5)
    ax.text(i * WORKPIECE_SPAWN_INTERVAL, 3.6, f"WP{i} in",
            ha="center", fontsize=7, color="grey", style="italic")

plt.tight_layout()
gantt_path = OUT_DIR / "discrete_event_gantt.png"
plt.savefig(gantt_path, dpi=180, bbox_inches="tight")
print(f"Gantt chart saved: {gantt_path}")
plt.show()

# SUMMARY
finished = sum(1 for v in workpiece_state.values() if v == "FINISHED")
print(f"\nSUMMARY")
print(f"  Pieces spawned   : {n_pieces}")
print(f"  Pieces finished  : {finished}")
print(f"  Theoretical throughput: 1 piece / {WORKPIECE_SPAWN_INTERVAL:.0f} s = "
      f"{3600/WORKPIECE_SPAWN_INTERVAL:.0f} pieces/h")