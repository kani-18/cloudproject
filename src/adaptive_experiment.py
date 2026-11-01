
import os
import csv
import traci

from rsu_twin import DigitalTwin
from metrics import position_error, speed_error, heading_error

os.environ["SUMO_HOME"] = "/usr/share/sumo"

PACKET_SIZE_BYTES = 100
SIMULATION_DURATION = 120.0
STEP = 0.05

# Three synchronization intervals
FAST_INTERVAL = 0.05       # 50 ms
MEDIUM_INTERVAL = 0.10     # 100 ms
SLOW_INTERVAL = 0.50       # 500 ms

# AoI thresholds
HIGH_AOI = 0.20
LOW_AOI = 0.05

# Mobility thresholds
HIGH_SPEED = 10.0
HIGH_ACCELERATION = 2.0


def choose_interval(aoi, state):
    """Choose a synchronization interval using AoI and mobility."""

    speed = state["speed"]
    acceleration = abs(state["acceleration"])

    # Urgent synchronization: stale information or rapid mobility.
    if (
        aoi is None
        or aoi >= HIGH_AOI
        or acceleration >= HIGH_ACCELERATION
    ):
        return FAST_INTERVAL

    # Moderate synchronization: moving vehicle or moderately stale twin.
    if speed >= HIGH_SPEED or aoi > LOW_AOI:
        return MEDIUM_INTERVAL

    # Relaxed synchronization for low-speed, fresh twin state.
    return SLOW_INTERVAL


def run_experiment():
    twin = DigitalTwin()

    next_update_time = {}
    current_interval = {}
    rows = []
    transmission_attempts = 0

    os.makedirs("results", exist_ok=True)

    traci.start([
        "sumo",
        "-c", "sumo/simulation.sumocfg",
        "--no-step-log",
        "--duration-log.disable"
    ])

    try:
        while traci.simulation.getMinExpectedNumber() > 0:
            traci.simulationStep()
            t = traci.simulation.getTime()

            for vid in traci.vehicle.getIDList():
                x, y = traci.vehicle.getPosition(vid)

                actual = {
                    "x": x,
                    "y": y,
                    "speed": traci.vehicle.getSpeed(vid),
                    "heading": traci.vehicle.getAngle(vid),
                    "acceleration": traci.vehicle.getAcceleration(vid),
                }

                if vid not in next_update_time:
                    next_update_time[vid] = t
                    current_interval[vid] = FAST_INTERVAL

                # Estimate freshness before deciding on a new transmission.
                aoi_before = twin.get_aoi(vid, t)
                interval = choose_interval(aoi_before, actual)
                current_interval[vid] = interval

                # Send immediately when first seen or when due.
                if t + 1e-9 >= next_update_time[vid]:
                    transmission_attempts += 1

                    # Ideal channel: immediate successful delivery.
                    twin.receive_update(vid, actual, t, t)

                    # Schedule the next transmission using the selected interval.
                    next_update_time[vid] = t + interval

                stored = twin.get_state(vid)
                aoi_after = twin.get_aoi(vid, t)

                rows.append({
                    "time": t,
                    "vehicle_id": vid,
                    "aoi": aoi_after,
                    "position_error": position_error(actual, stored),
                    "speed_error": speed_error(actual, stored),
                    "heading_error": heading_error(actual, stored),
                    "adaptive_interval": interval,
                })

    finally:
        traci.close()

    if not rows:
        raise RuntimeError("No samples collected; check the SUMO configuration.")

    duration = SIMULATION_DURATION
    delivered_packets = transmission_attempts

    summary = {
        "strategy": "AoI-aware-adaptive-v2",
        "samples": len(rows),
        "transmission_attempts": transmission_attempts,
        "delivered_packets": delivered_packets,
        "average_aoi_s": sum(r["aoi"] for r in rows) / len(rows),
        "average_position_error_m": (
            sum(r["position_error"] for r in rows) / len(rows)
        ),
        "overhead_bytes_per_sec": (
            delivered_packets * PACKET_SIZE_BYTES / duration
        ),
        "pdr_percent": (
            100.0 * delivered_packets / transmission_attempts
            if transmission_attempts else 0.0
        ),
    }

    with open("results/adaptive_v2.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    with open("results/adaptive_v2_summary.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=summary.keys())
        writer.writeheader()
        writer.writerow(summary)

    print("\nAdaptive synchronization v2:")
    for key, value in summary.items():
        print(f"{key}: {value}")

    print("\nSaved results/adaptive_v2.csv")
    print("Saved results/adaptive_v2_summary.csv")


if __name__ == "__main__":
    run_experiment()

