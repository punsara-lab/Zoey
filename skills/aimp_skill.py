import os
import subprocess
import time


def _candidate_paths() -> list[str]:
    env = os.environ.get("AIMP_EXE", "").strip().strip('"').strip("'")
    c = []
    if env:
        c.append(env)
    c.extend(
        [
            r"C:\Program Files\AIMP\AIMP.exe",
            r"C:\Program Files (x86)\AIMP\AIMP.exe",
        ]
    )
    return c


def open_aimp(_args: dict) -> str:
    if os.name != "nt":
        return "AIMP open isn't supported on this OS."
    for p in _candidate_paths():
        if p and os.path.exists(p):
            try:
                os.startfile(p)  # type: ignore[attr-defined]
                time.sleep(1.0)
                return "Opened AIMP."
            except Exception as e:
                return f"Couldn't open AIMP: {e}"
    return "I couldn't find AIMP.exe. Set AIMP_EXE in .env to your AIMP.exe path."


def start_aimp_playback(_args: dict) -> str:
    if os.name != "nt":
        return "AIMP playback isn't supported on this OS."
    try:
        import tools

        return tools.execute_tool("play_pause", {})
    except Exception:
        return "I couldn't start playback."


TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "open_aimp",
            "description": "Open AIMP player (Windows).",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "start_aimp_playback",
            "description": "Start playback in AIMP using media key play/pause (best effort).",
            "parameters": {"type": "object", "properties": {}},
        },
    },
]


DISPATCH = {
    "open_aimp": open_aimp,
    "start_aimp_playback": start_aimp_playback,
}

