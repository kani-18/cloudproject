
import os
import csv
import traci

from rsu_twin import DigitalTwin
from metrics import position_error, speed_error, heading_error
from channel import CommunicationChannel

os.environ["SUMO_HOME"] = "/usr/share/sumo"

INTERVAL = 0.10
STEP = 0.05
DURATION = 120.0
PACKET_SIZE_BYTES = 100

CHANNEL_DELAY = 0.05
PACKET_LOSS = 0.05


def run_experiment():
    twin = DigitalTwin()

    channel = CommunicationChannel(
        delay_s=CHANNEL_DELAY,
        loss_probability=PACKET_LOSS,
        seed=42,
    )

    next_update = {}
    rows = []

    os.makedirs("results", exist_ok=True)

    traci.start([
        "sumo",
        "-c", "sumo/simulation.sumocfg",
        "--no-step-log",
        "--duration-log.disable",
    ])

    try:
        while traci.simulation.getMinExpectedNumber() > 0:
            traci.simulationStep()
            t = traci.simulation.getTime()

            # Deliver packets that have reached the RSU by this time.
            for packet in channel.receive_ready(t):
                twin.receive_update(
                    packet["vehicle_id"],
                    packet["state"],
                    packet["generation_time"],
                    packet["arrival_time"],
                )

            for vid in traci.vehicle.getIDList():
                x, y = traci.vehicle.getPosition(vid)

                actual = {
                    "x": x,
                    "y": y,
                    "speed": traci.vehicle.getSpeed(vid),
                    "heading": traci.vehicle.getAngle(vid),
                    "acceleration": traci.vehicle.getAcceleration(vid),
                }

                if vid not in next_update:
                    next_update[vid] = t

                if t + 1e-9 >= next_update[vid]:
                    channel.transmit(vid, actual, t)

                    next_update[vid] += INTERVAL
                    if next_update[vid] <= t:
                        next_update[vid] = t + INTERVAL

                stored = twin.get_state(vid)
                aoi = twin.get_aoi(vid, t)

                rows.append({
                    "time": t,
                    "vehicle_id": vid,
                    "aoi": aoi if aoi is not None else "",
                    "position_error": (
                        position_error(actual, stored)
                        if stored is not None else ""
                    ),
                    "speed_error": (
                        speed_error(actual, stored)
                        if stored is not None else ""
                    ),
                    "heading_error": (
                        heading_error(actual, stored)
                        if stored is not None else ""
                    ),
                })

        # Flush packets still in flight at the end of SUMO.
        for packet in channel.receive_ready(DURATION + CHANNEL_DELAY):
            twin.receive_update(
                packet["vehicle_id"],
                packet["state"],
                packet["generation_time"],
                packet["arrival_time"],
            )

    finally:
        traci.close()

    attempts = channel.attempts
    delivered = channel.delivered

    summary = {
        "strategy": "periodic",
        "interval_ms": int(INTERVAL * 1000),
        "channel_delay_ms": int(CHANNEL_DELAY * 1000),
        "configured_loss_percent": PACKET_LOSS * 100,
        "samples": len(rows),
        "transmission_attempts": attempts,
        "delivered_packets": delivered,
        "dropped_packets": channel.dropped,
        "average_aoi_s": "",
        "average_position_error_m": "",
        "overhead_bytes_per_sec": attempts * PACKET_SIZE_BYTES / DURATION,
        "pdr_percent": 100.0 * delivered / attempts if attempts else 0.0,
    }

    # Exclude samples before the first packet reaches the RSU.
    valid_rows = [r for r in rows if r["aoi"] != ""]

    if valid_rows:
        summary["average_aoi_s"] = sum(
            float(r["aoi"]) for r in valid_rows
        ) / len(valid_rows)

        summary["average_position_error_m"] = sum(
            float(r["position_error"]) for r in valid_rows
        ) / len(valid_rows)

    with open("results/periodic_100ms_channel.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    with open("results/periodic_100ms_channel_summary.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=summary.keys())
        writer.writeheader()
        writer.writerow(summary)

    print("\nPeriodic 100 ms with channel effects:")
    for key, value in summary.items():
        print(f"{key}: {value}")

    print("\nSaved results/periodic_100ms_channel.csv")
    print("Saved results/periodic_100ms_channel_summary.csv")


if __name__ == "__main__":
    run_experiment()
