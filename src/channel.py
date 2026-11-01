
import random
import heapq
from itertools import count


class CommunicationChannel:
    """Simple simulated channel with delay and independent packet loss."""

    def __init__(
        self,
        delay_s=0.05,
        loss_probability=0.05,
        seed=42,
    ):
        if delay_s < 0:
            raise ValueError("delay_s must be non-negative")

        if not 0.0 <= loss_probability <= 1.0:
            raise ValueError("loss_probability must be between 0 and 1")

        self.delay_s = delay_s
        self.loss_probability = loss_probability
        self.random = random.Random(seed)
        self.pending = []
        self.sequence = count()

        self.attempts = 0
        self.dropped = 0
        self.delivered = 0

    def transmit(self, vehicle_id, state, generation_time):
        """Attempt transmission; schedule successful packets for later delivery."""
        self.attempts += 1

        if self.random.random() < self.loss_probability:
            self.dropped += 1
            return False

        arrival_time = generation_time + self.delay_s

        heapq.heappush(
            self.pending,
            (
                arrival_time,
                next(self.sequence),
                vehicle_id,
                state.copy(),
                generation_time,
            ),
        )
        return True

    def receive_ready(self, current_time):
        """Return packets whose simulated arrival time has been reached."""
        ready = []

        while self.pending and self.pending[0][0] <= current_time + 1e-9:
            arrival, _, vehicle_id, state, generation_time = (
                heapq.heappop(self.pending)
            )

            ready.append({
                "vehicle_id": vehicle_id,
                "state": state,
                "generation_time": generation_time,
                "arrival_time": arrival,
            })

            self.delivered += 1

        return ready
