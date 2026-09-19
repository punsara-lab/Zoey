"""
ZOEY — memory.py
A plain JSON file, not a database — always inspectable, always editable
by hand if something looks wrong.
"""

import json
import os

MEMORY_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "zoey_memory.json")

MAX_LOG_ENTRIES = 40  # rolling window so the file doesn't grow forever

_DEFAULT_MEMORY = {
    "user_name": "Punsara",
    "facts": [],
    "preferences": [],
    "conversation_log": [],
}


def load_memory() -> dict:
    if not os.path.exists(MEMORY_PATH):
        save_memory(_DEFAULT_MEMORY)
        return dict(_DEFAULT_MEMORY)
    try:
        with open(MEMORY_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        # Corrupted file — don't crash the whole app, start fresh but
        # don't silently overwrite what might be recoverable by hand.
        backup_path = MEMORY_PATH + ".broken"
        if os.path.exists(MEMORY_PATH):
            os.replace(MEMORY_PATH, backup_path)
        data = dict(_DEFAULT_MEMORY)
        save_memory(data)
    # Make sure all expected keys exist even if the file is old/partial
    for key, default in _DEFAULT_MEMORY.items():
        data.setdefault(key, default)
    return data


def save_memory(memory: dict) -> None:
    with open(MEMORY_PATH, "w", encoding="utf-8") as f:
        json.dump(memory, f, indent=2, ensure_ascii=False)


def add_fact(memory: dict, fact: str) -> None:
    if fact and fact not in memory["facts"]:
        memory["facts"].append(fact)
        save_memory(memory)


def add_preference(memory: dict, preference: str) -> None:
    if preference and preference not in memory["preferences"]:
        memory["preferences"].append(preference)
        save_memory(memory)


def log_exchange(memory: dict, user_text: str, zoey_text: str) -> None:
    memory["conversation_log"].append({"user": user_text, "zoey": zoey_text})
    memory["conversation_log"] = memory["conversation_log"][-MAX_LOG_ENTRIES:]
    save_memory(memory)


def build_context_block(memory: dict) -> str:
    """Turns stored memory into text injected into the system prompt
    every session, so ZOEY has continuity without a database."""
    lines = []

    if memory["facts"]:
        lines.append("Known facts about the user:")
        lines.extend(f"- {f}" for f in memory["facts"])

    if memory["preferences"]:
        lines.append("Known preferences:")
        lines.extend(f"- {p}" for p in memory["preferences"])

    if memory["conversation_log"]:
        lines.append("Recent conversation (most recent last):")
        for entry in memory["conversation_log"][-10:]:
            lines.append(f"User: {entry['user']}")
            lines.append(f"Zoey: {entry['zoey']}")

    if not lines:
        return "No prior memory yet — this is a fresh start with this user."

    return "\n".join(lines)
