import queue
import threading
import time

import engine
import config
import phone_bridge
import supervisor


def run():
    stop_event = threading.Event()
    muted_lock = threading.Lock()
    muted = False
    typed_queue: "queue.Queue[str]" = queue.Queue()
    last_reply_lock = threading.Lock()
    last_reply = {"text": "", "ts": 0.0}
    latest_stats_lock = threading.Lock()
    latest_stats = {}
    status_lock = threading.Lock()
    status_text = ""
    bridge_server = None
    sup = None

    def log(message: str, level: str = "info"):
        ts = time.strftime("%H:%M:%S")
        print(f"[{ts}] [{level}] {message}", flush=True)
        if sup and not (message or "").startswith("AUTO_FIX"):
            try:
                sup.observe(level, message)
            except Exception:
                pass
        if level == "zoey":
            with last_reply_lock:
                last_reply["text"] = message
                last_reply["ts"] = time.time()

    sup = supervisor.Supervisor(log)

    def get_last_reply():
        with last_reply_lock:
            return dict(last_reply)

    def set_status(st: str):
        nonlocal status_text
        with status_lock:
            status_text = st
        log(f"STATUS: {st}", "info")

    def should_stop() -> bool:
        return stop_event.is_set()

    def should_mute() -> bool:
        with muted_lock:
            return muted

    def report_stats(stats: dict):
        nonlocal latest_stats
        with latest_stats_lock:
            latest_stats = dict(stats or {})

    def route_event(skill, tool_name, phase, detail):
        compact = str(detail).replace("\n", " ")
        if len(compact) > 180:
            compact = compact[:177] + "..."
        log(f"ROUTE {skill} -> {tool_name} [{phase}] {compact}", "route")

    import tools
    tools.set_route_logger(route_event)

    def engine_thread():
        try:
            engine.run(
                log=log,
                set_status=set_status,
                should_stop=should_stop,
                should_mute=should_mute,
                report_stats=report_stats,
                typed_input_queue=typed_queue,
            )
        except BaseException as e:
            try:
                log(f"Engine crashed: {e}", "error")
            except Exception:
                pass
            try:
                sup.report_uncaught(e)
            except Exception:
                pass

    t = threading.Thread(target=engine_thread, daemon=True)
    t.start()

    if getattr(config, "PHONE_BRIDGE_ENABLED", False):
        token = (getattr(config, "PHONE_BRIDGE_TOKEN", "") or "").strip()
        host = getattr(config, "PHONE_BRIDGE_HOST", "127.0.0.1")
        port = int(getattr(config, "PHONE_BRIDGE_PORT", 8765))
        if token:
            bridge_server = phone_bridge.start(
                host=host,
                port=port,
                token=token,
                enqueue_text=lambda txt: typed_queue.put(txt),
                get_last_reply=get_last_reply,
                log=log,
            )
        else:
            log("Phone bridge enabled but PHONE_BRIDGE_TOKEN is empty. Not starting bridge.", "warn")

    log('Type to chat. Commands: /quit, /mute, /unmute, /status, /help', "info")

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
            log("Commands: /quit, /mute, /unmute, /status, /skills, /autofix on|off|status, /fix <token>, /fixdeny <token>", "info")
            continue
        if cmd == "/skills":
            import skills
            for item in skills.catalog():
                log(f"SKILL {item['skill']}: {', '.join(item['tools']) or 'no tools'}", "info")
            continue
        if cmd in {"/autofix", "/autofix status"}:
            log(sup.status_text(), "info")
            continue
        if cmd in {"/autofix on", "/autofix 1", "/autofix true"}:
            sup.set_enabled(True)
            log("AUTO_FIX: ON", "info")
            continue
        if cmd in {"/autofix off", "/autofix 0", "/autofix false"}:
            sup.set_enabled(False)
            log("AUTO_FIX: OFF", "warn")
            continue
        if cmd.startswith("/fixdeny "):
            token = cmd.split(None, 1)[1].strip()
            log(sup.deny_fix(token), "info")
            continue
        if cmd.startswith("/fix "):
            token = cmd.split(None, 1)[1].strip()
            log(sup.approve_fix(token), "info")
            continue
        if cmd == "/mute":
            with muted_lock:
                muted = True
            log("Muted.", "warn")
            continue
        if cmd == "/unmute":
            with muted_lock:
                muted = False
            log("Unmuted.", "info")
            continue
        if cmd == "/status":
            with status_lock:
                st = status_text
            with latest_stats_lock:
                s = dict(latest_stats or {})
            log(f"{st}", "info")
            if s:
                log(
                    f"uptime={int(s.get('uptime_seconds', 0))}s brain_calls={s.get('brain_calls', 0)} tool_calls={s.get('tool_calls', 0)} model={s.get('last_model_used', '-')}",
                    "info",
                )
            continue

        typed_queue.put(line)

    if bridge_server:
        try:
            bridge_server.shutdown()
            bridge_server.server_close()
        except Exception:
            pass

    t.join(timeout=2.0)


if __name__ == "__main__":
    run()
