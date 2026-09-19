"""Terminal dashboard for ZOEY's live local state.

Run normally with ``python zoey_dashboard.py``. Use ``q`` to quit. Use
``--once`` for a non-interactive render/smoke check.
"""

import argparse
import datetime
import json
import os
import time

from rich import box
from rich.live import Live
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.console import Console

import brain_store
import skills
import tools

try:
    import psutil
except ImportError:
    psutil = None


BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def _read_jsonl(filename: str, limit: int) -> list[dict]:
    records = list(brain_store.iter_jsonl(brain_store.path_for(filename)))
    return records[-max(1, limit) :]


def _format_time(value) -> str:
    try:
        return datetime.datetime.fromtimestamp(float(value)).strftime("%H:%M:%S")
    except (TypeError, ValueError, OSError):
        return "--:--:--"


def _short(value, width: int = 52) -> str:
    text = " ".join(str(value or "").split())
    return text if len(text) <= width else text[: width - 3] + "..."


class ZoeyDashboard:
    def __init__(self):
        self.layout = Layout(name="root")
        self.layout.split_column(
            Layout(name="header", size=5),
            Layout(name="main"),
            Layout(name="footer", size=3),
        )
        self.layout["main"].split_row(
            Layout(name="memory", ratio=3),
            Layout(name="skills", ratio=2),
            Layout(name="errors", ratio=3),
        )

    def _header(self) -> Panel:
        stats = tools.get_stats()
        brain_stats = _read_jsonl("dreams.jsonl", 1)
        memory_count = len(list(brain_store.iter_jsonl(brain_store.path_for("memory.jsonl"))))
        model = "unknown"
        try:
            import config
            model = config.LOCAL_BRAIN_MODEL
        except Exception:
            pass
        subtitle = (
            f"model={model}  memories={memory_count}  "
            f"tool_calls={stats.get('tool_calls', 0)}  "
            f"dreams={len(brain_stats)}"
        )
        return Panel(
            Text.assemble(("ZOEY DEVELOPER DASHBOARD", "bold green"), "\n", subtitle),
            title="Live local state | press q to quit",
            border_style="green",
        )

    def _memory_panel(self) -> Panel:
        table = Table(box=box.SIMPLE, expand=True)
        table.add_column("Time", style="cyan", no_wrap=True)
        table.add_column("Type", style="magenta", no_wrap=True)
        table.add_column("Content", style="green")
        for record in _read_jsonl("memory.jsonl", 6):
            table.add_row(
                _format_time(record.get("ts")),
                str(record.get("type", "memory")),
                _short(record.get("text", "")),
            )
        if not table.rows:
            table.add_row("--:--:--", "-", "No memories yet")
        return Panel(table, title="Recent Memories", border_style="cyan")

    def _skills_panel(self) -> Panel:
        table = Table(box=box.SIMPLE, expand=True)
        table.add_column("Skill", style="cyan", no_wrap=True)
        table.add_column("Tools", style="yellow", justify="right")
        table.add_column("Status", style="green")
        modules = getattr(skills, "_SKILL_MODULES", [])
        for module in modules:
            definitions = getattr(module, "TOOL_DEFINITIONS", [])
            table.add_row(module.__name__.rsplit(".", 1)[-1], str(len(definitions)), "loaded")
        if not table.rows:
            table.add_row("none", "0", "no skills loaded")
        return Panel(table, title="Active Skills", border_style="yellow")

    def _errors_panel(self) -> Panel:
        table = Table(box=box.SIMPLE, expand=True)
        table.add_column("Time", style="cyan", no_wrap=True)
        table.add_column("Error", style="red")
        records = _read_jsonl("errors.jsonl", 8)
        for record in records:
            table.add_row(_format_time(record.get("ts")), _short(record.get("error", ""), 64))
        if not table.rows:
            table.add_row("--:--:--", "No recorded errors")
        return Panel(table, title="Recent Errors", border_style="red")

    def _footer(self) -> Panel:
        if psutil is None:
            status = "CPU/RAM unavailable: install psutil | q: quit"
        else:
            status = f"CPU {psutil.cpu_percent():.0f}%  RAM {psutil.virtual_memory().percent:.0f}%  |  q: quit"
        return Panel(status, border_style="blue")

    def render(self):
        self.layout["header"].update(self._header())
        self.layout["memory"].update(self._memory_panel())
        self.layout["skills"].update(self._skills_panel())
        self.layout["errors"].update(self._errors_panel())
        self.layout["footer"].update(self._footer())
        return self.layout

    @staticmethod
    def _quit_requested() -> bool:
        try:
            import msvcrt
            if msvcrt.kbhit():
                return msvcrt.getwch().lower() == "q"
        except ImportError:
            pass
        return False

    def run(self, once: bool = False):
        if once:
            Console().print(self.render())
            return
        with Live(self.render(), refresh_per_second=2, screen=True) as live:
            while not self._quit_requested():
                time.sleep(0.5)
                live.update(self.render())


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ZOEY terminal developer dashboard")
    parser.add_argument("--once", action="store_true", help="render once and exit")
    args = parser.parse_args()
    ZoeyDashboard().run(once=args.once)
