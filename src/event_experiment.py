import os
import csv
import traci

from rsu_twin import DigitalTwin
from metrics import position_error, speed_error, heading_error

os.environ["SUMO_HOME"] = "/usr/share/sumo"

PACKET_SIZE_BYTES = 100

# Initial thresholds; we can tune these later.
POSITION_THRESHOLD = 5.0       # metres
SPEED_THRESHOLD = 2.0          # m/s
HEADING_THRESHOLD = 15.0       # degrees
ACCEL_THRESHOLD = 2.0          # m/s^2


def angle_difference(a, b):
    return abs((a - b + 180.0) % 360.0 - 180.0)


def run_experiment():
    twin = DigitalTwin()
    last_sent_state = {}
    rows = []
    attempts = 0

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

                previous = last_sent_state.get(vid)

                # Send the first update immediately.
                triggered = previous is None

                if previous is not None:
                    distance = (
                        (actual["x"] - previous["x"]) ** 2
                        + (actual["y"] - previous["y"]) ** 2
                    ) ** 0.5

                    triggered = (
                        distance >= POSITION_THRESHOLD
                        or abs(actual["speed"] - previous["speed"])
                            >= SPEED_THRESHOLD
                        or angle_difference(
                            actual["heading"], previous["heading"]
                        ) >= HEADING_THRESHOLD
                        or abs(
                            actual["acceleration"] - previous["acceleration"]
                        ) >= ACCEL_THRESHOLD
                    )

                if triggered:
                    attempts += 1

                    # Ideal channel: immediate, successful delivery.
                    twin.receive_update(vid, actual, t, t)
                    last_sent_state[vid] = actual.copy()

                stored = twin.get_state(vid)
                aoi = twin.get_aoi(vid, t)

                rows.append({
                    "time": t,
                    "vehicle_id": vid,
                    "aoi": aoi,
                    "position_error": position_error(actual, stored),
                    "speed_error": speed_error(actual, stored),
                    "heading_error": heading_error(actual, stored),
                })

    finally:
        traci.close()

    duration = 120.0
    delivered = attempts
    overhead = attempts * PACKET_SIZE_BYTES / duration
    pdr = 100.0 if attempts else 0.0

    with open("results/event_triggered.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    summary = {
        "strategy": "event-triggered",
        "samples": len(rows),
        "transmission_attempts": attempts,
        "delivered_packets": delivered,
        "average_aoi_s": sum(r["aoi"] for r in rows) / len(rows),
        "average_position_error_m": (
            sum(r["position_error"] for r in rows) / len(rows)
        ),
        "overhead_bytes_per_sec": overhead,
        "pdr_percent": pdr,
    }

    with open("results/event_summary.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=summary.keys())
        writer.writeheader()
        writer.writerow(summary)

    print(summary)
    print("Saved results/event_triggered.csv")
    print("Saved results/event_summary.csv")


if __name__ == "__main__":
    run_experiment()
