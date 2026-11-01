
class DigitalTwin:
    """Stores the freshest successfully received state for each vehicle."""

    def __init__(self):
        self.vehicles = {}

    def receive_update(
        self,
        vehicle_id,
        state,
        generation_time,
        reception_time,
    ):
        existing = self.vehicles.get(vehicle_id)

        # Reject packets containing older or duplicate generated states.
        if existing is not None:
            if generation_time <= existing["generation_time"]:
                return False

        self.vehicles[vehicle_id] = {
            "state": state.copy(),
            "generation_time": generation_time,
            "reception_time": reception_time,
        }

        return True

    def get_aoi(self, vehicle_id, current_time):
        record = self.vehicles.get(vehicle_id)

        if record is None:
            return None

        return max(
            0.0,
            current_time - record["generation_time"],
        )

    def get_state(self, vehicle_id):
        record = self.vehicles.get(vehicle_id)

        if record is None:
            return None

        return record["state"]

    def get_reception_time(self, vehicle_id):
        record = self.vehicles.get(vehicle_id)

        if record is None:
            return None

        return record["reception_time"]
