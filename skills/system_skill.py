"""
ZOEY — skills/system_skill.py
Basic PC control: open apps, run shell commands, check the time, open
URLs, and write to persistent memory.
"""

import datetime
import csv
import os
import secrets
import subprocess
import webbrowser

_memory = None
_pending_commands = {}
_app_process_map = {
    "chrome": ["chrome.exe"],
    "google chrome": ["chrome.exe"],
    "edge": ["msedge.exe"],
    "microsoft edge": ["msedge.exe"],
    "spotify": ["spotify.exe"],
    "youtube music": ["ytmdesktop.exe", "youtube music.exe", "youtubemusic.exe"],
}


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


def _command_is_safe(command: str) -> bool:
    cmd = (command or "").strip().lower()
    if not cmd:
        return True
    if any(x in cmd for x in ["&&", "||", "|", ">", "<", ";"]):
        return False
    if cmd in {
        "explorer.exe shell:mycomputerfolder",
        "explorer.exe shell:desktop",
        "explorer.exe shell:downloads",
        "explorer.exe shell:documents",
    }:
        return True
    first = cmd.split()[0]
    deny_first = {
        "del",
        "erase",
        "rd",
        "rmdir",
        "format",
        "shutdown",
        "restart",
        "reboot",
        "reg",
        "diskpart",
        "bcdedit",
        "powershell",
        "pwsh",
    }
    if first in deny_first:
        return False

    safe_first = {
        "dir",
        "type",
        "echo",
        "whoami",
        "ipconfig",
        "where",
        "ver",
        "cd",
        "python",
        "pip",
        "git",
    }
    if first in safe_first:
        if first == "pip" and any(x in cmd for x in ["install", "uninstall"]):
            return False
        if first == "git" and not any(cmd.startswith(f"git {x}") for x in ["status", "diff", "log", "branch", "rev-parse", "--version"]):
            return False
        return True
    return False


def set_memory(memory: dict) -> None:
    global _memory
    _memory = memory


def _list_windows_processes() -> set[str]:
    if os.name != "nt":
        return set()
    try:
        result = subprocess.run(
            ["tasklist", "/FO", "CSV", "/NH"],
            capture_output=True,
            text=True,
            timeout=8,
            shell=False,
        )
        out = (result.stdout or "").strip()
        if not out:
            return set()
        names = set()
        for row in csv.reader(out.splitlines()):
            if row and row[0]:
                names.add(row[0].strip().lower())
        return names
    except Exception:
        return set()


def open_app(args: dict) -> str:
    app_name = args.get("app_name", "")
    try:
        if os.name == "nt":
            os.startfile(app_name)  # type: ignore[attr-defined]
        else:
            subprocess.Popen([app_name])
        return f"Opened {app_name}."
    except Exception as e:
        return f"Couldn't open {app_name}: {e}"


def close_app(args: dict) -> str:
    app_name = (args.get("app_name") or "").strip()
    if not app_name:
        return "Missing app_name."
    if os.name != "nt":
        return "Close app isn't supported on this OS yet."

    key = app_name.strip().lower()
    candidates = []
    if key.endswith(".exe"):
        candidates = [key]
    else:
        candidates = _app_process_map.get(key, [])
        if not candidates:
            guessed = (key.replace(".exe", "").strip() + ".exe").strip()
            candidates = [guessed]

    running = _list_windows_processes()
    tried = []
    for exe in candidates:
        exe_norm = (exe or "").strip().lower()
        if not exe_norm:
            continue
        tried.append(exe_norm)
        if running and exe_norm not in running:
            continue
        try:
            result = subprocess.run(
                ["taskkill", "/IM", exe_norm, "/T", "/F"],
                capture_output=True,
                text=True,
                timeout=8,
                shell=False,
            )
            if result.returncode == 0:
                _append_action_log("CLOSE_APP", f"{app_name}\t{exe_norm}")
                return f"Closed {app_name}."
        except Exception:
            continue

    if key == "youtube music":
        return "I couldn't find a YouTube Music app process to close. If you're playing it in Chrome/Edge, I can't close just that tab yet."
    if tried:
        return f"I couldn't find a running process for {app_name}."
    return f"I couldn't close {app_name}."


def run_command(args: dict) -> str:
    command = args.get("command", "")
    if not _command_is_safe(command):
        token = secrets.token_urlsafe(8)
        _pending_commands[token] = command
        _append_action_log("PENDING_COMMAND", f"{token}\t{command}")
        return (
            "APPROVAL_REQUIRED\n"
            f"token: {token}\n"
            f"command: {command}\n"
            "Ask the user to approve by replying: /approve <token> or deny with: /deny <token>.\n"
            "If approved, call approve_command with the token."
        )
    try:
        result = subprocess.run(
            command, shell=True, capture_output=True, text=True, timeout=20
        )
        _append_action_log("RUN_COMMAND", command)
        output = (result.stdout or "").strip()
        error = (result.stderr or "").strip()
        if error and not output:
            return f"Command ran with an error: {error[:500]}"
        return output[:1000] if output else "Command ran with no output."
    except subprocess.TimeoutExpired:
        return "Command timed out after 20 seconds."
    except Exception as e:
        return f"Couldn't run that command: {e}"


def approve_command(args: dict) -> str:
    token = (args.get("token") or "").strip()
    if not token:
        return "Missing token."
    command = _pending_commands.pop(token, None)
    if not command:
        return "No pending command found for that token."
    try:
        result = subprocess.run(
            command, shell=True, capture_output=True, text=True, timeout=20
        )
        _append_action_log("APPROVED_RUN_COMMAND", command)
        output = (result.stdout or "").strip()
        error = (result.stderr or "").strip()
        if error and not output:
            return f"Command ran with an error: {error[:500]}"
        return output[:1000] if output else "Command ran with no output."
    except subprocess.TimeoutExpired:
        _append_action_log("APPROVED_RUN_COMMAND_TIMEOUT", command)
        return "Command timed out after 20 seconds."
    except Exception as e:
        _append_action_log("APPROVED_RUN_COMMAND_ERROR", f"{command}\t{e}")
        return f"Couldn't run that command: {e}"


def deny_command(args: dict) -> str:
    token = (args.get("token") or "").strip()
    if not token:
        return "Missing token."
    command = _pending_commands.pop(token, None)
    if not command:
        return "No pending command found for that token."
    _append_action_log("DENIED_COMMAND", f"{token}\t{command}")
    return "Denied."


def list_pending_commands(_args: dict) -> str:
    if not _pending_commands:
        return "No pending commands."
    lines = []
    for token, cmd in list(_pending_commands.items())[:10]:
        lines.append(f"{token}: {cmd}")
    return "\n".join(lines)


def get_current_time(_args: dict) -> str:
    return datetime.datetime.now().strftime("%A, %B %d, %Y — %I:%M %p")


def open_url(args: dict) -> str:
    url = args.get("url", "")
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    webbrowser.open(url)
    return f"Opened {url}."


def remember_fact(args: dict) -> str:
    fact = args.get("fact", "")
    if _memory is None:
        return "Memory isn't initialized yet."
    import memory as memory_module

    memory_module.add_fact(_memory, fact)
    return f"Got it — I'll remember that: {fact}"


def remember_preference(args: dict) -> str:
    preference = args.get("preference", "")
    if _memory is None:
        return "Memory isn't initialized yet."
    import memory as memory_module

    memory_module.add_preference(_memory, preference)
    return f"Noted your preference: {preference}"


TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "open_app",
            "description": "Open an application on the user's PC by name.",
            "parameters": {
                "type": "object",
                "properties": {
                    "app_name": {
                        "type": "string",
                        "description": "Name or path of the application, e.g. 'notepad' or 'chrome'.",
                    }
                },
                "required": ["app_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "close_app",
            "description": "Close a running application by name (Windows only). Example: 'youtube music', 'chrome', 'spotify'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "app_name": {
                        "type": "string",
                        "description": "App name or process name, e.g. 'youtube music' or 'chrome.exe'.",
                    }
                },
                "required": ["app_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_command",
            "description": "Run a shell command on the user's PC and return its output. If the command is risky, this returns APPROVAL_REQUIRED with a token; ask the user, then call approve_command with that token.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "The shell command to run."}
                },
                "required": ["command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "approve_command",
            "description": "Approve and execute a previously requested run_command using its token.",
            "parameters": {
                "type": "object",
                "properties": {"token": {"type": "string", "description": "Approval token."}},
                "required": ["token"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "deny_command",
            "description": "Deny a previously requested run_command using its token.",
            "parameters": {
                "type": "object",
                "properties": {"token": {"type": "string", "description": "Approval token."}},
                "required": ["token"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_pending_commands",
            "description": "List pending command approvals (token -> command).",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_current_time",
            "description": "Get the current date and time.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "open_url",
            "description": "Open a URL in the default web browser.",
            "parameters": {
                "type": "object",
                "properties": {"url": {"type": "string", "description": "The URL to open."}},
                "required": ["url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "remember_fact",
            "description": "Permanently remember a fact about the user for future conversations.",
            "parameters": {
                "type": "object",
                "properties": {"fact": {"type": "string", "description": "The fact to remember."}},
                "required": ["fact"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "remember_preference",
            "description": "Permanently remember a stated preference of the user.",
            "parameters": {
                "type": "object",
                "properties": {
                    "preference": {"type": "string", "description": "The preference to remember."}
                },
                "required": ["preference"],
            },
        },
    },
]

DISPATCH = {
    "open_app": open_app,
    "close_app": close_app,
    "run_command": run_command,
    "approve_command": approve_command,
    "deny_command": deny_command,
    "list_pending_commands": list_pending_commands,
    "get_current_time": get_current_time,
    "open_url": open_url,
    "remember_fact": remember_fact,
    "remember_preference": remember_preference,
}
