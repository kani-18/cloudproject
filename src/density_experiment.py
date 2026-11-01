
import os
import sys
import csv
import subprocess
import xml.etree.ElementTree as ET

DENSITIES = [5, 10, 20, 50, 100]

CONFIGURATIONS = [
    ("periodic", "0.05"),
    ("periodic", "0.10"),
    ("periodic", "0.50"),
    ("event-triggered", ""),
    ("adaptive", ""),
]

NETWORK = "sumo/network.net.xml"
OUTPUT = "results/density_summary.csv"
RUNNER = "src/strategy_channel_experiment.py"
RANDOM_TRIPS = "/usr/share/sumo/tools/randomTrips.py"


def count_elements(filename, tag):
    root = ET.parse(filename).getroot()
    return sum(1 for element in root.iter(tag))


def generate_scenario(density):
    trips = f"sumo/density_{density}.trips.xml"
    routes = f"sumo/density_{density}.rou.xml"
    config = f"sumo/density_{density}.sumocfg"

    # Generate trips for the new network.
    subprocess.run([
        sys.executable, RANDOM_TRIPS,
        "--net-file", NETWORK,
        "--output-trip-file", trips,
        "--begin", "0",
        "--end", "100",
        "--period", str(100.0 / density),
        "--seed", "42",
    ], check=True)

    # Convert trips to valid routes. Do not silently ignore errors.
    subprocess.run([
        "duarouter",
        "--net-file", NETWORK,
        "--route-files", trips,
        "--output-file", routes,
        "--ignore-errors", "false",
        "--no-warnings", "false",
        "--no-step-log", "true",
    ], check=True)

    trip_count = count_elements(trips, "trip")
    route_count = count_elements(routes, "vehicle")

    print(
        f"Demand {density}: {trip_count} trips, "
        f"{route_count} valid routes"
    )

    if route_count != trip_count:
        raise RuntimeError(
            f"Demand {density}: only {route_count}/{trip_count} "
            "trips received valid routes. Fix routing before simulation."
        )

    # Create a configuration referencing the newly generated files.
    root = ET.Element("configuration")
    inputs = ET.SubElement(root, "input")
    ET.SubElement(inputs, "net-file", value="network.net.xml")
    ET.SubElement(inputs, "route-files", value=os.path.basename(routes))

    time = ET.SubElement(root, "time")
    ET.SubElement(time, "begin", value="0")
    ET.SubElement(time, "end", value="120")
    ET.SubElement(time, "step-length", value="0.05")

    ET.ElementTree(root).write(config, encoding="UTF-8",
                               xml_declaration=True)


def main():
    os.makedirs("results", exist_ok=True)

    # Validate the network's connected components first.
    subprocess.run([
        sys.executable,
        "/usr/share/sumo/tools/net/netcheck.py",
        NETWORK,
    ], check=True)

    for density in DENSITIES:
        generate_scenario(density)

    all_rows = []

    for density in DENSITIES:
        config = f"sumo/density_{density}.sumocfg"

        for strategy, interval in CONFIGURATIONS:
            print(
                f"\nRunning demand={density}, "
                f"strategy={strategy}, interval={interval or 'N/A'}",
                flush=True,
            )

            env = os.environ.copy()
            env["SUMO_CONFIG"] = config
            env["RESULTS_CSV"] = "results/_density_single_run.csv"

            command = [sys.executable, RUNNER, strategy]
            if interval:
                command.append(interval)

            subprocess.run(command, env=env, check=True)

            with open(env["RESULTS_CSV"], newline="") as file:
                rows = list(csv.DictReader(file))

            if len(rows) != 1:
                raise RuntimeError(
                    f"Expected one result row, got {len(rows)}"
                )

            row = rows[0]
            row["density"] = density
            all_rows.append(row)

    fields = ["density"] + [
        key for key in all_rows[0] if key != "density"
    ]

    with open(OUTPUT, "w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(all_rows)

    print(f"\nAll experiments completed. Saved {OUTPUT}")


if __name__ == "__main__":
    main()

