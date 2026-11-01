
import os
import csv
import traci

from rsu_twin import DigitalTwin
from metrics import position_error
from channel import CommunicationChannel

os.environ["SUMO_HOME"] = "/usr/share/sumo"

INTERVAL = 0.10
STEP = 0.05
DURATION = 120.0
PACKET_SIZE_BYTES = 100

# (condition, delay in seconds, packet-loss probability)
CONDITIONS = [
    ("ideal", 0.00, 0.00),
    ("moderate", 0.05, 0.05),
    ("poor", 0.10, 0.10),
]


def run_condition(name, delay, loss):
    twin = DigitalTwin()

    channel = CommunicationChannel(
        delay_s=delay,
        loss_probability=loss,
        seed=42,
    )

    next_update = {}
    aoi_sum = 0.0
    position_error_sum = 0.0
    valid_samples = 0

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

            # Process packets that have arrived at the RSU.
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

                # Count only samples for which the twin has received data.
                if stored is not None and aoi is not None:
                    aoi_sum += aoi
                    position_error_sum += position_error(actual, stored)
                    valid_samples += 1

        # Drain packets still in flight. This affects delivery counts,
        # but samples are not added after the SUMO simulation ends.
        for packet in channel.receive_ready(DURATION + delay):
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

    return {
        "condition": name,
        "delay_ms": int(delay * 1000),
        "configured_loss_percent": loss * 100,
        "samples_with_twin": valid_samples,
        "transmission_attempts": attempts,
        "delivered_packets": delivered,
        "dropped_packets": channel.dropped,
        "pdr_percent": 100 * delivered / attempts if attempts else 0,
        "average_aoi_s": aoi_sum / valid_samples if valid_samples else "",
        "average_position_error_m": (
            position_error_sum / valid_samples if valid_samples else ""
        ),
        "overhead_bytes_per_sec": attempts * PACKET_SIZE_BYTES / DURATION,
    }


def main():
    results = []

    for name, delay, loss in CONDITIONS:
        result = run_condition(name, delay, loss)
        results.append(result)

        print(f"\nCondition: {name}")
        for key, value in result.items():
            print(f"{key}: {value}")

    os.makedirs("results", exist_ok=True)

    output = "results/channel_sensitivity_summary.csv"

    with open(output, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=results[0].keys())
        writer.writeheader()
        writer.writerows(results)

    print(f"\nSaved {output}")


if __name__ == "__main__":
    main()
