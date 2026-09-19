"""ZOEY integration for the optional Needle 2 file agent."""

import importlib
import os


_NEEDLE_MODULE = None
_NEEDLE_ERROR = None


def _load_needle():
    global _NEEDLE_MODULE, _NEEDLE_ERROR
    if _NEEDLE_MODULE is not None or _NEEDLE_ERROR is not None:
        return _NEEDLE_MODULE
    try:
        _NEEDLE_MODULE = importlib.import_module("needle2.agent")
    except Exception as exc:
        _NEEDLE_ERROR = str(exc)
    return _NEEDLE_MODULE


def run_needle2_file_agent(args: dict) -> str:
    """Run Needle 2 for file lookup, recent-file listing, or file organization."""
    query = (args.get("query") or "").strip()
    if not query:
        return "Need a file request, such as find my physics notes or list recent files."

    module = _load_needle()
    if module is None:
        return (
            "Needle 2 is unavailable. Install the optional dependency with "
            f"'pip install cactus-needle'. Details: {_NEEDLE_ERROR}"
        )

    folder = getattr(module.cfg, "FOLDER_PATH", "")
    if not os.path.isdir(folder):
        return f"Needle 2 folder not found: {folder}. Update needle2/config.py."

    try:
        outcome = module.agent.run(query)
        if isinstance(outcome, dict):
            results = outcome.get("results", [])
        else:
            results = outcome
        if isinstance(results, (list, tuple)):
            return "\n".join(str(item) for item in results) or "Needle 2 returned no result."
        return str(results)
    except Exception as exc:
        return f"Needle 2 could not complete that request: {exc}"


TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "run_needle2_file_agent",
            "description": (
                "Zoey's file sense for this computer: find files, list recent files, "
                "or move and organize files in the configured folder. "
                "Does not read file contents or control apps, mouse, or keyboard. "
                "Use this whenever the user asks to find, list, or organize files."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The user's plain-English file request.",
                    }
                },
                "required": ["query"],
            },
        },
    }
]

DISPATCH = {"run_needle2_file_agent": run_needle2_file_agent}
