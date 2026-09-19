import json
import os


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")


def _read_json(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_user_data() -> dict:
    return _read_json(os.path.join(DATA_DIR, "user.json"))


def get_zoey_data() -> dict:
    return _read_json(os.path.join(DATA_DIR, "zoey.json"))


def get_user_value(key: str):
    data = get_user_data()
    if not key:
        return data
    parts = [p for p in str(key).split(".") if p]
    cur = data
    for p in parts:
        if isinstance(cur, dict) and p in cur:
            cur = cur[p]
        else:
            return None
    return cur
