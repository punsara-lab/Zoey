"""Small persistent NEAT-style topology experiment for ZOEY.

This is not a replacement for Gemma. It is an inspectable concept graph that
can grow from interaction outcomes and later be used as a routing signal.
"""

import hashlib
import json
import os
import random
import time


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATE_PATH = os.path.join(BASE_DIR, "brain", "growing_brain.json")


class GrowingBrain:
    def __init__(self, path: str = STATE_PATH):
        self.path = path
        self.state = self._load()

    def _load(self) -> dict:
        try:
            with open(self.path, "r", encoding="utf-8") as handle:
                state = json.load(handle)
            if isinstance(state, dict) and state.get("neurons") and state.get("connections") is not None:
                return state
        except (OSError, ValueError, TypeError):
            pass
        return {
            "version": 1,
            "generation": 0,
            "neurons": [
                {"id": "input", "kind": "input", "label": "interaction"},
                {"id": "output", "kind": "output", "label": "response"},
            ],
            "connections": [],
            "experiences": 0,
            "last_reward": None,
        }

    def _save(self) -> None:
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        temp_path = self.path + ".tmp"
        with open(temp_path, "w", encoding="utf-8") as handle:
            json.dump(self.state, handle, ensure_ascii=False, indent=2)
        os.replace(temp_path, self.path)

    @staticmethod
    def _feature_id(feature: str) -> str:
        digest = hashlib.sha1(feature.strip().lower().encode("utf-8")).hexdigest()[:10]
        return f"feature_{digest}"

    def _ensure_neuron(self, neuron_id: str, kind: str, label: str) -> bool:
        if any(node["id"] == neuron_id for node in self.state["neurons"]):
            return False
        self.state["neurons"].append({"id": neuron_id, "kind": kind, "label": label})
        return True

    def _ensure_connection(self, source: str, target: str, weight: float) -> bool:
        for connection in self.state["connections"]:
            if connection["source"] == source and connection["target"] == target:
                connection["weight"] = round(float(connection["weight"]) + weight, 4)
                return False
        self.state["connections"].append(
            {"source": source, "target": target, "weight": round(weight, 4), "enabled": True}
        )
        return True

    def experience(self, features: list[str], reward: float, confused: bool = False) -> dict:
        """Learn from an interaction and grow only when novelty/error warrants it."""
        clean_features = sorted({str(item).strip().lower() for item in features if str(item).strip()})[:8]
        reward = max(-1.0, min(1.0, float(reward)))
        grew = []

        for feature in clean_features:
            neuron_id = self._feature_id(feature)
            if self._ensure_neuron(neuron_id, "concept", feature):
                grew.append(neuron_id)
            self._ensure_connection("input", neuron_id, 0.1 if reward >= 0 else -0.1)

            if confused or reward < 0.35:
                concept_id = f"path_{self._feature_id(feature)[8:]}"
                if self._ensure_neuron(concept_id, "hidden", f"pathway:{feature}"):
                    grew.append(concept_id)
                self._ensure_connection(neuron_id, concept_id, 0.2)
                self._ensure_connection(concept_id, "output", 0.2)
            else:
                self._ensure_connection(neuron_id, "output", 0.1)

        self.state["generation"] += 1
        self.state["experiences"] += 1
        self.state["last_reward"] = round(reward, 3)
        self.state["last_updated"] = time.time()
        self._save()
        return {
            "generation": self.state["generation"],
            "experiences": self.state["experiences"],
            "neurons": len(self.state["neurons"]),
            "connections": len(self.state["connections"]),
            "grew": grew,
        }

    def summary(self) -> dict:
        return {
            "version": self.state["version"],
            "generation": self.state["generation"],
            "experiences": self.state["experiences"],
            "neurons": self.state["neurons"],
            "connections": self.state["connections"],
            "last_reward": self.state["last_reward"],
        }


_DEFAULT_BRAIN = GrowingBrain()


def experience(features: list[str], reward: float, confused: bool = False) -> dict:
    return _DEFAULT_BRAIN.experience(features, reward, confused)


def summary() -> dict:
    return _DEFAULT_BRAIN.summary()
