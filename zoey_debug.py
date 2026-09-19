#!/usr/bin/env python3
"""ZOEY Debug Dashboard.

Shows memories, skills, errors, identity, and engine state for this project.
Run ``python zoey_debug.py`` or use ``--once`` for a single render.
"""

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

try:
    from rich import box
    from rich.console import Console
    from rich.layout import Layout
    from rich.live import Live
    from rich.panel import Panel
    from rich.table import Table
except ImportError:
    print("Installing rich...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "rich"])
    from rich import box
    from rich.console import Console
    from rich.layout import Layout
    from rich.live import Live
    from rich.panel import Panel
    from rich.table import Table

try:
    import psutil
except ImportError:
    print("Installing psutil...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "psutil"])
    import psutil


console = Console()
ROOT = Path(__file__).resolve().parent
BRAIN_DIR = ROOT / "brain"
DATA_DIR = ROOT / "data"


class ZoeyDebugger:
    def __init__(self):
        self.memory_file = BRAIN_DIR / "memory.jsonl"
        self.error_file = BRAIN_DIR / "errors.jsonl"
        self.user_file = DATA_DIR / "user.json"
        self.zoey_file = DATA_DIR / "zoey.json"
        self.skills_dir = ROOT / "skills"

    @staticmethod
    def _time(value) -> str:
        try:
            return datetime.fromtimestamp(float(value)).strftime("%H:%M:%S")
        except (TypeError, ValueError, OSError):
            return str(value or "?")[-8:]

    @staticmethod
    def _short(value, width=60) -> str:
        text = " ".join(str(value or "").split())
        return text if len(text) <= width else text[: width - 3] + "..."

    def _read_jsonl(self, path: Path) -> list[dict]:
        if not path.exists():
            return []
        records = []
        try:
            with path.open("r", encoding="utf-8", errors="replace") as handle:
                for line in handle:
                    try:
                        item = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if isinstance(item, dict):
                        records.append(item)
        except OSError:
            return []
        return records

    def get_memories(self, limit=10):
        records = self._read_jsonl(self.memory_file)[-limit:]
        if not records:
            return [{"time": "now", "type": "info", "content": "No memories yet"}]
        return [
            {
                "time": self._time(item.get("ts", item.get("timestamp"))),
                "type": item.get("type", "memory"),
                "content": self._short(item.get("text", item.get("content", item)), 60),
            }
            for item in records
        ]

    def get_skills(self):
        if not self.skills_dir.exists():
            return [{"name": "no skills folder", "status": "?", "calls": 0}]
        skills = []
        for file in sorted(self.skills_dir.glob("*.py")):
            if file.name.startswith("__"):
                continue
            name = file.name.replace("_skill.py", "").replace(".py", "")
            skills.append({"name": name, "status": "loaded", "calls": "?"})
        return skills or [{"name": "no skills found", "status": "-", "calls": 0}]

    @staticmethod
    def _read_json(path: Path) -> dict | None:
        try:
            with path.open("r", encoding="utf-8") as handle:
                value = json.load(handle)
            return value if isinstance(value, dict) else None
        except (OSError, ValueError):
            return None

    def get_zoey_info(self):
        data = self._read_json(self.zoey_file)
        if not data:
            return "Zoey config not found"
        return f"{data.get('name', 'ZOEY')} | identity rules: {len(data.get('identity_rules', []))}"

    def get_user_info(self):
        data = self._read_json(self.user_file)
        if not data:
            return "User not configured"
        return f"User: {data.get('preferred_name', data.get('name', 'unknown'))}"

    def check_engine(self):
        if not (ROOT / "engine.py").exists():
            return "[red]engine.py NOT FOUND[/red]"
        for proc in psutil.process_iter(["pid", "name", "cmdline"]):
            try:
                name = (proc.info.get("name") or "").lower()
                command = " ".join(proc.info.get("cmdline") or []).lower()
                if "python" in name and ("engine.py" in command or "console_app.py" in command or "main.py" in command):
                    return f"[green]Running (PID {proc.info['pid']})[/green]"
            except (psutil.Error, AttributeError):
                continue
        return "[yellow]engine exists but is not running[/yellow]"

    def get_recent_errors(self):
        records = self._read_jsonl(self.error_file)[-5:]
        if not records:
            return [{"time": "-", "msg": "No errors logged"}]
        return [
            {
                "time": self._time(item.get("ts", item.get("timestamp"))),
                "msg": self._short(item.get("error", item.get("content", item)), 60),
            }
            for item in records
        ]

    def create_layout(self):
        memory_table = Table(box=box.SIMPLE, show_header=True, expand=True)
        memory_table.add_column("Time", style="cyan", width=8)
        memory_table.add_column("Type", style="magenta", width=12)
        memory_table.add_column("Content", style="green")
        for memory in self.get_memories(8):
            memory_table.add_row(memory["time"], memory["type"], memory["content"])

        skill_table = Table(box=box.SIMPLE, expand=True)
        skill_table.add_column("Skill", style="cyan")
        skill_table.add_column("Status", style="green")
        for skill in self.get_skills()[:12]:
            skill_table.add_row(skill["name"], skill["status"])

        error_table = Table(box=box.SIMPLE, expand=True)
        error_table.add_column("Time", style="dim", width=8)
        error_table.add_column("Error", style="red")
        for error in self.get_recent_errors():
            error_table.add_row(error["time"], error["msg"])

        memory_count = len(self._read_jsonl(self.memory_file))
        status = (
            f"{self.get_user_info()}\n"
            f"{self.get_zoey_info()}\n"
            f"Engine: {self.check_engine()}\n"
            f"Memories: {memory_count} | CPU: {psutil.cpu_percent():.0f}% | RAM: {psutil.virtual_memory().percent:.0f}%"
        )

        layout = Layout(name="root")
        layout.split_column(
            Layout(Panel(status, title="ZOEY Status", border_style="blue"), size=7),
            Layout(name="main"),
        )
        layout["main"].split_row(
            Layout(Panel(memory_table, title="Recent Memories", border_style="green"), ratio=3),
            Layout(Panel(skill_table, title="Loaded Skills", border_style="yellow"), ratio=2),
            Layout(Panel(error_table, title="Errors", border_style="red"), ratio=2),
        )
        return layout

    def run(self, once=False):
        if once:
            console.print(self.create_layout())
            return
        console.clear()
        console.print("[bold green]ZOEY Debug Dashboard[/bold green]")
        console.print("[dim]Watching your ZOEY folder... Press Ctrl+C to exit[/dim]\n")
        try:
            with Live(self.create_layout(), refresh_per_second=1) as live:
                while True:
                    time.sleep(0.5)
                    live.update(self.create_layout())
        except KeyboardInterrupt:
            console.print("\n[dim]Dashboard closed.[/dim]")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ZOEY debug dashboard")
    parser.add_argument("--once", action="store_true", help="render once and exit")
    ZoeyDebugger().run(once=parser.parse_args().once)
