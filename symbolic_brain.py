"""Explainable production rules learned from local experience."""

import json
import os
import time


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATE_PATH = os.path.join(BASE_DIR, "brain", "symbolic_rules.json")


class SymbolicBrain:
    def __init__(self, path: str = STATE_PATH):
        self.path = path
        self.state = self._load()

    def _load(self) -> dict:
        try:
            with open(self.path, "r", encoding="utf-8") as handle:
                state = json.load(handle)
            if isinstance(state, dict) and isinstance(state.get("rules"), list):
                return state
        except (OSError, ValueError, TypeError):
            pass
        return {"version": 1, "rules": [], "experiences": 0, "last_updated": None}

    def _save(self) -> None:
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        temporary = self.path + ".tmp"
        with open(temporary, "w", encoding="utf-8") as handle:
            json.dump(self.state, handle, indent=2)
        os.replace(temporary, self.path)

    def learn(self, conditions: list[str], action: str, reward: float) -> dict:
        conditions = sorted({str(item).strip().lower() for item in conditions if str(item).strip()})[:8]
        action = str(action).strip().lower()
        reward = max(-1.0, min(1.0, float(reward)))
        if not conditions or not action:
            return {"status": "ignored", "reason": "conditions and action are required"}
        match = next(
            (rule for rule in self.state["rules"] if rule["conditions"] == conditions and rule["action"] == action),
            None,
        )
        if match is None:
            match = {
                "conditions": conditions,
                "action": action,
                "strength": 0.2 if reward >= 0 else -0.2,
                "uses": 0,
                "regrets": 0,
                "last_reward": reward,
            }
            self.state["rules"].append(match)
        match["strength"] = round(max(-1.0, min(1.0, match["strength"] + reward * 0.2)), 4)
        match["uses"] += 1
        match["last_reward"] = reward
        if reward < 0:
            match["regrets"] += 1
        self.state["experiences"] += 1
        self.state["last_updated"] = time.time()
        self._save()
        return {"status": "learned", "rule": match}

    def fire(self, features: list[str]) -> dict | None:
        feature_set = {str(item).strip().lower() for item in features}
        candidates = [
            rule for rule in self.state["rules"]
            if rule["strength"] > 0 and set(rule["conditions"]).issubset(feature_set)
        ]
        if not candidates:
            return None
        rule = max(candidates, key=lambda item: (item["strength"], len(item["conditions"])))
        return {"action": rule["action"], "rule": rule, "explanation": self.explain(rule)}

    @staticmethod
    def explain(rule: dict) -> str:
        conditions = " AND ".join(rule["conditions"])
        return f"IF {conditions} THEN {rule['action']} (strength={rule['strength']})"

    def summary(self) -> dict:
        return {
            "rules": self.state["rules"],
            "rule_count": len(self.state["rules"]),
            "experiences": self.state["experiences"],
        }


_DEFAULT_BRAIN = SymbolicBrain()


def learn(conditions: list[str], action: str, reward: float) -> dict:
    return _DEFAULT_BRAIN.learn(conditions, action, reward)


def fire(features: list[str]) -> dict | None:
    return _DEFAULT_BRAIN.fire(features)


def summary() -> dict:
    return _DEFAULT_BRAIN.summary()
