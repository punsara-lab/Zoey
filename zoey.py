"""
ZOEY — one entry point for everything.
  1. Dream Visualizer  — terminal opening animation (memory consolidation)
  2. Engine Agent      — voice + typed chat, TTS/STT, tools, skills, learning
  3. Chat Web UI       — http://127.0.0.1:8765  (parallel thread)

Run:  python zoey.py
"""

import os
import sys
import time
import random
import queue
import threading
import datetime
from collections import defaultdict

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)


# ---------------------------------------------------------------------------
# Dream Visualizer — terminal opening animation
# ---------------------------------------------------------------------------
class DreamVisualizer:
    def __init__(self, width=80, height=22):
        self.width = width
        self.height = height
        self.memories = []
        self.clusters = defaultdict(list)
        self.enabled = True
        try:
            import shutil
            cols = shutil.get_terminal_size((80, 24)).columns
            if cols < 60:
                self.enabled = False
        except Exception:
            pass

    def generate_memories(self, count=55):
        topics = ["python", "research", "error", "success", "question", "discovery"]
        for i in range(count):
            self.memories.append({
                "id": i,
                "x": random.randint(5, self.width - 5),
                "y": random.randint(3, self.height - 3),
                "topic": random.choice(topics),
                "intensity": random.uniform(0.3, 1.0),
                "cluster": None,
            })

    def cluster_memories(self):
        for mem in self.memories:
            if mem["cluster"] is None:
                self.clusters[mem["topic"]].append(mem)
                mem["cluster"] = mem["topic"]

    def _sep(self, color="\033[95m"):
        return color + "─" * self.width + "\033[0m"

    def _run_animation(self):
        cluster_targets = {
            "python":    (18, 7),
            "research":  (62, 7),
            "error":     (18, 17),
            "success":   (62, 17),
            "question":  (40, 12),
            "discovery": (40, 5),
        }
        CSI = "\033["
        sys.stdout.write(CSI + "2J" + CSI + "H")
        sys.stdout.flush()

        for frame in range(28):
            canvas = [[" " for _ in range(self.width)] for _ in range(self.height)]
            for mem in self.memories:
                if mem["cluster"]:
                    tx, ty = cluster_targets.get(mem["cluster"], (40, 12))
                    mem["x"] += (tx - mem["x"]) * 0.17
                    mem["y"] += (ty - mem["y"]) * 0.17
                x, y = int(mem["x"]), int(mem["y"])
                if 0 <= x < self.width and 0 <= y < self.height:
                    canvas[y][x] = "\x01" if mem["cluster"] else "\x02"
            if frame > 13:
                for topic, (tx, ty) in cluster_targets.items():
                    label = f"[{topic.upper()}]"
                    ly = min(ty + 1, self.height - 1)
                    lx0 = tx - len(label) // 2
                    for off, ch in enumerate(label):
                        lx = lx0 + off
                        if 0 <= lx < self.width:
                            canvas[ly][lx] = ch

            lines = [
                self._sep(),
                (f"\033[95m ZOEY · DREAM CYCLE {frame + 1:02d}/28 · "
                 f"{len(self.memories)} memories consolidating "
                 f"\033[0m").ljust(self.width + 9, " "),
                self._sep(),
            ]
            for row in canvas:
                buf = []
                for ch in row:
                    if ch == "\x01":
                        buf.append("\033[95m●\033[0m")
                    elif ch == "\x02":
                        buf.append("\033[37m○\033[0m")
                    else:
                        buf.append(ch)
                lines.append("".join(buf))

            sys.stdout.write(CSI + "H" + "\n".join(lines) + CSI + "J")
            sys.stdout.flush()
            time.sleep(0.12)

        for _ in range(3):
            sys.stdout.write(CSI + "?5h")
            sys.stdout.flush()
            time.sleep(0.08)
            sys.stdout.write(CSI + "?5l")
            sys.stdout.flush()
            time.sleep(0.08)

        print("\n\033[92m ✓ Consolidation complete — morning brief ready.\033[0m")
        time.sleep(0.5)
        sys.stdout.write(CSI + "2J" + CSI + "H")
        sys.stdout.flush()

    def run(self):
        if not self.enabled:
            print("=" * 60)
            print("  ZOEY · awakening")
            print("=" * 60)
            time.sleep(0.4)
            return
        try:
            self.generate_memories(60)
            self.cluster_memories()
            self._run_animation()
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Shared queue + logger bridges engine (terminal) <-> chat web UI
# ---------------------------------------------------------------------------
_typed_input_queue: "queue.Queue[str]" = queue.Queue()


def _make_web_stats_bridge():
    """Return (report_stats_fn, get_stats_fn) sharing a dict across threads."""
    _stats_lock = threading.Lock()
    _latest = {}

    def report(stats):
        with _stats_lock:
            _latest.clear()
            _latest.update(stats or {})

    def get():
        with _stats_lock:
            return dict(_latest)

    return report, get


def _start_chat_server_in_thread(stop_event, muted_lock, muted_ref,
                                  stats_reporter_getter,
                                  status_setter, engine_log,
                                  supervisor_observer,
                                  route_event_cb):
    """Launch chat_app.ChatApp HTTP server in a background thread.

    Rather than let chat_app spin up its own engine, we replace its
    run_engine with a polling loop that reads the shared terminal log
    and state so the browser and console stay in sync.
    """
    import chat_app
    import config
    import tools

    host = getattr(config, "CHAT_HOST", "127.0.0.1")
    port = int(getattr(config, "CHAT_PORT", 8765))
    app = chat_app.ChatApp(host=host, port=port)

    # Override logging so the web UI sees every engine event.
    original_log = app.log

    def tee_log(message, level="info"):
        # Re-publish engine logs through the web app's event stream.
        if level in {"zoey", "user", "status"}:
            event_level = level
        else:
            event_level = "system"
        safe = chat_app.sanitize_terminal_text(str(message))
        with app.events_lock:
            app.events.append({"id": len(app.events) + 1,
                               "level": event_level, "text": safe})
            app.events = app.events[-200:]
        return original_log(message, level)

    app.log = tee_log
    tools.set_route_logger(route_event_cb)

    def should_mute():
        with muted_lock:
            return bool(muted_ref[0])

    def set_muted(v):
        with muted_lock:
            muted_ref[0] = bool(v)

    app.should_mute = should_mute
    app.set_muted = set_muted

    # Instead of chat_app.run_engine, we just poll stats + forward typed
    # messages from the browser to the engine's queue.
    def run_web_only():
        import json as _json
        next_status_ping = 0.0
        try:
            while not stop_event.is_set():
                # Drain typed messages queued from the browser into engine queue.
                while True:
                    try:
                        msg = app.queue.get_nowait()
                    except queue.Empty:
                        break
                    _typed_input_queue.put(msg)

                # Pump engine-side latest stats into the web app's stats dict.
                current = stats_reporter_getter()
                if current:
                    app.report_stats(current)

                now = time.time()
                if now > next_status_ping:
                    next_status_ping = now + 1.0
                time.sleep(0.15)
        except Exception as exc:
            engine_log(f"Web UI bridge stopped: {exc}", "warn")

    threading.Thread(target=run_web_only, daemon=True).start()

    def handler():
        H = chat_app.ChatApp.handler(app)
        # Patch the Handler so its POST /api/chat uses our shared queue too.
        # (already done above via app.queue → _typed_input_queue)
        return H

    from http.server import ThreadingHTTPServer
    server = ThreadingHTTPServer((app.host, app.port), handler())
    url = f"http://{app.host}:{app.port}"
    engine_log(f"Chat UI open: {url}", "info")
    try:
        import webbrowser
        webbrowser.open(url)
    except Exception:
        pass
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        stop_event.set()
        try:
            server.server_close()
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Main boot: dream → engine (terminal agent, main thread) + web UI (thread)
# ---------------------------------------------------------------------------
def main():
    # 1. Dream visualizer
    viz = DreamVisualizer()
    viz.run()

    # Shared mutable state between web UI thread and engine main thread.
    stop_event = threading.Event()
    muted_lock = threading.Lock()
    muted_ref = [False]
    report_stats, get_stats = _make_web_stats_bridge()

    # ---- Boot the web UI in background BEFORE engine so the URL banner lands.
    def engine_log(message, level="info"):
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        safe = str(message)
        try:
            safe_bytes = safe.encode("ascii", "ignore").decode("ascii")
        except Exception:
            safe_bytes = safe
        print(f"[{ts}] [{level}] {safe_bytes}", flush=True)

    import supervisor as _sup
    sup = _sup.Supervisor(engine_log)

    def observe(level, text):
        try:
            sup.observe(level, text)
        except Exception:
            pass

    last_reply_lock = threading.Lock()
    last_reply = {"text": "", "ts": 0.0}

    def observing_engine_log(message, level="info"):
        engine_log(message, level)
        if level == "zoey":
            with last_reply_lock:
                last_reply["text"] = str(message)
                last_reply["ts"] = time.time()
        if not (str(message) or "").startswith("AUTO_FIX"):
            observe(level, str(message))

    import tools as _tools

    def route_event(skill, tool_name, phase, detail):
        compact = str(detail).replace("\n", " ")
        if len(compact) > 180:
            compact = compact[:177] + "..."
        observing_engine_log(
            f"ROUTE {skill} -> {tool_name} [{phase}] {compact}", "info")

    _tools.set_route_logger(route_event)

    threading.Thread(
        target=_start_chat_server_in_thread,
        args=(stop_event, muted_lock, muted_ref,
              get_stats, None, observing_engine_log,
              observe, route_event),
        daemon=True,
    ).start()
    # Give the server a moment to bind so URL log line prints cleanly.
    time.sleep(0.45)

    # 2. Banner
    print("\033[95m" + "─" * 78 + "\033[0m")
    print("  \033[1m\033[95mZOEY\033[0m  ·  a mind growing  ·  one experience at a time")
    print("  Browser chat: \033[95mhttp://127.0.0.1:8765\033[0m   ·   type below, or speak (mic on = /mic on)")
    print("  Commands: /help   /status   /skills   /baby   /mute   /unmute   /quit")
    print("\033[95m" + "─" * 78 + "\033[0m\n")
    sys.stdout.flush()

    # 3. Terminal agent — input loop + engine.run both on main thread.
    #    engine.run already accepts typed_input_queue; we feed it from
    #    a background input reader so engine.run's mainloop can poll it.
    def stdin_reader():
        try:
            while not stop_event.is_set():
                try:
                    line = input("> ").strip()
                except (EOFError, KeyboardInterrupt):
                    stop_event.set()
                    break
                if not line:
                    continue
                cmd = line.lower()
                if cmd in {"/quit", "/exit"}:
                    stop_event.set()
                    break
                if cmd == "/help":
                    observing_engine_log(
                        "Commands: /quit, /mute, /unmute, /status, /skills, /baby, "
                        "/mic on|off|status, /offline on|off, /autofix on|off|status, "
                        "/fix <token>, /fixdeny <token>", "info")
                    continue
                if cmd == "/skills":
                    import skills as _sk
                    for item in _sk.catalog():
                        observing_engine_log(
                            f"SKILL {item['skill']}: "
                            f"{', '.join(item['tools']) or 'no tools'}", "info")
                    continue
                if cmd in {"/autofix", "/autofix status"}:
                    observing_engine_log(sup.status_text(), "info")
                    continue
                if cmd in {"/autofix on", "/autofix 1", "/autofix true"}:
                    sup.set_enabled(True)
                    observing_engine_log("AUTO_FIX: ON", "info")
                    continue
                if cmd in {"/autofix off", "/autofix 0", "/autofix false"}:
                    sup.set_enabled(False)
                    observing_engine_log("AUTO_FIX: OFF", "warn")
                    continue
                if cmd.startswith("/fixdeny "):
                    token = cmd.split(None, 1)[1].strip()
                    observing_engine_log(sup.deny_fix(token), "info")
                    continue
                if cmd.startswith("/fix "):
                    token = cmd.split(None, 1)[1].strip()
                    observing_engine_log(sup.approve_fix(token), "info")
                    continue
                if cmd == "/mute":
                    with muted_lock:
                        muted_ref[0] = True
                    observing_engine_log("Muted.", "warn")
                    continue
                if cmd == "/unmute":
                    with muted_lock:
                        muted_ref[0] = False
                    observing_engine_log("Unmuted.", "info")
                    continue
                if cmd == "/status":
                    # We don't know the engine status text here (it's inside
                    # engine.run). The user will see the real status via the
                    # periodic status log lines printed by engine itself.
                    s = get_stats()
                    if s:
                        observing_engine_log(
                            f"uptime={int(s.get('uptime_seconds', 0))}s "
                            f"brain_calls={s.get('brain_calls', 0)} "
                            f"tool_calls={s.get('tool_calls', 0)} "
                            f"model={s.get('last_model_used', '-')}", "info")
                    continue
                _typed_input_queue.put(line)
        except BaseException as exc:
            if not isinstance(exc, (EOFError, KeyboardInterrupt)):
                observing_engine_log(f"stdin reader stopped: {exc}", "error")
            stop_event.set()

    threading.Thread(target=stdin_reader, daemon=True).start()

    # 4. Engine — this is the real worker with voice, TTS, STT, tools, mind.
    import engine as _engine
    status_lock = threading.Lock()
    status_text = ["PASSIVE (Listening for wake word)"]

    def set_status(st):
        with status_lock:
            status_text[0] = str(st)
        observing_engine_log(f"STATUS: {st}", "info")

    def should_stop() -> bool:
        return stop_event.is_set()

    def should_mute() -> bool:
        with muted_lock:
            return bool(muted_ref[0])

    try:
        _engine.run(
            log=observing_engine_log,
            set_status=set_status,
            should_stop=should_stop,
            should_mute=should_mute,
            report_stats=report_stats,
            typed_input_queue=_typed_input_queue,
        )
    except KeyboardInterrupt:
        pass
    except BaseException as exc:
        try:
            observing_engine_log(f"Engine stopped: {exc}", "error")
            sup.report_uncaught(exc)
        except Exception:
            pass
    finally:
        stop_event.set()
        print("\n\033[92mUntil next time — Zoey will dream about this conversation.\033[0m",
              flush=True)


if __name__ == "__main__":
    main()
