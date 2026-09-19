"""
ZOEY — skills/__init__.py

This is the extension point for the whole project. Each file in this
folder is one "skill": a small module that exposes TOOL_DEFINITIONS
(OpenAI-style schemas) and DISPATCH (name -> function). This loader
auto-discovers every skill module and merges them — tools.py never
needs to know how many skills exist or what they're called.

To add a new skill later (e.g. a KDE Connect integration for
controlling/reaching other devices): drop a new
skills/kdeconnect_skill.py file following the same shape as the skills
already here. Nothing else in the project needs to change.
"""

import importlib
import pkgutil

TOOL_DEFINITIONS = []
_DISPATCH = {}
_SKILL_MODULES = []
_TOOL_SKILLS = {}


def _load_all():
    global TOOL_DEFINITIONS, _DISPATCH, _SKILL_MODULES, _TOOL_SKILLS
    TOOL_DEFINITIONS = []
    _DISPATCH = {}
    _SKILL_MODULES = []
    _TOOL_SKILLS = {}

    for _finder, module_name, _is_pkg in pkgutil.iter_modules(__path__):
        module = importlib.import_module(f"{__name__}.{module_name}")
        definitions = getattr(module, "TOOL_DEFINITIONS", [])
        dispatch = getattr(module, "DISPATCH", {})
        skill_name = module_name.removesuffix("_skill")
        TOOL_DEFINITIONS.extend(definitions)
        for tool_name in dispatch:
            _TOOL_SKILLS[tool_name] = skill_name
        _DISPATCH.update(dispatch)
        _SKILL_MODULES.append(module)


def execute(name: str, arguments: dict) -> str:
    handler = _DISPATCH.get(name)
    if handler is None:
        return f"Unknown tool: {name}"
    return handler(arguments)


def skill_for_tool(name: str) -> str:
    return _TOOL_SKILLS.get(name, "unknown")


def catalog() -> list[dict]:
    return [
        {
            "skill": module.__name__.rsplit(".", 1)[-1].removesuffix("_skill"),
            "tools": sorted(name for name, skill in _TOOL_SKILLS.items() if skill == module.__name__.rsplit(".", 1)[-1].removesuffix("_skill")),
        }
        for module in _SKILL_MODULES
    ]


def set_memory_all(memory: dict) -> None:
    """Any skill that needs to read/write persistent memory (like
    remembering facts) exposes its own set_memory(memory) function —
    called here so skills stay decoupled from each other."""
    for module in _SKILL_MODULES:
        setter = getattr(module, "set_memory", None)
        if setter:
            setter(memory)


_load_all()
