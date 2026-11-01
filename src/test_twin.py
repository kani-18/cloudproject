import os
import sys
import csv
import traci

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from rsu_twin import DigitalTwin
from metrics import position_error, speed_error, heading_error

twin = DigitalTwin()
results = []

os.environ["SUMO_HOME"] = "/usr/share/sumo"

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

            # Ideal channel: every observed state is delivered immediately.
            twin.receive_update(vid, actual, t, t)

            stored = twin.get_state(vid)
            aoi = twin.get_aoi(vid, t)

            results.append({
                "time": t,
                "vehicle_id": vid,
                "aoi": aoi,
                "position_error": position_error(actual, stored),
                "speed_error": speed_error(actual, stored),
                "heading_error": heading_error(actual, stored),
            })

finally:
    traci.close()

with open("results/twin_test.csv", "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=[
        "time", "vehicle_id", "aoi",
        "position_error", "speed_error", "heading_error"
    ])
    writer.writeheader()
    writer.writerows(results)

print("Digital Twin test completed.")
print("Saved results to results/twin_test.csv")
print("Recorded samples:", len(results))
