import ctypes
import ctypes.wintypes
import os
import time


_user32 = None
_ULONG_PTR = getattr(ctypes.wintypes, "ULONG_PTR", ctypes.c_size_t)


def _u32():
    global _user32
    if _user32 is None:
        _user32 = ctypes.WinDLL("user32", use_last_error=True)
    return _user32


class _KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", ctypes.wintypes.WORD),
        ("wScan", ctypes.wintypes.WORD),
        ("dwFlags", ctypes.wintypes.DWORD),
        ("time", ctypes.wintypes.DWORD),
        ("dwExtraInfo", _ULONG_PTR),
    ]


class _INPUT_UNION(ctypes.Union):
    _fields_ = [("ki", _KEYBDINPUT)]


class _INPUT(ctypes.Structure):
    _fields_ = [("type", ctypes.wintypes.DWORD), ("u", _INPUT_UNION)]


def _send_vk(vk: int) -> bool:
    if os.name != "nt":
        return False
    user32 = _u32()
    INPUT_KEYBOARD = 1
    KEYEVENTF_KEYUP = 0x0002
    KEYEVENTF_EXTENDEDKEY = 0x0001
    inp_down = _INPUT(type=INPUT_KEYBOARD, u=_INPUT_UNION(ki=_KEYBDINPUT(wVk=vk, wScan=0, dwFlags=0, time=0, dwExtraInfo=0)))
    inp_up = _INPUT(type=INPUT_KEYBOARD, u=_INPUT_UNION(ki=_KEYBDINPUT(wVk=vk, wScan=0, dwFlags=KEYEVENTF_KEYUP, time=0, dwExtraInfo=0)))
    arr = (_INPUT * 2)(inp_down, inp_up)
    sent = user32.SendInput(2, ctypes.byref(arr), ctypes.sizeof(_INPUT))
    if int(sent) == 2:
        return True
    try:
        user32.keybd_event(vk, 0, KEYEVENTF_EXTENDEDKEY, 0)
        user32.keybd_event(vk, 0, KEYEVENTF_EXTENDEDKEY | KEYEVENTF_KEYUP, 0)
        return True
    except Exception:
        return False


def _enum_windows_titles() -> list[str]:
    if os.name != "nt":
        return []
    user32 = _u32()
    titles: list[str] = []

    EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.wintypes.BOOL, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM)

    def cb(hwnd, _lparam):
        if not user32.IsWindowVisible(hwnd):
            return True
        length = user32.GetWindowTextLengthW(hwnd)
        if length <= 0:
            return True
        buf = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buf, length + 1)
        t = (buf.value or "").strip()
        if t:
            titles.append(t)
        return True

    user32.EnumWindows(EnumWindowsProc(cb), 0)
    return titles


def _best_aimp_title() -> str | None:
    titles = _enum_windows_titles()
    if not titles:
        return None
    candidates = [t for t in titles if "aimp" in t.lower()]
    if not candidates:
        return None
    candidates.sort(key=lambda x: len(x), reverse=True)
    return candidates[0]


def _parse_track_from_title(title: str) -> str | None:
    t = (title or "").strip()
    if not t:
        return None
    low = t.lower()
    if low == "aimp":
        return None
    for s in [" - aimp", " — aimp", " | aimp", " · aimp"]:
        if low.endswith(s):
            t = t[: -len(s)].strip()
            break
    for p in ["aimp - ", "aimp — ", "aimp | ", "aimp: "]:
        if low.startswith(p):
            t = t[len(p) :].strip()
            break
    if not t or t.lower() == "aimp":
        return None
    return t


def get_now_playing(_args: dict) -> str:
    if os.name != "nt":
        return "Now playing detection isn't supported on this OS."
    title = _best_aimp_title()
    if not title:
        return "I can't see AIMP right now. Is it open?"
    track = _parse_track_from_title(title)
    if track:
        return f"Now playing: {track}"
    return "AIMP is open, but I couldn't read the current track name."


def volume_up(args: dict) -> str:
    steps = int(args.get("steps") or 1)
    steps = max(1, min(steps, 50))
    for _ in range(steps):
        if not _send_vk(0xAF):
            return "I couldn't change the volume."
        time.sleep(0.03)
    return "Volume up."


def volume_down(args: dict) -> str:
    steps = int(args.get("steps") or 1)
    steps = max(1, min(steps, 50))
    for _ in range(steps):
        if not _send_vk(0xAE):
            return "I couldn't change the volume."
        time.sleep(0.03)
    return "Volume down."


def volume_mute(_args: dict) -> str:
    if not _send_vk(0xAD):
        return "I couldn't mute."
    return "Muted."


def next_track(_args: dict) -> str:
    if not _send_vk(0xB0):
        return "I couldn't skip to the next track."
    time.sleep(0.6)
    np = get_now_playing({})
    if np.lower().startswith("now playing:"):
        return np
    return "Next track."


def previous_track(_args: dict) -> str:
    if not _send_vk(0xB1):
        return "I couldn't go to the previous track."
    time.sleep(0.6)
    np = get_now_playing({})
    if np.lower().startswith("now playing:"):
        return np
    return "Previous track."


def play_pause(_args: dict) -> str:
    if not _send_vk(0xB3):
        return "I couldn't toggle play/pause."
    time.sleep(0.4)
    np = get_now_playing({})
    if np.lower().startswith("now playing:"):
        return np
    return "Toggled play/pause."


TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "get_now_playing",
            "description": "Get the currently playing track (best effort; reads AIMP window title on Windows).",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "volume_up",
            "description": "Increase system volume (sends media key).",
            "parameters": {
                "type": "object",
                "properties": {
                    "steps": {"type": "integer", "description": "How many volume steps to apply."}
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "volume_down",
            "description": "Decrease system volume (sends media key).",
            "parameters": {
                "type": "object",
                "properties": {
                    "steps": {"type": "integer", "description": "How many volume steps to apply."}
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "next_track",
            "description": "Skip to next track (sends media key) and then report now playing.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "volume_mute",
            "description": "Mute/unmute system volume (toggles mute).",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "previous_track",
            "description": "Go to previous track (sends media key) and then report now playing.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "play_pause",
            "description": "Toggle play/pause (sends media key) and then report now playing.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
]


DISPATCH = {
    "get_now_playing": get_now_playing,
    "volume_up": volume_up,
    "volume_down": volume_down,
    "volume_mute": volume_mute,
    "next_track": next_track,
    "previous_track": previous_track,
    "play_pause": play_pause,
}
