
import os
import traci

os.environ["SUMO_HOME"] = "/usr/share/sumo"

traci.start([
    "sumo",
    "-c", "sumo/simulation.sumocfg",
    "--no-step-log",
    "--duration-log.disable"
])

try:
    watched_vehicle = None

    for _ in range(2000):
        traci.simulationStep()

        vehicle_ids = traci.vehicle.getIDList()

        if watched_vehicle is None and vehicle_ids:
            watched_vehicle = vehicle_ids[0]
            print("Watching vehicle:", watched_vehicle)

        if watched_vehicle in vehicle_ids:
            print(
                f"t={traci.simulation.getTime():.2f}s, "
                f"position={traci.vehicle.getPosition(watched_vehicle)}, "
                f"speed={traci.vehicle.getSpeed(watched_vehicle):.2f} m/s"
            )

        if traci.simulation.getMinExpectedNumber() == 0:
            break

finally:
    traci.close()

