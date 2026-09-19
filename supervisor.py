import collections
import json
import os
import re
import secrets
import threading
import time
import traceback

import api
import brain_store
import config
import tools


class Supervisor:
    def __init__(self, log):
        self._log = log
        self._enabled = bool(getattr(config, "AUTO_FIX_ENABLED", True))
        self._buf = collections.deque(maxlen=120)
        self._lock = threading.Lock()
        self._pending = {}
        self._worker = threading.Thread(target=self._loop, daemon=True)
        self._q = collections.deque()
        self._worker.start()

    def enabled(self) -> bool:
        return bool(self._enabled)

    def set_enabled(self, v: bool) -> None:
        self._enabled = bool(v)

    def observe(self, level: str, message: str) -> None:
        ts = time.time()
        lvl = (level or "").strip().lower()
        msg = (message or "").strip()
        with self._lock:
            self._buf.append({"ts": ts, "level": lvl, "msg": msg})
        if not self._enabled:
            return
        if lvl == "error" or "traceback" in msg.lower():
            self._enqueue({"type": "incident", "kind": "log", "detail": msg})

    def report_uncaught(self, exc: BaseException) -> None:
        tb = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
        self._enqueue({"type": "incident", "kind": "crash", "detail": tb})

    def approve_fix(self, token: str) -> str:
        t = (token or "").strip()
        if not t:
            return "Missing token."
        with self._lock:
            inc = self._pending.get(t)
        if not inc:
            return "No pending fix for that token."
        self._enqueue({"type": "online_help", "token": t})
        return "Okay. I'll ask for help and report back."

    def deny_fix(self, token: str) -> str:
        t = (token or "").strip()
        if not t:
            return "Missing token."
        with self._lock:
            if t in self._pending:
                self._pending.pop(t, None)
                return "Denied."
        return "No pending fix for that token."

    def status_text(self) -> str:
        with self._lock:
            n = len(self._pending)
        return f"AUTO_FIX={'ON' if self._enabled else 'OFF'} pending={n}"

    def _enqueue(self, item: dict) -> None:
        with self._lock:
            self._q.append(item)

    def _loop(self) -> None:
        while True:
            item = None
            with self._lock:
                if self._q:
                    item = self._q.popleft()
            if not item:
                time.sleep(0.15)
                continue
            try:
                t = item.get("type")
                if t == "incident":
                    self._handle_incident(item.get("kind", ""), item.get("detail", ""))
                elif t == "online_help":
                    self._handle_online_help(item.get("token", ""))
            except Exception as e:
                try:
                    self._log(f"AUTO_FIX internal error: {e}", "warn")
                except Exception:
                    pass

    def _context_text(self) -> str:
        with self._lock:
            rows = list(self._buf)
        lines = []
        for r in rows[-60:]:
            lvl = r.get("level", "")
            msg = r.get("msg", "")
            lines.append(f"[{lvl}] {msg}")
        return "\n".join(lines).strip()

    def _handle_incident(self, kind: str, detail: str) -> None:
        detail_s = (detail or "").strip()
        context = self._context_text()
        token = secrets.token_urlsafe(6)
        inc = {
            "token": token,
            "ts": time.time(),
            "kind": kind,
            "detail": detail_s[:4000],
            "context": context[:8000],
        }
        with self._lock:
            self._pending[token] = inc

        brain_store.add_error(error=f"{kind}: {detail_s[:1200]}", fix="", tags=["auto_fix"])
        self._attempt_local_fixes(inc)

        self._log(
            "AUTO_FIX detected an issue. Reply with: /fix "
            + token
            + " to let me ask online for help, or /fixdeny "
            + token
            + " to ignore.",
            "warn",
        )

    def _attempt_local_fixes(self, inc: dict) -> None:
        ctx = (inc.get("detail") or "") + "\n" + (inc.get("context") or "")
        ctx_low = ctx.lower()

        try:
            from skills import maintenance_skill

            stat = maintenance_skill._windows_memory_status()  # type: ignore[attr-defined]
            if stat:
                avail_mb = int(stat.get("avail_phys_bytes", 0)) // (1024 * 1024)
                min_mb = int(getattr(config, "AUTO_FIX_MIN_FREE_MB", 600))
                if avail_mb and avail_mb < min_mb:
                    res = tools.execute_tool(
                        "clean_temp",
                        {
                            "max_files": int(getattr(config, "AUTO_FIX_TEMP_MAX_FILES", 500)),
                            "min_age_days": int(getattr(config, "AUTO_FIX_TEMP_MIN_AGE_DAYS", 14)),
                        },
                    )
                    self._log(f"AUTO_FIX low memory ({avail_mb}MB free). {res}", "warn")
        except Exception:
            pass

        if "free-models-per-day" in ctx_low or "openrouter_free_tier_daily" in ctx_low:
            try:
                config.OFFLINE_MODE = True
                brain_store.add_lesson(
                    problem="OpenRouter rate limit triggered",
                    fix="Set OFFLINE_MODE=True to force local-only backend until rate limit resets.",
                    tags=["auto_fix", "openrouter"],
                )
                self._log("AUTO_FIX: OpenRouter rate-limited. Offline mode enabled (local-only).", "warn")
            except Exception:
                pass

        if "winerror 2" in ctx_low and "piper" in ctx_low:
            try:
                config.TTS_PROVIDER = "pyttsx3"
                brain_store.add_lesson(
                    problem="Piper WinError 2",
                    fix="Fallback to pyttsx3 and verify PIPER_EXE/PIPER_MODEL paths in .env/config.",
                    tags=["auto_fix", "tts"],
                )
                self._log("AUTO_FIX: Piper failed (WinError 2). Switched TTS_PROVIDER to pyttsx3.", "warn")
            except Exception:
                pass

        if "microphone error:" in ctx_low:
            try:
                config.MIC_ENABLED = False
                brain_store.add_lesson(
                    problem="Microphone error crash",
                    fix="Disable mic (MIC_ENABLED=False) and use typed input until audio device is fixed.",
                    tags=["auto_fix", "audio"],
                )
                self._log("AUTO_FIX: Microphone error detected. MIC_ENABLED set to False.", "warn")
            except Exception:
                pass

    def _call_brain_no_tools(self, messages: list[dict]) -> tuple[str, str]:
        client = api.make_client()
        local_enabled = bool(getattr(config, "LOCAL_BRAIN_ENABLED", False))
        local_first = bool(getattr(config, "LOCAL_BRAIN_FIRST", True))
        offline_mode = bool(getattr(config, "OFFLINE_MODE", False))

        models = []
        if local_enabled and local_first:
            models.append(("local", getattr(config, "LOCAL_BRAIN_MODEL", "llama3.2:1b-instruct")))
        if not offline_mode:
            for m in getattr(config, "FALLBACK_MODELS", []) or []:
                models.append(("online", m))
        if local_enabled and not local_first:
            models.append(("local", getattr(config, "LOCAL_BRAIN_MODEL", "llama3.2:1b-instruct")))

        last_err = None
        for mode, model in models:
            try:
                c = api.make_local_client() if mode == "local" else client
                resp = c.chat.completions.create(model=model, messages=messages)
                choice0 = resp.choices[0]
                content = (choice0.message.content or "").strip()
                return content, (f"local:{model}" if mode == "local" else model)
            except Exception as e:
                last_err = e
                continue
        raise RuntimeError(f"All models failed: {last_err}")

    def _handle_online_help(self, token: str) -> None:
        t = (token or "").strip()
        with self._lock:
            inc = self._pending.get(t)
        if not inc:
            return

        system = (
            "You are a senior Python engineer. Diagnose the error and propose a minimal fix. "
            "Output short steps and, if code changes are needed, include exact file+line hints. "
            "Do not ask questions unless required."
        )
        user = {
            "token": inc.get("token"),
            "kind": inc.get("kind"),
            "detail": inc.get("detail"),
            "context": inc.get("context"),
            "os": os.name,
        }
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": json.dumps(user, ensure_ascii=False)},
        ]
        try:
            reply, used = self._call_brain_no_tools(messages)
            self._log(f"AUTO_FIX online suggestion ({used}): {reply}", "info")
            brain_store.add_research(note=reply, source="online_debug", url="", tags=["auto_fix"])
        except Exception as e:
            self._log(f"AUTO_FIX online help failed: {e}", "warn")

