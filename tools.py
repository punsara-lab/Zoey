"""
ZOEY — tools.py
Thin aggregator over the skills/ package. engine.py and api.py only
ever import this file — they don't know or care how many skills exist.
Adding a new skill (like a future KDE Connect integration for reaching
other devices) means adding a file under skills/, not touching this one.
"""

import skills

TOOL_DEFINITIONS = skills.TOOL_DEFINITIONS

_stats = {"tool_calls": 0}
_route_logger = None


def set_memory(memory: dict) -> None:
    skills.set_memory_all(memory)


def get_stats() -> dict:
    return dict(_stats)


def set_route_logger(logger) -> None:
    """Set a callback receiving (skill, tool, phase, detail) route events."""
    global _route_logger
    _route_logger = logger


def execute_tool(name: str, arguments: dict) -> str:
    _stats["tool_calls"] += 1
    skill = skills.skill_for_tool(name)
    if _route_logger:
        _route_logger(skill, name, "start", arguments)
    try:
        result = skills.execute(name, arguments)
    except Exception as exc:
        if _route_logger:
            _route_logger(skill, name, "error", str(exc))
        raise
    if _route_logger:
        _route_logger(skill, name, "done", result)
    return result
