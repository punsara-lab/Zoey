"""
ZOEY — skills/android_skill.py
Android control via ADB (USB or Wireless debugging).
"""

import datetime
import os
import re
import subprocess

import config


def _actions_log_path() -> str:
    return os.path.join(os.getcwd(), "zoey_actions.log")


def _append_action_log(event: str, detail: str) -> None:
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"{ts}\t{event}\t{detail}\n"
    try:
        with open(_actions_log_path(), "a", encoding="utf-8") as f:
            f.write(line)
    except Exception:
        pass


def _adb_exe() -> str:
    return getattr(config, "ADB_EXECUTABLE", "adb")


def _run_adb(args: list[str], timeout: int = 12) -> tuple[int, str, str]:
    try:
        result = subprocess.run(
            [_adb_exe(), *args],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return result.returncode, (result.stdout or "").strip(), (result.stderr or "").strip()
    except FileNotFoundError:
        return 127, "", "adb not found. Install Android Platform Tools and ensure adb is in PATH."
    except subprocess.TimeoutExpired:
        return 124, "", "adb command timed out."
    except Exception as e:
        return 1, "", str(e)


def adb_devices(_args: dict) -> str:
    code, out, err = _run_adb(["devices"])
    _append_action_log("ADB_DEVICES", f"code={code}")
    if code != 0:
        return f"ADB error: {err or out}"
    return out or "(no output)"


def adb_pair(args: dict) -> str:
    host = (args.get("host") or "").strip()
    port = int(args.get("port") or 0)
    pairing_code = (args.get("pairing_code") or "").strip()
    if not host or not port or not pairing_code:
        return "Missing host/port/pairing_code."
    code, out, err = _run_adb(["pair", f"{host}:{port}", pairing_code], timeout=25)
    _append_action_log("ADB_PAIR", f"{host}:{port}\tcode={code}")
    if code != 0:
        return f"ADB pair failed: {err or out}"
    return out or "Paired."


def adb_connect(args: dict) -> str:
    host = (args.get("host") or "").strip()
    port = int(args.get("port") or 5555)
    if not host:
        return "Missing host."
    code, out, err = _run_adb(["connect", f"{host}:{port}"], timeout=20)
    _append_action_log("ADB_CONNECT", f"{host}:{port}\tcode={code}")
    if code != 0:
        return f"ADB connect failed: {err or out}"
    return out or "Connected."


def android_status(_args: dict) -> str:
    code, out, err = _run_adb(["shell", "dumpsys", "battery"], timeout=15)
    _append_action_log("ANDROID_STATUS", f"code={code}")
    if code != 0:
        return f"ADB error: {err or out}"

    level = None
    status = None
    ac = None
    usb = None
    wireless = None

    for line in (out or "").splitlines():
        m = re.match(r"\s*level:\s*(\d+)\s*$", line)
        if m:
            level = int(m.group(1))
        m = re.match(r"\s*status:\s*(\d+)\s*$", line)
        if m:
            status = int(m.group(1))
        m = re.match(r"\s*AC powered:\s*(true|false)\s*$", line, re.I)
        if m:
            ac = m.group(1).lower() == "true"
        m = re.match(r"\s*USB powered:\s*(true|false)\s*$", line, re.I)
        if m:
            usb = m.group(1).lower() == "true"
        m = re.match(r"\s*Wireless powered:\s*(true|false)\s*$", line, re.I)
        if m:
            wireless = m.group(1).lower() == "true"

    charging = bool(ac or usb or wireless)
    status_map = {
        1: "unknown",
        2: "charging",
        3: "discharging",
        4: "not_charging",
        5: "full",
    }
    status_text = status_map.get(status, "unknown")

    pieces = []
    if level is not None:
        pieces.append(f"battery: {level}%")
    pieces.append(f"status: {status_text}")
    pieces.append(f"charging: {charging}")
    if ac is not None:
        pieces.append(f"ac: {ac}")
    if usb is not None:
        pieces.append(f"usb: {usb}")
    if wireless is not None:
        pieces.append(f"wireless: {wireless}")
    return ", ".join(pieces)


TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "adb_devices",
            "description": "List connected Android devices seen by ADB.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "adb_pair",
            "description": "Pair ADB over Wi‑Fi using Wireless debugging (Android 11+). Requires host, pairing port, and pairing code shown on the phone.",
            "parameters": {
                "type": "object",
                "properties": {
                    "host": {"type": "string", "description": "Phone IP address on your LAN, e.g. 192.168.1.20"},
                    "port": {"type": "integer", "description": "Pairing port from Wireless debugging."},
                    "pairing_code": {"type": "string", "description": "Pairing code from Wireless debugging."},
                },
                "required": ["host", "port", "pairing_code"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "adb_connect",
            "description": "Connect ADB over Wi‑Fi to the phone debug port (usually 5555).",
            "parameters": {
                "type": "object",
                "properties": {
                    "host": {"type": "string", "description": "Phone IP address on your LAN, e.g. 192.168.1.20"},
                    "port": {"type": "integer", "description": "ADB connect port (default 5555 or the port shown on the phone)."},
                },
                "required": ["host"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "android_status",
            "description": "Get Android battery and charging status via ADB.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
]


DISPATCH = {
    "adb_devices": adb_devices,
    "adb_pair": adb_pair,
    "adb_connect": adb_connect,
    "android_status": android_status,
}

