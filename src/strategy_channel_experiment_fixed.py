
import os
import csv
import math
import sys
from pathlib import Path

# Resolve project paths from this file, not from the terminal's current directory.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
os.environ.setdefault("SUMO_HOME", "/usr/share/sumo")

import traci

from rsu_twin import DigitalTwin
from metrics import position_error, speed_error, heading_error
from channel import CommunicationChannel


STEP = 0.05
DURATION = 120.0
PACKET_SIZE_BYTES = 100

CHANNEL_DELAY = 0.05
PACKET_LOSS = 0.05

POSITION_THRESHOLD = 5.0
SPEED_THRESHOLD = 2.0
HEADING_THRESHOLD = 15.0
ACCEL_THRESHOLD = 2.0

# Event-triggered strategy sends at least once every 500 ms.
EVENT_MAX_INTERVAL = 0.50

HIGH_AOI = 0.20
LOW_AOI = 0.05
HIGH_SPEED = 10.0


def angle_difference(a, b):
    return abs((a - b + 180.0) % 360.0 - 180.0)


def choose_adaptive_interval(aoi, state):
    if (
        aoi is None
        or aoi >= HIGH_AOI
        or abs(state["acceleration"]) >= ACCEL_THRESHOLD
    ):
        return 0.05

    if aoi > LOW_AOI or state["speed"] >= HIGH_SPEED:
        return 0.10

    return 0.50


def percentile(values, p):
    """Calculate a percentile using linear interpolation."""
    if not values:
        return ""

    ordered = sorted(values)
    index = (len(ordered) - 1) * p
    lower = int(index)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = index - lower

    return (
        ordered[lower] * (1 - fraction)
        + ordered[upper] * fraction
    )


def run_strategy(strategy, interval=None):
    if strategy == "periodic" and (interval is None or interval <= 0):
        raise ValueError("Periodic strategy requires a positive interval, e.g. 0.05")

    twin = DigitalTwin()

    channel = CommunicationChannel(
        delay_s=CHANNEL_DELAY,
        loss_probability=PACKET_LOSS,
        seed=42,
    )

    next_update = {}
    last_sent_state = {}
    last_sent_timestamp = {}
    rows = []

    config_value = os.environ.get("SUMO_CONFIG")
    if config_value:
        config_path = Path(config_value).expanduser()
        if not config_path.is_absolute():
            # Prefer the path as supplied if it exists; otherwise resolve from project root.
            if not config_path.exists():
                config_path = PROJECT_ROOT / config_path
    else:
        config_path = PROJECT_ROOT / "sumo" / "simulation.sumocfg"

    if not config_path.is_file():
        raise FileNotFoundError(
            f"SUMO configuration not found: {config_path}\n"
            "Set SUMO_CONFIG to a valid .sumocfg file."
        )

    traci.start([
        "sumo",
        "-c", str(config_path),
        "--no-step-log",
        "--duration-log.disable",
    ])

    try:
        while traci.simulation.getTime() < DURATION - 1e-9:
            traci.simulationStep()
            t = traci.simulation.getTime()

            # Deliver packets that have reached the RSU.
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

                should_send = False
                selected_interval = None

                if strategy == "periodic":
                    selected_interval = interval

                    should_send = (
                        t + 1e-9 >= next_update[vid]
                    )

                elif strategy == "event-triggered":
                    previous = last_sent_state.get(vid)
                    last_sent_time = last_sent_timestamp.get(vid)

                    # Always send the first state for a vehicle.
                    if previous is None:
                        should_send = True
                    else:
                        distance = math.hypot(
                            actual["x"] - previous["x"],
                            actual["y"] - previous["y"],
                        )

                        event_occurred = (
                            distance >= POSITION_THRESHOLD
                            or abs(
                                actual["speed"] - previous["speed"]
                            ) >= SPEED_THRESHOLD
                            or angle_difference(
                                actual["heading"],
                                previous["heading"],
                            ) >= HEADING_THRESHOLD
                            or abs(
                                actual["acceleration"]
                                - previous["acceleration"]
                            ) >= ACCEL_THRESHOLD
                        )

                        periodic_fallback = (
                            last_sent_time is None
                            or t - last_sent_time
                            >= EVENT_MAX_INTERVAL - 1e-9
                        )

                        should_send = (
                            event_occurred or periodic_fallback
                        )

                elif strategy == "adaptive":
                    aoi = twin.get_aoi(vid, t)

                    selected_interval = choose_adaptive_interval(
                        aoi, actual
                    )

                    should_send = (
                        t + 1e-9 >= next_update[vid]
                    )

                else:
                    raise ValueError(
                        f"Unknown synchronization strategy: {strategy}"
                    )

                if should_send:
                    channel.transmit(vid, actual, t)

                    # Record attempted transmissions. A packet can
                    # still be dropped by the simulated channel.
                    last_sent_state[vid] = actual.copy()
                    last_sent_timestamp[vid] = t

                    if strategy == "periodic":
                        next_update[vid] += interval

                        if next_update[vid] <= t:
                            next_update[vid] = t + interval

                    elif strategy == "adaptive":
                        next_update[vid] = (
                            t + selected_interval
                        )

                    else:
                        next_update[vid] = (
                            t + EVENT_MAX_INTERVAL
                        )

                stored = twin.get_state(vid)
                aoi = twin.get_aoi(vid, t)

                rows.append({
                    "time": t,
                    "vehicle_id": vid,
                    "aoi": aoi,
                    "position_error": (
                        position_error(actual, stored)
                        if stored is not None else None
                    ),
                    "speed_error": (
                        speed_error(actual, stored)
                        if stored is not None else None
                    ),
                    "heading_error": (
                        heading_error(actual, stored)
                        if stored is not None else None
                    ),
                })

        # Record the actual end time and process packets still in flight.
        simulation_end_time = traci.simulation.getTime()
        print(f"Simulation stopped at t={simulation_end_time:.2f}s")

        for packet in channel.receive_ready(
            simulation_end_time + CHANNEL_DELAY
        ):
            twin.receive_update(
                packet["vehicle_id"],
                packet["state"],
                packet["generation_time"],
                packet["arrival_time"],
            )

    finally:
        traci.close()

    # Measure samples for which the twin has received a state.
    valid = [
        row for row in rows
        if row["aoi"] is not None
    ]

    aoi_values = [
        float(row["aoi"]) for row in valid
    ]

    position_values = [
        float(row["position_error"])
        for row in valid
        if row["position_error"] is not None
    ]

    speed_values = [
        float(row["speed_error"])
        for row in valid
        if row["speed_error"] is not None
    ]

    heading_values = [
        float(row["heading_error"])
        for row in valid
        if row["heading_error"] is not None
    ]

    attempts = channel.attempts
    delivered = channel.delivered

    summary = {
        "strategy": strategy,
        "interval_ms": (
            int(interval * 1000) if interval else ""
        ),
        "delay_ms": int(CHANNEL_DELAY * 1000),
        "configured_loss_percent": PACKET_LOSS * 100,
        "samples_with_twin": len(valid),
        "transmission_attempts": attempts,
        "delivered_packets": delivered,
        "dropped_packets": channel.dropped,
        "pdr_percent": (
            100 * delivered / attempts
            if attempts else 0.0
        ),
        "average_aoi_s": (
            sum(aoi_values) / len(aoi_values)
            if aoi_values else ""
        ),
        "p95_aoi_s": percentile(aoi_values, 0.95),
        "maximum_aoi_s": (
            max(aoi_values) if aoi_values else ""
        ),
        "average_position_error_m": (
            sum(position_values) / len(position_values)
            if position_values else ""
        ),
        "maximum_position_error_m": (
            max(position_values)
            if position_values else ""
        ),
        "average_speed_error_mps": (
            sum(speed_values) / len(speed_values)
            if speed_values else ""
        ),
        "average_heading_error_deg": (
            sum(heading_values) / len(heading_values)
            if heading_values else ""
        ),
        "overhead_bytes_per_sec": (
            attempts * PACKET_SIZE_BYTES / simulation_end_time
            if simulation_end_time > 0 else 0.0
        ),
    }

    print(summary)
    return summary


def main():
    configurations = [
        ("periodic", 0.05),
        ("periodic", 0.10),
        ("periodic", 0.50),
        ("event-triggered", None),
        ("adaptive", None),
    ]

    # Optional arguments:
    # python src/strategy_channel_experiment.py periodic 0.05
    if len(sys.argv) >= 2:
        strategy = sys.argv[1]

        interval = (
            float(sys.argv[2])
            if len(sys.argv) >= 3 and sys.argv[2]
            else None
        )

        configurations = [(strategy, interval)]

    summaries = []

    for strategy, interval in configurations:
        summaries.append(
            run_strategy(strategy, interval)
        )

    os.makedirs("results", exist_ok=True)

    output_value = os.environ.get(
        "RESULTS_CSV",
        "results/strategy_channel_summary.csv",
    )
    output_path = Path(output_value).expanduser()
    if not output_path.is_absolute():
        if not output_path.parent.exists() and not (PROJECT_ROOT / output_path.parent).exists():
            output_path = PROJECT_ROOT / output_path
        elif not output_path.is_absolute():
            # Keep an existing path relative to the current working directory.
            output_path = output_path.resolve()

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", newline="") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=summaries[0].keys(),
        )

        writer.writeheader()
        writer.writerows(summaries)

    print(f"\nSaved {output_path}")


if __name__ == "__main__":
    main()
