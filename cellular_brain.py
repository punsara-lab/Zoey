"""A small learning cellular automaton for ZOEY.

Cells update from local neighborhoods. Successful transitions receive more
weight; failed transitions are weakened. The grid is persistent and has no
central controller.
"""

import json
import os
import random
import time
from collections import defaultdict


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATE_PATH = os.path.join(BASE_DIR, "brain", "cellular_brain.json")


class CellularBrain:
    def __init__(self, width: int = 8, height: int = 8, path: str = STATE_PATH):
        self.width = max(3, int(width))
        self.height = max(3, int(height))
        self.path = path
        self.state = self._load()

    def _load(self) -> dict:
        try:
            with open(self.path, "r", encoding="utf-8") as handle:
                state = json.load(handle)
            if state.get("width") == self.width and state.get("height") == self.height:
                return state
        except (OSError, ValueError, TypeError):
            pass
        return {
            "version": 1,
            "width": self.width,
            "height": self.height,
            "generation": 0,
            "grid": [[0 for _ in range(self.width)] for _ in range(self.height)],
            "rules": {},
            "experiences": 0,
            "last_reward": None,
        }

    def _save(self) -> None:
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        temporary = self.path + ".tmp"
        with open(temporary, "w", encoding="utf-8") as handle:
            json.dump(self.state, handle, indent=2)
        os.replace(temporary, self.path)

    def _pattern(self, row: int, col: int) -> str:
        grid = self.state["grid"]
        bits = []
        for row_delta, col_delta in ((-1, 0), (0, -1), (0, 0), (0, 1), (1, 0)):
            r = (row + row_delta) % self.height
            c = (col + col_delta) % self.width
            bits.append(str(grid[r][c]))
        return "".join(bits)

    def step(self, reward: float = 0.0) -> dict:
        reward = max(-1.0, min(1.0, float(reward)))
        next_grid = [[0 for _ in range(self.width)] for _ in range(self.height)]
        for row in range(self.height):
            for col in range(self.width):
                pattern = self._pattern(row, col)
                options = self.state["rules"].setdefault(pattern, {"0": 1.0, "1": 1.0})
                if reward < 0:
                    options["0"] += 0.15
                elif reward > 0:
                    options["1"] += 0.15
                total = options["0"] + options["1"]
                next_grid[row][col] = 1 if random.random() < options["1"] / total else 0
        self.state["grid"] = next_grid
        self.state["generation"] += 1
        self.state["experiences"] += 1
        self.state["last_reward"] = round(reward, 3)
        self.state["last_updated"] = time.time()
        self._save()
        return self.summary()

    def experience(self, reward: float) -> dict:
        return self.step(reward=reward)

    def summary(self) -> dict:
        active = sum(sum(row) for row in self.state["grid"])
        return {
            "generation": self.state["generation"],
            "experiences": self.state["experiences"],
            "active_cells": active,
            "learned_rules": len(self.state["rules"]),
            "last_reward": self.state["last_reward"],
            "grid": self.state["grid"],
        }


_DEFAULT_BRAIN = CellularBrain()


def experience(reward: float) -> dict:
    return _DEFAULT_BRAIN.experience(reward)


def summary() -> dict:
    return _DEFAULT_BRAIN.summary()
