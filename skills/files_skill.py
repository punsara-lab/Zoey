"""
ZOEY — skills/files_skill.py
Real filesystem access: list a folder, search for files by name, read a
text file, write one, or open any file with its default app. This is
the "reach into your PC" capability — deliberately unrestricted, same
trust model as run_command in system_skill.py: fine for a personal
assistant only its owner talks to, on their own machine.
"""

import fnmatch
import datetime
import os
import secrets
import shutil

MAX_RESULTS = 40
MAX_READ_CHARS = 4000
_pending_file_actions = {}


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


def _normalize_path(raw_path: str) -> str:
    p = (raw_path or "").strip()
    if not p:
        return p

    p = os.path.expanduser(p)

    if os.name == "nt":
        home = os.path.expanduser("~")

        if p.startswith("/home/"):
            parts = p.split("/")
            if len(parts) >= 3:
                rest = "/".join(parts[3:])
                p = os.path.join(home, *([x for x in rest.split("/") if x]))
            else:
                p = home

        if p.startswith("/Users/"):
            parts = p.split("/")
            if len(parts) >= 3:
                rest = "/".join(parts[3:])
                p = os.path.join(home, *([x for x in rest.split("/") if x]))
            else:
                p = home

        if p.startswith("/"):
            p = os.path.join(home, *([x for x in p.split("/") if x]))

        p = p.replace("/", "\\")

    return p


def list_directory(args: dict) -> str:
    path = _normalize_path(args.get("path", "."))
    try:
        entries = os.listdir(path)
    except Exception as e:
        return f"Couldn't list {path}: {e}"
    entries = sorted(entries)[:MAX_RESULTS]
    return "\n".join(entries) if entries else "(empty folder)"


def search_files(args: dict) -> str:
    """Searches for files by name pattern under a starting folder —
    the 'find that file' / lightweight research-on-my-own-PC tool."""
    query = args.get("query", "")
    start_path = _normalize_path(args.get("start_path", os.path.expanduser("~")))
    pattern = f"*{query}*"

    matches = []
    for root, _dirs, files in os.walk(start_path):
        for name in files:
            if fnmatch.fnmatch(name.lower(), pattern.lower()):
                matches.append(os.path.join(root, name))
                if len(matches) >= MAX_RESULTS:
                    break
        if len(matches) >= MAX_RESULTS:
            break

    if not matches:
        return f"No files matching '{query}' found under {start_path}."
    return "\n".join(matches)


def read_text_file(args: dict) -> str:
    path = _normalize_path(args.get("path", ""))
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read(MAX_READ_CHARS)
        return content if content else "(empty file)"
    except Exception as e:
        return f"Couldn't read {path}: {e}"


def write_text_file(args: dict) -> str:
    path = _normalize_path(args.get("path", ""))
    content = args.get("content", "")
    if os.path.exists(path):
        token = secrets.token_urlsafe(8)
        _pending_file_actions[token] = {"type": "write", "path": path, "content": content}
        _append_action_log("PENDING_FILE_WRITE", f"{token}\t{path}")
        return (
            "APPROVAL_REQUIRED\n"
            f"token: {token}\n"
            f"action: overwrite_file\n"
            f"path: {path}\n"
            "Ask the user to approve by replying: /approve <token> or deny with: /deny <token>.\n"
            "If approved, call approve_file_action with the token."
        )
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        _append_action_log("WRITE_FILE", path)
        return f"Wrote {len(content)} characters to {path}."
    except Exception as e:
        return f"Couldn't write {path}: {e}"


def append_text_file(args: dict) -> str:
    path = _normalize_path(args.get("path", ""))
    content = args.get("content", "")
    try:
        with open(path, "a", encoding="utf-8") as f:
            f.write(content)
        _append_action_log("APPEND_FILE", path)
        return f"Appended {len(content)} characters to {path}."
    except Exception as e:
        return f"Couldn't append {path}: {e}"


def make_directory(args: dict) -> str:
    path = _normalize_path(args.get("path", ""))
    try:
        os.makedirs(path, exist_ok=True)
        _append_action_log("MKDIR", path)
        return f"Created {path}."
    except Exception as e:
        return f"Couldn't create {path}: {e}"


def delete_path(args: dict) -> str:
    path = _normalize_path(args.get("path", ""))
    token = secrets.token_urlsafe(8)
    _pending_file_actions[token] = {"type": "delete", "path": path}
    _append_action_log("PENDING_DELETE", f"{token}\t{path}")
    return (
        "APPROVAL_REQUIRED\n"
        f"token: {token}\n"
        f"action: delete_path\n"
        f"path: {path}\n"
        "Ask the user to approve by replying: /approve <token> or deny with: /deny <token>.\n"
        "If approved, call approve_file_action with the token."
    )


def move_path(args: dict) -> str:
    src = _normalize_path(args.get("src", ""))
    dst = _normalize_path(args.get("dst", ""))
    if os.path.exists(dst):
        token = secrets.token_urlsafe(8)
        _pending_file_actions[token] = {"type": "move", "src": src, "dst": dst}
        _append_action_log("PENDING_MOVE_OVERWRITE", f"{token}\t{src}\t{dst}")
        return (
            "APPROVAL_REQUIRED\n"
            f"token: {token}\n"
            f"action: move_overwrite\n"
            f"src: {src}\n"
            f"dst: {dst}\n"
            "Ask the user to approve by replying: /approve <token> or deny with: /deny <token>.\n"
            "If approved, call approve_file_action with the token."
        )
    try:
        shutil.move(src, dst)
        _append_action_log("MOVE", f"{src}\t{dst}")
        return f"Moved {src} -> {dst}."
    except Exception as e:
        return f"Couldn't move {src} -> {dst}: {e}"


def copy_path(args: dict) -> str:
    src = _normalize_path(args.get("src", ""))
    dst = _normalize_path(args.get("dst", ""))
    if os.path.exists(dst):
        token = secrets.token_urlsafe(8)
        _pending_file_actions[token] = {"type": "copy", "src": src, "dst": dst}
        _append_action_log("PENDING_COPY_OVERWRITE", f"{token}\t{src}\t{dst}")
        return (
            "APPROVAL_REQUIRED\n"
            f"token: {token}\n"
            f"action: copy_overwrite\n"
            f"src: {src}\n"
            f"dst: {dst}\n"
            "Ask the user to approve by replying: /approve <token> or deny with: /deny <token>.\n"
            "If approved, call approve_file_action with the token."
        )
    try:
        if os.path.isdir(src):
            shutil.copytree(src, dst)
        else:
            shutil.copy2(src, dst)
        _append_action_log("COPY", f"{src}\t{dst}")
        return f"Copied {src} -> {dst}."
    except Exception as e:
        return f"Couldn't copy {src} -> {dst}: {e}"


def approve_file_action(args: dict) -> str:
    token = (args.get("token") or "").strip()
    if not token:
        return "Missing token."
    action = _pending_file_actions.pop(token, None)
    if not action:
        return "No pending file action found for that token."

    t = action.get("type")
    try:
        if t == "write":
            path = action["path"]
            content = action.get("content", "")
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            _append_action_log("APPROVED_WRITE_FILE", path)
            return f"Wrote {len(content)} characters to {path}."

        if t == "delete":
            path = action["path"]
            if os.path.isdir(path):
                shutil.rmtree(path)
            else:
                os.remove(path)
            _append_action_log("APPROVED_DELETE", path)
            return f"Deleted {path}."

        if t == "move":
            src = action["src"]
            dst = action["dst"]
            if os.path.exists(dst):
                if os.path.isdir(dst):
                    shutil.rmtree(dst)
                else:
                    os.remove(dst)
            shutil.move(src, dst)
            _append_action_log("APPROVED_MOVE_OVERWRITE", f"{src}\t{dst}")
            return f"Moved {src} -> {dst}."

        if t == "copy":
            src = action["src"]
            dst = action["dst"]
            if os.path.exists(dst):
                if os.path.isdir(dst):
                    shutil.rmtree(dst)
                else:
                    os.remove(dst)
            if os.path.isdir(src):
                shutil.copytree(src, dst)
            else:
                shutil.copy2(src, dst)
            _append_action_log("APPROVED_COPY_OVERWRITE", f"{src}\t{dst}")
            return f"Copied {src} -> {dst}."

        return "Unknown pending action type."
    except Exception as e:
        _append_action_log("APPROVED_FILE_ACTION_ERROR", f"{t}\t{e}")
        return f"Couldn't complete approved action: {e}"


def deny_file_action(args: dict) -> str:
    token = (args.get("token") or "").strip()
    if not token:
        return "Missing token."
    action = _pending_file_actions.pop(token, None)
    if not action:
        return "No pending file action found for that token."
    _append_action_log("DENIED_FILE_ACTION", f"{token}\t{action.get('type')}\t{action}")
    return "Denied."


def list_pending_file_actions(_args: dict) -> str:
    if not _pending_file_actions:
        return "No pending file actions."
    lines = []
    for token, action in list(_pending_file_actions.items())[:10]:
        t = action.get("type")
        if t == "write":
            lines.append(f"{token}: overwrite {action.get('path')}")
        elif t == "delete":
            lines.append(f"{token}: delete {action.get('path')}")
        elif t == "move":
            lines.append(f"{token}: move {action.get('src')} -> {action.get('dst')}")
        elif t == "copy":
            lines.append(f"{token}: copy {action.get('src')} -> {action.get('dst')}")
        else:
            lines.append(f"{token}: {t}")
    return "\n".join(lines)


def open_file(args: dict) -> str:
    path = _normalize_path(args.get("path", ""))
    try:
        if os.name == "nt":
            os.startfile(path)  # type: ignore[attr-defined]
        else:
            import subprocess

            opener = "open" if os.uname().sysname == "Darwin" else "xdg-open"
            subprocess.Popen([opener, path])
        return f"Opened {path}."
    except Exception as e:
        return f"Couldn't open {path}: {e}"


TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "list_directory",
            "description": "List files and folders inside a directory on the user's PC.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Folder path to list."}
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_files",
            "description": "Search for files by name (partial match) under a starting folder. Use this to find something on the user's PC.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Part of the filename to search for."},
                    "start_path": {
                        "type": "string",
                        "description": "Folder to search under. Defaults to the user's home folder if not given.",
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_text_file",
            "description": "Read the contents of a text file on the user's PC.",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string", "description": "Full path to the file."}},
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_text_file",
            "description": "Write text content to a file on the user's PC. If the file exists, returns APPROVAL_REQUIRED with a token; ask the user, then call approve_file_action with that token.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Full path to the file."},
                    "content": {"type": "string", "description": "Text content to write."},
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "append_text_file",
            "description": "Append text content to a file on the user's PC (creates it if missing).",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Full path to the file."},
                    "content": {"type": "string", "description": "Text content to append."},
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "make_directory",
            "description": "Create a directory (and parents if needed).",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string", "description": "Folder path to create."}},
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "delete_path",
            "description": "Delete a file or folder. Always returns APPROVAL_REQUIRED with a token; ask the user, then call approve_file_action with that token.",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string", "description": "Path to delete (file or folder)."}},
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "move_path",
            "description": "Move/rename a file or folder. If destination exists, returns APPROVAL_REQUIRED with a token; ask the user, then call approve_file_action with that token.",
            "parameters": {
                "type": "object",
                "properties": {
                    "src": {"type": "string", "description": "Source path."},
                    "dst": {"type": "string", "description": "Destination path."},
                },
                "required": ["src", "dst"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "copy_path",
            "description": "Copy a file or folder. If destination exists, returns APPROVAL_REQUIRED with a token; ask the user, then call approve_file_action with that token.",
            "parameters": {
                "type": "object",
                "properties": {
                    "src": {"type": "string", "description": "Source path."},
                    "dst": {"type": "string", "description": "Destination path."},
                },
                "required": ["src", "dst"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "approve_file_action",
            "description": "Approve and execute a pending file action using its token.",
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
            "name": "deny_file_action",
            "description": "Deny a pending file action using its token.",
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
            "name": "list_pending_file_actions",
            "description": "List pending file approvals (token -> action).",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "open_file",
            "description": "Open any file with its default application (documents, images, etc).",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string", "description": "Full path to the file."}},
                "required": ["path"],
            },
        },
    },
]

DISPATCH = {
    "list_directory": list_directory,
    "search_files": search_files,
    "read_text_file": read_text_file,
    "write_text_file": write_text_file,
    "append_text_file": append_text_file,
    "make_directory": make_directory,
    "delete_path": delete_path,
    "move_path": move_path,
    "copy_path": copy_path,
    "approve_file_action": approve_file_action,
    "deny_file_action": deny_file_action,
    "list_pending_file_actions": list_pending_file_actions,
    "open_file": open_file,
}
