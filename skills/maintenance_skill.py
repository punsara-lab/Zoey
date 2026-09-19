import ctypes
import ctypes.wintypes
import os
import shutil
import tempfile
import time


def _windows_memory_status() -> dict | None:
    if os.name != "nt":
        return None

    class MEMORYSTATUSEX(ctypes.Structure):
        _fields_ = [
            ("dwLength", ctypes.wintypes.DWORD),
            ("dwMemoryLoad", ctypes.wintypes.DWORD),
            ("ullTotalPhys", ctypes.c_ulonglong),
            ("ullAvailPhys", ctypes.c_ulonglong),
            ("ullTotalPageFile", ctypes.c_ulonglong),
            ("ullAvailPageFile", ctypes.c_ulonglong),
            ("ullTotalVirtual", ctypes.c_ulonglong),
            ("ullAvailVirtual", ctypes.c_ulonglong),
            ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
        ]

    stat = MEMORYSTATUSEX()
    stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
    try:
        ok = ctypes.WinDLL("kernel32", use_last_error=True).GlobalMemoryStatusEx(ctypes.byref(stat))
        if not ok:
            return None
        return {
            "memory_load_percent": int(stat.dwMemoryLoad),
            "total_phys_bytes": int(stat.ullTotalPhys),
            "avail_phys_bytes": int(stat.ullAvailPhys),
            "total_pagefile_bytes": int(stat.ullTotalPageFile),
            "avail_pagefile_bytes": int(stat.ullAvailPageFile),
        }
    except Exception:
        return None


def get_system_memory(_args: dict) -> str:
    stat = _windows_memory_status()
    if not stat:
        return "Memory info unavailable."
    avail_mb = stat["avail_phys_bytes"] // (1024 * 1024)
    total_mb = stat["total_phys_bytes"] // (1024 * 1024)
    load = stat["memory_load_percent"]
    return f"Memory: {avail_mb}MB free / {total_mb}MB total (load {load}%)."


def clean_temp(args: dict) -> str:
    max_files = int(args.get("max_files") or 400)
    min_age_days = int(args.get("min_age_days") or 14)
    min_age_seconds = float(min_age_days) * 86400.0
    now = time.time()

    temp_root = tempfile.gettempdir()
    deleted = 0
    freed = 0
    errors = 0

    zoey_dir = os.path.join(temp_root, "zoey")
    if os.path.isdir(zoey_dir):
        try:
            size_before = 0
            for root, _dirs, files in os.walk(zoey_dir):
                for f in files:
                    p = os.path.join(root, f)
                    try:
                        size_before += os.path.getsize(p)
                    except Exception:
                        pass
            shutil.rmtree(zoey_dir, ignore_errors=True)
            freed += size_before
        except Exception:
            errors += 1

    safe_ext = {".tmp", ".log"}
    unsafe_ext = {".exe", ".msi", ".bat", ".cmd", ".ps1", ".dll", ".sys", ".zip", ".7z", ".rar"}

    try:
        for name in os.listdir(temp_root):
            if deleted >= max_files:
                break
            p = os.path.join(temp_root, name)
            if os.path.isdir(p):
                continue
            low = name.lower()
            ext = os.path.splitext(low)[1]
            if ext in unsafe_ext:
                continue
            if ext not in safe_ext and not (low.startswith("zoey") or low.startswith("tmp") or low.startswith("~")):
                continue
            try:
                st = os.stat(p)
                age = now - float(st.st_mtime)
                if age < min_age_seconds:
                    continue
                size = int(st.st_size)
                os.remove(p)
                deleted += 1
                freed += size
            except Exception:
                errors += 1
                continue
    except Exception:
        errors += 1

    freed_mb = freed / (1024 * 1024)
    return f"Temp cleanup: deleted={deleted} freed={freed_mb:.1f}MB errors={errors} temp={temp_root}"


TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "get_system_memory",
            "description": "Get current system memory usage (Windows).",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "clean_temp",
            "description": "Clean old safe temp files and Zoey temp folder to free memory/disk space (Windows).",
            "parameters": {
                "type": "object",
                "properties": {
                    "max_files": {"type": "integer", "description": "Maximum number of files to delete."},
                    "min_age_days": {"type": "integer", "description": "Only delete files older than this many days."},
                },
            },
        },
    },
]


DISPATCH = {
    "get_system_memory": get_system_memory,
    "clean_temp": clean_temp,
}

