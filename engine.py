"""
ZOEY — engine.py
Execution engine with voice + typed input, tool calling, and safe fallbacks.
"""

import queue
import time
import re
import datetime
import api
import audio
import config
import brain_store
import data_store
import json
import tools
import confidence
import zoey_dreams
import growing_brain
import cellular_brain
import world_model
import baby_zoey
import mind


def run(
    log=None,
    set_status=None,
    should_stop=None,
    should_mute=None,
    report_stats=None,
    typed_input_queue=None,
    **kwargs,
):
    """Main execution loop for ZOEY connected to TUI."""
    def _log(msg, level="info"):
        safe_msg = msg
        try:
            safe_msg = msg.encode("ascii", "ignore").decode("ascii")
        except Exception:
            safe_msg = str(msg)
        if log:
            log(safe_msg, level)
        else:
            print(f"[{level}] {safe_msg}")

    def _set_status(st):
        if set_status:
            set_status(st)

    # Sidebar usage stats tracking
    start_time = time.time()
    brain_calls = 0
    tool_calls = 0
    last_model_used = "-"
    def _mic_enabled() -> bool:
        return bool(getattr(config, "MIC_ENABLED", True))

    def _report(mic_level=0.0):
        if report_stats:
            mic_on = _mic_enabled()
            report_stats({
                "uptime_seconds": time.time() - start_time,
                "brain_calls": brain_calls,
                "tool_calls": tool_calls,
                "tts_provider": getattr(config, "TTS_PROVIDER", "elevenlabs"),
                "whisper_model": getattr(config, "WHISPER_MODEL_SIZE", "base") if mic_on else "disabled",
                "mic_device": audio.get_mic_name() if mic_on else "disabled",
                "mic_level": mic_level,
                "last_model_used": last_model_used,
                "mute": should_mute() if should_mute else False,
            })

    # Initialize engines
    pyttsx3_engine = audio.load_tts_engine()
    whisper_model = audio.load_whisper_model() if _mic_enabled() else None
    client = api.make_client()

    use_short_system = bool(getattr(config, "LOCAL_BRAIN_ENABLED", False)) and bool(
        getattr(config, "LOCAL_BRAIN_FIRST", False)
    )
    system_base = (
        getattr(config, "SYSTEM_PROMPT_TEMPLATE_SHORT", "").strip()
        if use_short_system
        else getattr(config, "SYSTEM_PROMPT_TEMPLATE", "").strip()
    )
    try:
        user_data = data_store.get_user_data()
        zoey_data = data_store.get_zoey_data()
    except Exception:
        user_data = {}
        zoey_data = {}
    brain_context = ""
    try:
        brain_context = brain_store.build_context(limit_per_file=3)
    except Exception:
        brain_context = ""
    system_runtime = (
        "This machine is Windows. Use Windows paths (e.g. C:\\Users\\... or ~\\Downloads). Never use Linux paths like /home/... .\n"
        f"Today's date is {datetime.date.today().isoformat()}. For current or today's news, use this date and verify with web_search.\n"
        "For a news request, search once or twice, then summarize the collected results. Do not keep calling web_search after you have usable sources.\n"
        "Keep replies concise unless the user asks for detail.\n"
        "If a tool returns APPROVAL_REQUIRED with a token, ask the user to approve (/approve <token>) or deny (/deny <token>), then call the relevant approve/deny tool.\n"
        "For multi-step goals, write a short numbered plan, then execute step-by-step, confirming before risky actions.\n"
        + mind.IDENTITY_BLOCK
        + "\n"
    ).strip()
    injected = []
    if user_data:
        minimal_user = {
            "preferred_name": user_data.get("preferred_name"),
            "name": user_data.get("name"),
            "birthday": user_data.get("birthday"),
            "nationality": user_data.get("nationality"),
            "languages": user_data.get("languages"),
            "core_values": user_data.get("core_values"),
            "long_term_goals": user_data.get("long_term_goals"),
            "communication_preferences": user_data.get("communication_preferences"),
        }
        injected.append("User profile (local):\n" + json.dumps(minimal_user, ensure_ascii=False))
    if zoey_data:
        minimal_zoey = {
            "name": zoey_data.get("name"),
            "identity_rules": zoey_data.get("identity_rules"),
            "style_rules": zoey_data.get("style_rules"),
        }
        injected.append("Zoey identity rules (local):\n" + json.dumps(minimal_zoey, ensure_ascii=False))
    if brain_context:
        injected.append("Brain context (recent lessons/errors/memory):\n" + brain_context)
    injection_block = "\n\n".join(injected).strip()
    system_prompt = "\n\n".join([x for x in [system_base, injection_block, system_runtime] if x]).strip()

    messages = [
        {
            "role": "system",
            "content": system_prompt,
        }
    ]

    def _strip_emojis(s: str) -> str:
        if not s:
            return s
        try:
            return re.sub(r"[\U0001F300-\U0001FAFF\U00002700-\U000027BF]", "", s)
        except Exception:
            return s

    def _sanitize_reply(user_prompt: str, reply: str) -> str:
        r = (reply or "").strip()
        if not r:
            return r
        r = r.replace("[Your Name]", "Zoey")
        r = _strip_emojis(r)
        r = mind.sanitize_identity(r)
        up = (user_prompt or "").lower()
        if "what is ur name" in up or "what is your name" in up or "your name" in up:
            if "no name" in r.lower() or "language model" in r.lower() or "gemma" in r.lower():
                return "My name is Zoey."
        return r.strip()

    def _trim_chat_history():
        max_msgs = int(getattr(config, "MAX_CHAT_MESSAGES", 32))
        if max_msgs < 4:
            max_msgs = 4
        if len(messages) <= max_msgs:
            return
        messages[:] = [messages[0]] + messages[-(max_msgs - 1) :]

    state = "PASSIVE"
    last_active_time = 0.0
    current_player = None

    def _dream_on_sleep(reason: str) -> None:
        try:
            result = zoey_dreams.dream_cycle()
            _log(
                f"Dream cycle ({reason}): {result['memories_seen']} memories, "
                f"{result['insights_created']} new insights.",
                "info",
            )
        except Exception as exc:
            _log(f"Dream cycle failed: {exc}", "warn")

    wake_words = getattr(config, "WAKE_WORDS", ["hey", "zoey", "hi zoey", "soey", "zoe", "wake up"])
    sleep_words = getattr(config, "SLEEP_WORDS", ["go to sleep", "sleep", "stop listening", "shut up", "bye", "goodbye"])
    active_timeout = getattr(config, "ACTIVE_TIMEOUT", 60.0)

    _set_status("PASSIVE (Listening for wake word)")
    mic_on = _mic_enabled()
    _log(
        "ZOEY Engine initialized. Say a wake word or type below!"
        if mic_on
        else "ZOEY Engine initialized. Mic disabled. Type below!",
        "info",
    )

    while True:
        if should_stop and should_stop():
            break

        _report(mic_level=0.0)
        current_time = time.time()

        # 1. AUTO-SLEEP: Go back to sleep only after 60s of silence
        if state == "ACTIVE" and (current_time - last_active_time > active_timeout):
            state = "PASSIVE"
            _set_status("PASSIVE (Listening for wake word)")
            _log("💤 [60s Timeout: ZOEY went back to sleep. Say a wake word to activate]", "warn")
            _dream_on_sleep("timeout")

        # 2. CHECK TYPED INPUT
        typed_text = None
        if typed_input_queue:
            try:
                typed_text = typed_input_queue.get_nowait()
            except queue.Empty:
                typed_text = None

        text = ""
        if typed_text:
            text = typed_text.strip()
            _log(f'⌨️ Typed: "{text}"', "user")
        else:
            if not _mic_enabled():
                time.sleep(0.05)
                continue
            if whisper_model is None:
                try:
                    whisper_model = audio.load_whisper_model()
                except Exception as e:
                    config.MIC_ENABLED = False
                    whisper_model = None
                    _log(f"Mic failed to start: {e}", "error")
                    time.sleep(0.2)
                    continue

            def level_cb(lvl):
                _report(mic_level=lvl)

            text = audio.record_and_transcribe(
                whisper_model, duration_seconds=3.0, level_callback=level_cb
            )

        if not text:
            continue

        if not typed_text:
            _log(f'🎤 Heard: "{text}"', "user")

        if typed_text:
            t = text.strip().lower()
            if t in {"/offline", "/offline on", "/offline 1", "/offline true"}:
                config.OFFLINE_MODE = True
                _log("Offline mode: ON (local-only, no internet backends).", "info")
                continue
            if t in {"/offline off", "/offline 0", "/offline false", "/online"}:
                config.OFFLINE_MODE = False
                _log("Offline mode: OFF (online backends allowed).", "info")
                continue
            if t in {"/mic", "/mic status"}:
                mic_on = _mic_enabled()
                name = audio.get_mic_name() if mic_on else "disabled"
                _log(f"Mic: {'ON' if mic_on else 'OFF'} ({name}).", "info")
                continue
            if t in {"/mic on", "/mic 1", "/mic true"}:
                config.MIC_ENABLED = True
                if whisper_model is None:
                    try:
                        whisper_model = audio.load_whisper_model()
                    except Exception as e:
                        config.MIC_ENABLED = False
                        _log(f"Mic failed to start: {e}", "error")
                        continue
                _set_status("PASSIVE (Listening for wake word)")
                _log(f"Mic: ON ({audio.get_mic_name()}).", "info")
                continue
            if t in {"/mic off", "/mic 0", "/mic false"}:
                config.MIC_ENABLED = False
                whisper_model = None
                _set_status("PASSIVE (Listening for wake word)")
                _log("Mic: OFF (typed input only).", "info")
                continue
            if t in {"/time", "/now"}:
                reply_text = tools.execute_tool("get_current_time", {})
                reply_text = _sanitize_reply(text, reply_text)
                _log(f"{reply_text}", "zoey")
                is_muted = should_mute() if should_mute else False
                audio.speak(pyttsx3_engine, reply_text, mute=is_muted, log=_log)
                continue
            if t in {"/baby", "/baby state", "/baby stats"}:
                try:
                    state = baby_zoey.get_state()
                    growing = state.get("growing", {}) or {}
                    symbolic = state.get("symbolic", {}) or {}
                    cellular = state.get("cellular", {}) or {}
                    world = state.get("world", {}) or {}
                    exp = growing.get("experiences", 0)
                    neurons = len(growing.get("neurons", []))
                    rules = symbolic.get("rule_count", len(symbolic.get("rules", [])))
                    gen = cellular.get("generation", 0)
                    observed = world.get("observations", 0)
                    surprise = world.get("surprise", 0.0) if isinstance(world.get("surprise", 0.0), (int, float)) else 0.0
                    stage = "🆕 Newborn"
                    if exp >= 500:
                        stage = "🎓 Young Adult"
                    elif exp >= 200:
                        stage = "🧒 Child"
                    elif exp >= 50:
                        stage = "🧒 Toddler"
                    elif exp >= 10:
                        stage = "👶 Infant"
                    reply_text = (
                        f"Zoey learning report\n"
                        f"Stage: {stage}\n"
                        f"Growing Brain: {exp} experiences, {neurons} neurons\n"
                        f"Symbolic Rules: {rules} learned\n"
                        f"Cellular Brain: Gen {gen}, {cellular.get('learned_rules', 0)} patterns\n"
                        f"World Model: {observed} observations, surprise={surprise:.3f}\n"
                        f"Thresholds: HIGH>={baby_zoey.CONFIDENCE_THRESHOLD_HIGH}, LOW>={baby_zoey.CONFIDENCE_THRESHOLD_LOW}"
                    )
                except Exception as bz_err:
                    reply_text = f"Baby state unavailable: {bz_err}"
                _log(f"{reply_text}", "zoey")
                is_muted = should_mute() if should_mute else False
                audio.speak(pyttsx3_engine, reply_text, mute=is_muted, log=_log)
                continue
            if t in {"/baby reset", "/baby-reset"}:
                try:
                    reset_res = baby_zoey.reset_learning()
                    reply_text = f"🍼 {reset_res.get('message','Baby reset done.')} Deleted {len(reset_res.get('deleted_files', []))} memory files."
                except Exception as bz_err:
                    reply_text = f"Baby reset failed: {bz_err}"
                _log(f"{reply_text}", "zoey")
                is_muted = should_mute() if should_mute else False
                audio.speak(pyttsx3_engine, reply_text, mute=is_muted, log=_log)
                continue
            if t in {"/skills", "/tools"}:
                import skills as _skills
                cat = _skills.catalog()
                parts = [f"Loaded {len(tools.TOOL_DEFINITIONS)} tools across {len(cat)} skills:"]
                for sk in cat:
                    parts.append(f"  • [{sk['skill']}] {', '.join(sk['tools']) if sk['tools'] else '(empty)'}")
                reply_text = "\n".join(parts)
                _log(f"{reply_text}", "zoey")
                is_muted = should_mute() if should_mute else False
                audio.speak(pyttsx3_engine, "Loaded " + str(len(tools.TOOL_DEFINITIONS)) + " tools across " + str(len(cat)) + " skills.", mute=is_muted, log=_log)
                continue

        prompt_to_send = None

        # 4. PASSIVE STATE LOGIC
        if state == "PASSIVE":
            if typed_text or any(w in text.lower() for w in wake_words):
                state = "ACTIVE"
                last_active_time = time.time()
                _set_status("ACTIVE (Awake)")
                _log("✨ [ZOEY is now AWAKE]", "info")

                if typed_text:
                    prompt_to_send = text
                else:
                    cleaned_prompt = text.lower()
                    for w in wake_words:
                        cleaned_prompt = cleaned_prompt.replace(w, "").strip()

                    if cleaned_prompt:
                        prompt_to_send = cleaned_prompt
                    else:
                        is_muted = should_mute() if should_mute else False
                        audio.speak(pyttsx3_engine, "Yes?", mute=is_muted, log=_log)
                        last_active_time = time.time()
                        continue
            else:
                continue

        # 5. ACTIVE STATE LOGIC
        elif state == "ACTIVE":
            if any(s in text.lower() for s in sleep_words):
                state = "PASSIVE"
                _set_status("PASSIVE (Listening for wake word)")
                _log("💤 [Sleep word detected. ZOEY is going to sleep]", "warn")
                _dream_on_sleep("sleep word")
                is_muted = should_mute() if should_mute else False
                audio.speak(pyttsx3_engine, "Going to sleep now.", mute=is_muted, log=_log)
                continue

            prompt_to_send = text

        # 6. PROCESS PROMPT WITH BRAIN
        if prompt_to_send:
            prompt_to_send = mind.normalize_user_text(prompt_to_send)
            lower_prompt = (prompt_to_send or "").strip().lower()
            for a, b in [
                ("vulme", "volume"),
                ("volme", "volume"),
                ("voume", "volume"),
                ("voulme", "volume"),
                ("dowwn", "down"),
                ("openn", "open"),
                ("opne", "open"),
            ]:
                lower_prompt = re.sub(rf"\b{re.escape(a)}\b", b, lower_prompt)

            if mind.is_file_request(prompt_to_send):
                res = tools.execute_tool(
                    "run_needle2_file_agent",
                    {"query": mind.file_query(prompt_to_send)},
                )
                reply_text = _sanitize_reply(prompt_to_send, mind.speak_files(res))
                last_model_used = "tool:run_needle2_file_agent"
                brain_calls += 1
                _log(f"{reply_text}", "zoey")
                messages.append({"role": "assistant", "content": reply_text})
                _set_status("SPEAKING...")
                is_muted = should_mute() if should_mute else False
                audio.speak(pyttsx3_engine, reply_text, mute=is_muted, log=_log)
                state = "ACTIVE"
                last_active_time = time.time()
                continue

            if "i'm on youtube music" in lower_prompt or "im on youtube music" in lower_prompt or "i am on youtube music" in lower_prompt:
                current_player = "youtube_music"
            if "i'm on aimp" in lower_prompt or "im on aimp" in lower_prompt or "i am on aimp" in lower_prompt:
                current_player = "aimp"
            if any(x in lower_prompt for x in ["what time", "time now", "current time", "wht is the time"]):
                reply_text = tools.execute_tool("get_current_time", {})
                reply_text = _sanitize_reply(prompt_to_send, reply_text)
                last_model_used = "tool:get_current_time"
                brain_calls += 1
                _log(f"{reply_text}", "zoey")
                messages.append({"role": "assistant", "content": reply_text})
                _set_status("SPEAKING...")
                is_muted = should_mute() if should_mute else False
                audio.speak(pyttsx3_engine, reply_text, mute=is_muted, log=_log)
                state = "ACTIVE"
                last_active_time = time.time()
                continue

            if "what is my name" in lower_prompt or "my name" in lower_prompt:
                preferred = None
                try:
                    preferred = data_store.get_user_value("preferred_name") or data_store.get_user_value("name")
                except Exception:
                    preferred = None
                if preferred:
                    reply_text = f"Your name is {preferred}."
                    reply_text = _sanitize_reply(prompt_to_send, reply_text)
                    last_model_used = "tool:get_user_profile"
                    brain_calls += 1
                    _log(f"{reply_text}", "zoey")
                    messages.append({"role": "assistant", "content": reply_text})
                    _set_status("SPEAKING...")
                    is_muted = should_mute() if should_mute else False
                    audio.speak(pyttsx3_engine, reply_text, mute=is_muted, log=_log)
                    state = "ACTIVE"
                    last_active_time = time.time()
                    continue

            if any(x in lower_prompt for x in ["open browser", "open chrome", "open the browser", "chrome)"]):
                res = tools.execute_tool("open_app", {"app_name": "chrome"})
                reply_text = "Opening Chrome." if "Opened" in (res or "") else f"Couldn't open Chrome: {res}"
                reply_text = _sanitize_reply(prompt_to_send, reply_text)
                last_model_used = "tool:open_app"
                brain_calls += 1
                _log(f"{reply_text}", "zoey")
                messages.append({"role": "assistant", "content": reply_text})
                _set_status("SPEAKING...")
                is_muted = should_mute() if should_mute else False
                audio.speak(pyttsx3_engine, reply_text, mute=is_muted, log=_log)
                state = "ACTIVE"
                last_active_time = time.time()
                continue

            m_vol_up = re.search(r"(?:volume|sound)\s+up(?:\s+by\s+(\d{1,3})\s*%?)?", lower_prompt)
            if m_vol_up or any(x in lower_prompt for x in ["increase volume", "louder"]):
                pct = None
                if m_vol_up:
                    try:
                        pct = int(m_vol_up.group(1)) if m_vol_up.group(1) else None
                    except Exception:
                        pct = None
                steps = 1
                if pct is not None:
                    steps = max(1, min(50, int(round(pct / 2.0))))
                res = tools.execute_tool("volume_up", {"steps": steps})
                reply_text = _sanitize_reply(prompt_to_send, res)
                last_model_used = "tool:volume_up"
                brain_calls += 1
                _log(f"{reply_text}", "zoey")
                messages.append({"role": "assistant", "content": reply_text})
                _set_status("SPEAKING...")
                is_muted = should_mute() if should_mute else False
                audio.speak(pyttsx3_engine, reply_text, mute=is_muted, log=_log)
                state = "ACTIVE"
                last_active_time = time.time()
                continue

            m_vol_down = re.search(r"(?:volume|sound)\s+down(?:\s+by\s+(\d{1,3})\s*%?)?", lower_prompt)
            if m_vol_down or any(x in lower_prompt for x in ["decrease volume", "quieter"]):
                pct = None
                if m_vol_down:
                    try:
                        pct = int(m_vol_down.group(1)) if m_vol_down.group(1) else None
                    except Exception:
                        pct = None
                steps = 1
                if pct is not None:
                    steps = max(1, min(50, int(round(pct / 2.0))))
                res = tools.execute_tool("volume_down", {"steps": steps})
                reply_text = _sanitize_reply(prompt_to_send, res)
                last_model_used = "tool:volume_down"
                brain_calls += 1
                _log(f"{reply_text}", "zoey")
                messages.append({"role": "assistant", "content": reply_text})
                _set_status("SPEAKING...")
                is_muted = should_mute() if should_mute else False
                audio.speak(pyttsx3_engine, reply_text, mute=is_muted, log=_log)
                state = "ACTIVE"
                last_active_time = time.time()
                continue

            if any(x in lower_prompt for x in ["next song", "next track", "skip", "skip song"]):
                res = tools.execute_tool("next_track", {})
                reply_text = _sanitize_reply(prompt_to_send, res)
                last_model_used = "tool:next_track"
                brain_calls += 1
                _log(f"{reply_text}", "zoey")
                messages.append({"role": "assistant", "content": reply_text})
                _set_status("SPEAKING...")
                is_muted = should_mute() if should_mute else False
                audio.speak(pyttsx3_engine, reply_text, mute=is_muted, log=_log)
                state = "ACTIVE"
                last_active_time = time.time()
                continue

            if any(x in lower_prompt for x in ["previous song", "prev song", "previous track", "prev track", "go back song"]):
                res = tools.execute_tool("previous_track", {})
                reply_text = _sanitize_reply(prompt_to_send, res)
                last_model_used = "tool:previous_track"
                brain_calls += 1
                _log(f"{reply_text}", "zoey")
                messages.append({"role": "assistant", "content": reply_text})
                _set_status("SPEAKING...")
                is_muted = should_mute() if should_mute else False
                audio.speak(pyttsx3_engine, reply_text, mute=is_muted, log=_log)
                state = "ACTIVE"
                last_active_time = time.time()
                continue

            if any(x in lower_prompt for x in ["play pause", "pause", "resume", "play music"]):
                res = tools.execute_tool("play_pause", {})
                reply_text = _sanitize_reply(prompt_to_send, res)
                last_model_used = "tool:play_pause"
                brain_calls += 1
                _log(f"{reply_text}", "zoey")
                messages.append({"role": "assistant", "content": reply_text})
                _set_status("SPEAKING...")
                is_muted = should_mute() if should_mute else False
                audio.speak(pyttsx3_engine, reply_text, mute=is_muted, log=_log)
                state = "ACTIVE"
                last_active_time = time.time()
                continue

            if any(x in lower_prompt for x in ["what is playing", "what's playing", "now playing", "current song", "song name"]):
                if current_player == "youtube_music":
                    res = "I can't read the current song name from YouTube Music yet."
                else:
                    res = tools.execute_tool("get_now_playing", {})
                reply_text = _sanitize_reply(prompt_to_send, res)
                last_model_used = "tool:get_now_playing"
                brain_calls += 1
                _log(f"{reply_text}", "zoey")
                messages.append({"role": "assistant", "content": reply_text})
                _set_status("SPEAKING...")
                is_muted = should_mute() if should_mute else False
                audio.speak(pyttsx3_engine, reply_text, mute=is_muted, log=_log)
                state = "ACTIVE"
                last_active_time = time.time()
                continue

            if any(x in lower_prompt for x in ["what music", "music open", "music playing", "music right now"]):
                if current_player == "youtube_music":
                    res = "I can't read the current song name from YouTube Music yet."
                else:
                    res = tools.execute_tool("get_now_playing", {})
                reply_text = _sanitize_reply(prompt_to_send, res)
                last_model_used = "tool:get_now_playing"
                brain_calls += 1
                _log(f"{reply_text}", "zoey")
                messages.append({"role": "assistant", "content": reply_text})
                _set_status("SPEAKING...")
                is_muted = should_mute() if should_mute else False
                audio.speak(pyttsx3_engine, reply_text, mute=is_muted, log=_log)
                state = "ACTIVE"
                last_active_time = time.time()
                continue

            if "open settings" in lower_prompt or lower_prompt.strip() == "settings":
                res = tools.execute_tool("open_app", {"app_name": "ms-settings:"})
                reply_text = "Opening Settings." if "Opened" in (res or "") else f"Couldn't open Settings: {res}"
                reply_text = _sanitize_reply(prompt_to_send, reply_text)
                last_model_used = "tool:open_app"
                brain_calls += 1
                _log(f"{reply_text}", "zoey")
                messages.append({"role": "assistant", "content": reply_text})
                _set_status("SPEAKING...")
                is_muted = should_mute() if should_mute else False
                audio.speak(pyttsx3_engine, reply_text, mute=is_muted, log=_log)
                state = "ACTIVE"
                last_active_time = time.time()
                continue

            if "open aimp" in lower_prompt or "open the aimp" in lower_prompt:
                res1 = tools.execute_tool("open_aimp", {})
                current_player = "aimp"
                if "play" in lower_prompt:
                    res2 = tools.execute_tool("start_aimp_playback", {})
                    res = f"{res1} {res2}".strip()
                else:
                    res = res1
                reply_text = _sanitize_reply(prompt_to_send, res)
                last_model_used = "tool:open_aimp"
                brain_calls += 1
                _log(f"{reply_text}", "zoey")
                messages.append({"role": "assistant", "content": reply_text})
                _set_status("SPEAKING...")
                is_muted = should_mute() if should_mute else False
                audio.speak(pyttsx3_engine, reply_text, mute=is_muted, log=_log)
                state = "ACTIVE"
                last_active_time = time.time()
                continue

            if re.search(r"(?:volume|sound)\s+down\s+to\s+(?:0|zero)\b", lower_prompt) and "mute" in lower_prompt:
                _ = tools.execute_tool("volume_down", {"steps": 50})
                res = tools.execute_tool("volume_mute", {})
                reply_text = _sanitize_reply(prompt_to_send, res)
                last_model_used = "tool:volume_mute"
                brain_calls += 1
                _log(f"{reply_text}", "zoey")
                messages.append({"role": "assistant", "content": reply_text})
                _set_status("SPEAKING...")
                is_muted = should_mute() if should_mute else False
                audio.speak(pyttsx3_engine, reply_text, mute=is_muted, log=_log)
                state = "ACTIVE"
                last_active_time = time.time()
                continue

            if lower_prompt.strip() == "mute" or lower_prompt.endswith(" mute") or " mute " in lower_prompt:
                res = tools.execute_tool("volume_mute", {})
                reply_text = _sanitize_reply(prompt_to_send, res)
                last_model_used = "tool:volume_mute"
                brain_calls += 1
                _log(f"{reply_text}", "zoey")
                messages.append({"role": "assistant", "content": reply_text})
                _set_status("SPEAKING...")
                is_muted = should_mute() if should_mute else False
                audio.speak(pyttsx3_engine, reply_text, mute=is_muted, log=_log)
                state = "ACTIVE"
                last_active_time = time.time()
                continue

            if "aimp" in lower_prompt and "play" in lower_prompt and ("playlist" in lower_prompt or '"' in lower_prompt or "'" in lower_prompt):
                reply_text = _sanitize_reply(
                    prompt_to_send,
                    "I can open AIMP and control next/previous/play/pause, but I can't search your AIMP playlist for a specific song yet.",
                )
                last_model_used = "local:rule"
                brain_calls += 1
                _log(f"{reply_text}", "zoey")
                messages.append({"role": "assistant", "content": reply_text})
                _set_status("SPEAKING...")
                is_muted = should_mute() if should_mute else False
                audio.speak(pyttsx3_engine, reply_text, mute=is_muted, log=_log)
                state = "ACTIVE"
                last_active_time = time.time()
                continue

            if ("close" in lower_prompt or "exit" in lower_prompt or "quit" in lower_prompt) and "youtube" in lower_prompt and "music" in lower_prompt and ("open aimp" in lower_prompt or "open the aimp" in lower_prompt):
                res_close = tools.execute_tool("close_app", {"app_name": "YouTube Music"})
                res_open = tools.execute_tool("open_aimp", {})
                current_player = "aimp"
                res_play = ""
                if "play" in lower_prompt:
                    res_play = tools.execute_tool("start_aimp_playback", {})
                combo = " ".join([x for x in [res_close, res_open, res_play] if x]).strip()
                reply_text = _sanitize_reply(prompt_to_send, combo or "Done.")
                last_model_used = "tool:combo"
                brain_calls += 1
                _log(f"{reply_text}", "zoey")
                messages.append({"role": "assistant", "content": reply_text})
                _set_status("SPEAKING...")
                is_muted = should_mute() if should_mute else False
                audio.speak(pyttsx3_engine, reply_text, mute=is_muted, log=_log)
                state = "ACTIVE"
                last_active_time = time.time()
                continue

            m = re.search(
                r"(?:^|\b)(?:open|start)\s+(?:the\s+)?youtube\s+music(?:\s+(?:and\s+)?)?(?:play\s+)?(.+)?$",
                lower_prompt,
            )
            if m and "youtube" in lower_prompt and "music" in lower_prompt:
                query = (m.group(1) or "").strip()
                if query:
                    res = tools.execute_tool("play_youtube_music", {"query": query})
                    last_model_used = "tool:play_youtube_music"
                else:
                    res = tools.execute_tool("open_youtube_music", {})
                    last_model_used = "tool:open_youtube_music"
                current_player = "youtube_music"
                reply_text = res or "Done."
                reply_text = _sanitize_reply(prompt_to_send, reply_text)
                brain_calls += 1
                _log(f"{reply_text}", "zoey")
                messages.append({"role": "assistant", "content": reply_text})
                _set_status("SPEAKING...")
                is_muted = should_mute() if should_mute else False
                audio.speak(pyttsx3_engine, reply_text, mute=is_muted, log=_log)
                state = "ACTIVE"
                last_active_time = time.time()
                continue

            if any(x in lower_prompt for x in ["close", "exit", "quit", "stop"]) and "youtu" in lower_prompt and "music" in lower_prompt:
                res = tools.execute_tool("close_app", {"app_name": "YouTube Music"})
                reply_text = res or "I couldn't close YouTube Music."
                reply_text = _sanitize_reply(prompt_to_send, reply_text)
                last_model_used = "tool:close_app"
                brain_calls += 1
                _log(f"{reply_text}", "zoey")
                messages.append({"role": "assistant", "content": reply_text})
                _set_status("SPEAKING...")
                is_muted = should_mute() if should_mute else False
                audio.speak(pyttsx3_engine, reply_text, mute=is_muted, log=_log)
                if "Closed" in (res or ""):
                    if current_player == "youtube_music":
                        current_player = None
                state = "ACTIVE"
                last_active_time = time.time()
                continue

            if any(x in lower_prompt for x in ["close", "exit", "quit"]) and "chrome" in lower_prompt:
                res = tools.execute_tool("close_app", {"app_name": "Chrome"})
                reply_text = res or "I couldn't close Chrome."
                reply_text = _sanitize_reply(prompt_to_send, reply_text)
                last_model_used = "tool:close_app"
                brain_calls += 1
                _log(f"{reply_text}", "zoey")
                messages.append({"role": "assistant", "content": reply_text})
                _set_status("SPEAKING...")
                is_muted = should_mute() if should_mute else False
                audio.speak(pyttsx3_engine, reply_text, mute=is_muted, log=_log)
                state = "ACTIVE"
                last_active_time = time.time()
                continue

            if any(x in lower_prompt for x in ["close", "exit", "quit"]) and "edge" in lower_prompt:
                res = tools.execute_tool("close_app", {"app_name": "Edge"})
                reply_text = res or "I couldn't close Edge."
                reply_text = _sanitize_reply(prompt_to_send, reply_text)
                last_model_used = "tool:close_app"
                brain_calls += 1
                _log(f"{reply_text}", "zoey")
                messages.append({"role": "assistant", "content": reply_text})
                _set_status("SPEAKING...")
                is_muted = should_mute() if should_mute else False
                audio.speak(pyttsx3_engine, reply_text, mute=is_muted, log=_log)
                state = "ACTIVE"
                last_active_time = time.time()
                continue

            messages.append({"role": "user", "content": prompt_to_send})
            _trim_chat_history()

            # ---- BABY ZOEY FIRST: Think with local learning systems ----
            baby_result = None
            used_baby_shortcut = False
            try:
                baby_result = baby_zoey.think(prompt_to_send)
                _log(
                    f"mind: source={baby_result.get('source')}, "
                    f"confidence={baby_result.get('confidence', 0.0):.2f}",
                    "info",
                )
            except Exception as baby_err:
                _log(f"Baby ZOEY think() skipped: {baby_err}", "warn")
                baby_result = None

            # Feature vector used by world_model + learning updates
            feature_words = re.findall(r"[a-zA-Z][a-zA-Z0-9']{3,}", prompt_to_send.lower())

            # Baby ZOEY fast-path: use local response directly if confident
            if baby_result and baby_result.get("response"):
                b_source = baby_result.get("source", "")
                b_conf = float(baby_result.get("confidence", 0.0) or 0.0)
                b_resp = baby_result["response"]

                # HIGH confidence local_symbolic: fully autonomous response
                if b_source == "local_symbolic" and b_conf >= baby_zoey.CONFIDENCE_THRESHOLD_HIGH:
                    reply_text = _sanitize_reply(prompt_to_send, b_resp)
                    used_model = f"baby:{b_source} ({b_conf:.2f})"
                    response_confidence, confidence_reason = confidence.estimate(prompt_to_send, reply_text)
                    brain_store.record_confidence(prompt_to_send, reply_text, response_confidence, confidence_reason)
                    reward = (response_confidence * 2.0) - 1.0
                    try:
                        growing_brain.experience(features=feature_words[:8], reward=reward, confused=False)
                        cellular_brain.experience(reward=reward)
                    except Exception as _ge:
                        _log(f"Brain post-update (baby local) skipped: {_ge}", "warn")
                    last_model_used = used_model
                    brain_calls += 1
                    _log(f"{reply_text}", "zoey")
                    messages.append({"role": "assistant", "content": reply_text})
                    try:
                        brain_store.remember(
                            text=f"User: {prompt_to_send}\nZoey (baby local): {reply_text}",
                            tags=["conversation", "baby_local"],
                            source="engine",
                        )
                    except Exception:
                        pass
                    _set_status("SPEAKING...")
                    is_muted = should_mute() if should_mute else False
                    audio.speak(pyttsx3_engine, reply_text, mute=is_muted, log=_log)
                    state = "ACTIVE"
                    last_active_time = time.time()
                    _set_status("ACTIVE (Awake)")
                    _report()
                    # Train world model after this turn
                    try:
                        numeric_sensation = [float(i % 7) / 6.0 for i in range(min(8, len(feature_words)) or 1)]
                        numeric_action = [float(len(reply_text)) / 500.0, float(b_conf)]
                        world_model.observe(numeric_sensation, numeric_action)
                    except Exception:
                        pass
                    used_baby_shortcut = True
                # MEDIUM confidence local_exploratory: use but mark (no parent needed)
                elif b_source == "local_exploratory" and b_conf >= (baby_zoey.CONFIDENCE_THRESHOLD_LOW + 0.10):
                    reply_text = _sanitize_reply(prompt_to_send, b_resp)
                    if confidence.should_disclose(b_conf):
                        reply_text = "I'm still learning, but " + reply_text
                    used_model = f"baby:{b_source} ({b_conf:.2f})"
                    response_confidence, confidence_reason = confidence.estimate(prompt_to_send, reply_text)
                    brain_store.record_confidence(prompt_to_send, reply_text, response_confidence, confidence_reason)
                    reward = (response_confidence * 2.0) - 1.0
                    try:
                        growing_brain.experience(features=feature_words[:8], reward=reward, confused=True)
                        cellular_brain.experience(reward=reward)
                    except Exception as _ge:
                        _log(f"Brain post-update (baby exploratory) skipped: {_ge}", "warn")
                    last_model_used = used_model
                    brain_calls += 1
                    _log(f"{reply_text}", "zoey")
                    messages.append({"role": "assistant", "content": reply_text})
                    try:
                        brain_store.remember(
                            text=f"User: {prompt_to_send}\nZoey (baby exploratory): {reply_text}",
                            tags=["conversation", "baby_exploratory"],
                            source="engine",
                        )
                    except Exception:
                        pass
                    _set_status("SPEAKING...")
                    is_muted = should_mute() if should_mute else False
                    audio.speak(pyttsx3_engine, reply_text, mute=is_muted, log=_log)
                    state = "ACTIVE"
                    last_active_time = time.time()
                    _set_status("ACTIVE (Awake)")
                    _report()
                    # Train world model after this turn
                    try:
                        numeric_sensation = [float(i % 7) / 6.0 for i in range(min(8, len(feature_words)) or 1)]
                        numeric_action = [float(len(reply_text)) / 500.0, float(b_conf)]
                        world_model.observe(numeric_sensation, numeric_action)
                    except Exception:
                        pass
                    used_baby_shortcut = True

            # ---- PARENT / FULL LLM FLOW: runs when baby couldn't shortcut ----
            if not used_baby_shortcut:
                try:
                    _set_status("THINKING...")

                    # Use api.run_brain_turn or call_brain_with_fallback safely
                    if hasattr(api, "run_brain_turn"):
                        reply_text = api.run_brain_turn(client, messages, log=_log)
                        used_model = getattr(api, "_stats", {}).get("last_model_used", "OpenRouter")
                    else:
                        reply, used_model = api.call_brain_with_fallback(client, messages, log=_log)
                        raw_content = reply.choices[0].message.content
                        reply_text = (raw_content or "").strip()

                    # Safe fallback if content is empty or None
                    if not reply_text:
                        reply_text = "I'm right here! How can I help you?"

                    reply_text = _sanitize_reply(prompt_to_send, reply_text)
                    response_confidence, confidence_reason = confidence.estimate(prompt_to_send, reply_text)
                    brain_store.record_confidence(
                        prompt_to_send, reply_text, response_confidence, confidence_reason
                    )

                    # --- POST-PARENT LEARNING: Baby ZOEY studies parent's reply ---
                    try:
                        if baby_result and feature_words:
                            b_conf = float(baby_result.get("confidence", 0.0) or 0.0)
                            # Baby was uncertain → learn explicitly from the parent answer we just got
                            if b_conf < baby_zoey.CONFIDENCE_THRESHOLD_HIGH:
                                import symbolic_brain as _sb
                                _sb.learn(
                                    conditions=feature_words[:4],
                                    action="respond_with_guidance",
                                    reward=max(0.55, response_confidence),
                                )
                                try:
                                    brain_store.add_lesson(
                                        problem=f"Baby uncertain (conf={b_conf:.2f}): '{prompt_to_send[:80]}...'",
                                        fix=f"Parent's answer pattern: '{reply_text[:120]}...'",
                                        tags=["parent_guidance", "baby_learning"],
                                    )
                                except Exception:
                                    pass
                    except Exception as _baby_learn:
                        _log(f"Baby post-parent learning skipped: {_baby_learn}", "warn")

                    # Train topology + cellular after every parent turn
                    try:
                        growing_brain.experience(
                            features=feature_words[:8],
                            reward=(response_confidence * 2.0) - 1.0,
                            confused=confidence.should_disclose(response_confidence),
                        )
                        cellular_brain.experience(reward=(response_confidence * 2.0) - 1.0)
                    except Exception as growth_error:
                        _log(f"Growing brain update skipped: {growth_error}", "warn")

                    # Train world model after every turn (numeric sensation -> action)
                    try:
                        numeric_sensation = [float(i % 7) / 6.0 for i in range(min(8, len(feature_words)) or 1)]
                        numeric_action = [float(len(reply_text)) / 500.0, float(response_confidence)]
                        world_model.observe(numeric_sensation, numeric_action)
                    except Exception as _wm_err:
                        _log(f"World model observe skipped: {_wm_err}", "warn")

                    if confidence.should_disclose(response_confidence):
                        reply_text = "I'm guessing, but " + reply_text
                    last_model_used = used_model
                    brain_calls += 1
                    _log(f"{reply_text}", "zoey")

                    messages.append({"role": "assistant", "content": reply_text})
                    try:
                        brain_store.remember(
                            text=f"User: {prompt_to_send}\nZoey: {reply_text}",
                            tags=["conversation"],
                            source="engine",
                        )
                    except Exception:
                        pass

                    _set_status("SPEAKING...")
                    is_muted = should_mute() if should_mute else False
                    audio.speak(pyttsx3_engine, reply_text, mute=is_muted, log=_log)

                    # RESET 60s timer AFTER speaking
                    state = "ACTIVE"
                    last_active_time = time.time()
                    _set_status("ACTIVE (Awake)")
                    _report()

                except Exception as e:
                    _log(f"Error during brain turn: {e}", "error")
                    _set_status("ACTIVE (Awake)")
