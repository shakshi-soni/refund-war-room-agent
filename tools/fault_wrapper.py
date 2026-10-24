
import random


class FaultWrapper:
    def __init__(self, failure_rate=0.15, seed=7):
        if not 0 <= failure_rate <= 1:
            raise ValueError("failure_rate must be between 0 and 1")

        self.failure_rate = failure_rate
        self.rng = random.Random(seed)

    def call(self, tool, *args, **kwargs):
        if self.rng.random() < self.failure_rate:
            outcome = self.rng.choice(["timeout", "empty", "error"])

            if outcome == "timeout":
                return {"ok": False, "error": "Tool timed out"}

            if outcome == "empty":
                return {"ok": True, "results": [], "fault": "empty"}

            return {"ok": False, "error": "Simulated tool failure"}

        try:
            return tool(*args, **kwargs)
        except Exception as exc:
            return {"ok": False, "error": str(exc)}
