import os
import csv
import traci

from rsu_twin import DigitalTwin
from metrics import position_error, speed_error, heading_error

os.environ["SUMO_HOME"] = "/usr/share/sumo"

STEP = 0.05
UPDATE_INTERVALS = [0.05, 0.10, 0.50]
PACKET_SIZE_BYTES = 100

os.makedirs("results", exist_ok=True)

def run_experiment(interval):
    twin = DigitalTwin()
    rows = []
    attempts = 0
    delivered = 0
    next_update = {}

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

                # First observation: initialize this vehicle's schedule.
                if vid not in next_update:
                    next_update[vid] = t

                # Periodic transmission attempt.
                if t + 1e-9 >= next_update[vid]:
                    attempts += 1

                    # Ideal channel: all packets are delivered immediately.
                    twin.receive_update(vid, actual, t, t)
                    delivered += 1

                    next_update[vid] += interval

                    # Prevent a backlog of missed scheduled transmissions.
                    if next_update[vid] <= t:
                        next_update[vid] = t + interval

                stored = twin.get_state(vid)
                aoi = twin.get_aoi(vid, t)

                rows.append({
                    "time": t,
                    "vehicle_id": vid,
                    "interval_ms": int(interval * 1000),
                    "aoi": aoi,
                    "position_error": position_error(actual, stored),
                    "speed_error": speed_error(actual, stored),
                    "heading_error": heading_error(actual, stored),
                })

    finally:
        traci.close()

    # Simulation duration is the configured 120 seconds.
    duration = 120.0
    overhead = attempts * PACKET_SIZE_BYTES / duration
    pdr = 100.0 * delivered / attempts if attempts else 0.0

    filename = f"results/periodic_{int(interval * 1000)}ms.csv"
    with open(filename, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    average_aoi = sum(r["aoi"] for r in rows) / len(rows)
    average_position_error = (
        sum(r["position_error"] for r in rows) / len(rows)
    )

    summary = {
        "strategy": "periodic",
        "interval_ms": int(interval * 1000),
        "samples": len(rows),
        "transmission_attempts": attempts,
        "delivered_packets": delivered,
        "average_aoi_s": average_aoi,
        "average_position_error_m": average_position_error,
        "overhead_bytes_per_sec": overhead,
        "pdr_percent": pdr,
    }

    print(summary)
    return summary


summaries = [run_experiment(interval) for interval in UPDATE_INTERVALS]

with open("results/periodic_summary.csv", "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=summaries[0].keys())
    writer.writeheader()
    writer.writerows(summaries)

print("\nPeriodic experiments completed.")
print("Summary saved to results/periodic_summary.csv")
