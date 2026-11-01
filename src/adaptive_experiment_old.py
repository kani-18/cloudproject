
import os
import csv
import traci

from rsu_twin import DigitalTwin
from metrics import position_error, speed_error, heading_error

os.environ["SUMO_HOME"] = "/usr/share/sumo"

PACKET_SIZE_BYTES = 100
SIMULATION_DURATION = 120.0

# Adaptive synchronization interval limits
MIN_INTERVAL = 0.05       # 50 ms
MAX_INTERVAL = 0.50       # 500 ms

# AoI thresholds
HIGH_AOI = 0.20           # seconds
LOW_AOI = 0.05            # seconds

# Mobility threshold
HIGH_SPEED = 10.0         # m/s


def run_experiment():
    twin = DigitalTwin()

    last_sent_state = {}
    next_update_time = {}
    current_interval = {}

    rows = []
    transmission_attempts = 0

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

                if vid not in current_interval:
                    current_interval[vid] = MAX_INTERVAL
                    next_update_time[vid] = t

                aoi = twin.get_aoi(vid, t)

                # Adapt the interval using AoI and vehicle mobility.
                if (
                    aoi is None
                    or aoi >= HIGH_AOI
                    or actual["speed"] >= HIGH_SPEED
                    or abs(actual["acceleration"]) >= 2.0
                ):
                    current_interval[vid] = MIN_INTERVAL

                elif aoi <= LOW_AOI and actual["speed"] < HIGH_SPEED:
                    current_interval[vid] = MAX_INTERVAL

                # Transmit when the scheduled update time is reached.
                if t + 1e-9 >= next_update_time[vid]:
                    transmission_attempts += 1

                    # Ideal channel: immediate successful delivery.
                    twin.receive_update(vid, actual, t, t)

                    last_sent_state[vid] = actual.copy()
                    next_update_time[vid] = (
                        t + current_interval[vid]
                    )

                stored = twin.get_state(vid)
                aoi = twin.get_aoi(vid, t)

                rows.append({
                    "time": t,
                    "vehicle_id": vid,
                    "aoi": aoi,
                    "position_error": position_error(actual, stored),
                    "speed_error": speed_error(actual, stored),
                    "heading_error": heading_error(actual, stored),
                    "adaptive_interval": current_interval[vid],
                })

    finally:
        traci.close()

    if not rows:
        raise RuntimeError(
            "No simulation samples were collected. Check the SUMO configuration."
        )

    duration = SIMULATION_DURATION
    delivered_packets = transmission_attempts

    summary = {
        "strategy": "AoI-aware-adaptive",
        "samples": len(rows),
        "transmission_attempts": transmission_attempts,
        "delivered_packets": delivered_packets,
        "average_aoi_s": (
            sum(r["aoi"] for r in rows) / len(rows)
        ),
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

    os.makedirs("results", exist_ok=True)

    with open(
        "results/adaptive_triggered.csv", "w", newline=""
    ) as f:
        writer = csv.DictWriter(
            f, fieldnames=rows[0].keys()
        )
        writer.writeheader()
        writer.writerows(rows)

    with open(
        "results/adaptive_summary.csv", "w", newline=""
    ) as f:
        writer = csv.DictWriter(
            f, fieldnames=summary.keys()
        )
        writer.writeheader()
        writer.writerow(summary)

    print("\nAdaptive synchronization results:")
    for key, value in summary.items():
        print(f"{key}: {value}")

    print("\nSaved results/adaptive_triggered.csv")
    print("Saved results/adaptive_summary.csv")


if __name__ == "__main__":
    run_experiment()
