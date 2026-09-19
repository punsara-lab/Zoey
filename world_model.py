"""Tiny from-scratch world model using only local next-sensation prediction.

There are no labels, pretrained weights, Gemma calls, or network requests.
The model learns a numeric sensation transition from observations supplied by
local tools. Prediction error becomes surprise and curiosity.
"""

import json
import math
import os
import random
import time


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATE_PATH = os.path.join(BASE_DIR, "brain", "world_model.json")


class WorldModel:
    def __init__(self, dimensions: int = 4, path: str = STATE_PATH, seed: int | None = None):
        self.dimensions = max(1, int(dimensions))
        self.path = path
        self.random = random.Random(seed)
        self.state = self._load()

    def _load(self) -> dict:
        try:
            with open(self.path, "r", encoding="utf-8") as handle:
                state = json.load(handle)
            if state.get("dimensions") == self.dimensions:
                return state
        except (OSError, ValueError, TypeError):
            pass
        feature_count = self.dimensions * 2 + 1
        return {
            "version": 1,
            "dimensions": self.dimensions,
            "learning_rate": 0.08,
            "weights": [
                [self.random.uniform(-0.1, 0.1) for _ in range(feature_count)]
                for _ in range(self.dimensions)
            ],
            "previous": None,
            "observations": 0,
            "surprise_total": 0.0,
            "last_surprise": None,
            "last_updated": None,
        }

    def _save(self) -> None:
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        temporary = self.path + ".tmp"
        with open(temporary, "w", encoding="utf-8") as handle:
            json.dump(self.state, handle, indent=2)
        os.replace(temporary, self.path)

    def _vector(self, sensation: list[float], action: list[float]) -> list[float]:
        values = [float(value) for value in (sensation + action)]
        values = (values + [0.0] * (self.dimensions * 2))[: self.dimensions * 2]
        return values + [1.0]

    def _predict_vector(self, features: list[float]) -> list[float]:
        return [sum(weight * value for weight, value in zip(row, features)) for row in self.state["weights"]]

    def observe(self, sensation: list[float], action: list[float] | None = None) -> dict:
        current = [float(value) for value in sensation[: self.dimensions]]
        current = (current + [0.0] * self.dimensions)[: self.dimensions]
        action_values = [float(value) for value in (action or [])[: self.dimensions]]
        action_values = (action_values + [0.0] * self.dimensions)[: self.dimensions]
        prediction = None
        surprise = None

        if self.state["previous"] is not None:
            previous = self.state["previous"]
            features = self._vector(previous["sensation"], previous["action"])
            prediction = self._predict_vector(features)
            errors = [actual - predicted for actual, predicted in zip(current, prediction)]
            surprise = math.sqrt(sum(error * error for error in errors) / self.dimensions)
            learning_rate = float(self.state["learning_rate"])
            for row, error in zip(self.state["weights"], errors):
                for index, value in enumerate(features):
                    row[index] += learning_rate * error * value
            self.state["surprise_total"] += surprise
            self.state["last_surprise"] = round(surprise, 6)

        self.state["previous"] = {"sensation": current, "action": action_values}
        self.state["observations"] += 1
        self.state["last_updated"] = time.time()
        self._save()
        return {
            "observations": self.state["observations"],
            "prediction": prediction,
            "surprise": surprise,
            "curiosity": round(surprise or 0.0, 6),
            "habituated": surprise is not None and surprise < 0.05,
        }

    def summary(self) -> dict:
        return {
            "dimensions": self.dimensions,
            "observations": self.state["observations"],
            "average_surprise": round(
                self.state["surprise_total"] / max(1, self.state["observations"] - 1), 6
            ),
            "last_surprise": self.state["last_surprise"],
            "learning_source": "local next-sensation prediction only",
        }


_DEFAULT_MODEL = WorldModel()


def observe(sensation: list[float], action: list[float] | None = None) -> dict:
    return _DEFAULT_MODEL.observe(sensation, action)


def summary() -> dict:
    return _DEFAULT_MODEL.summary()
