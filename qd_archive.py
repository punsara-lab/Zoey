"""Bounded quality-diversity archive of explainable strategy genomes."""

import json
import os
import random
import time
import uuid


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATE_PATH = os.path.join(BASE_DIR, "brain", "qd_archive.json")
MAX_ARCHIVE = 1000


class QualityDiversityArchive:
    def __init__(self, path: str = STATE_PATH, seed: int | None = None):
        self.path = path
        self.random = random.Random(seed)
        self.state = self._load()

    def _load(self) -> dict:
        try:
            with open(self.path, "r", encoding="utf-8") as handle:
                state = json.load(handle)
            if isinstance(state, dict) and isinstance(state.get("members"), list):
                return state
        except (OSError, ValueError, TypeError):
            pass
        return {"version": 1, "members": [], "evaluations": 0, "last_updated": None}

    def _save(self) -> None:
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        temporary = self.path + ".tmp"
        with open(temporary, "w", encoding="utf-8") as handle:
            json.dump(self.state, handle, indent=2)
        os.replace(temporary, self.path)

    def _new_member(self, descriptor: str) -> dict:
        return {
            "id": uuid.uuid4().hex[:10],
            "descriptor": descriptor or "balanced",
            "strategy": {
                "conciseness": self.random.random(),
                "caution": self.random.random(),
                "exploration": self.random.random(),
            },
            "score": 0.0,
            "evaluations": 0,
            "regrets": 0,
        }

    def select(self, descriptor: str = "") -> dict:
        matches = [member for member in self.state["members"] if not descriptor or member["descriptor"] == descriptor]
        if not matches:
            member = self._new_member(descriptor)
            self.state["members"].append(member)
            self._save()
            return member
        return max(matches, key=lambda item: item["score"])

    def evaluate(self, member_id: str, score: float) -> dict:
        score = max(-1.0, min(1.0, float(score)))
        member = next((item for item in self.state["members"] if item["id"] == member_id), None)
        if member is None:
            return {"status": "missing", "member_id": member_id}
        member["score"] = round((member["score"] * member["evaluations"] + score) / (member["evaluations"] + 1), 4)
        member["evaluations"] += 1
        if score < 0:
            member["regrets"] += 1
        self.state["evaluations"] += 1
        self.state["last_updated"] = time.time()
        self._save()
        return member

    def mutate(self, parent_id: str) -> dict:
        parent = next((item for item in self.state["members"] if item["id"] == parent_id), None)
        if parent is None:
            return {"status": "missing", "member_id": parent_id}
        child = json.loads(json.dumps(parent))
        child["id"] = uuid.uuid4().hex[:10]
        child["score"] = 0.0
        child["evaluations"] = 0
        for key in child["strategy"]:
            child["strategy"][key] = round(max(0.0, min(1.0, child["strategy"][key] + self.random.uniform(-0.1, 0.1))), 4)
        self.state["members"].append(child)
        self.state["members"] = sorted(self.state["members"], key=lambda item: item["score"], reverse=True)[:MAX_ARCHIVE]
        self._save()
        return child

    def summary(self) -> dict:
        return {
            "archive_size": len(self.state["members"]),
            "evaluations": self.state["evaluations"],
            "descriptors": sorted({item["descriptor"] for item in self.state["members"]}),
            "top_members": sorted(self.state["members"], key=lambda item: item["score"], reverse=True)[:5],
        }


_DEFAULT_ARCHIVE = QualityDiversityArchive()


def select(descriptor: str = "") -> dict:
    return _DEFAULT_ARCHIVE.select(descriptor)


def evaluate(member_id: str, score: float) -> dict:
    return _DEFAULT_ARCHIVE.evaluate(member_id, score)


def mutate(parent_id: str) -> dict:
    return _DEFAULT_ARCHIVE.mutate(parent_id)


def summary() -> dict:
    return _DEFAULT_ARCHIVE.summary()
