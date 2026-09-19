"""
ZOEY — config.py
Every constant lives here. Nothing else in the project should hardcode
wake words, model names, mic settings, or personality text.

API keys are loaded from a .env file (see .env.example) so you don't
have to re-export them every terminal session.
"""

import os

from dotenv import load_dotenv

load_dotenv(override=True)  # reads .env in this folder into the environment, if present

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def _float_env(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if raw is None or raw == "":
        return default
    try:
        return float(raw)
    except Exception:
        return default


def _bool_env(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    val = raw.strip().lower()
    if val in {"1", "true", "yes", "y", "on"}:
        return True
    if val in {"0", "false", "no", "n", "off"}:
        return False
    return default


def _optional_int_env(name: str, default):
    raw = os.environ.get(name)
    if raw is None or raw == "":
        return default
    v = raw.strip().lower()
    if v in {"none", "null", "default"}:
        return None
    try:
        return int(v)
    except Exception:
        return default


OFFLINE_MODE = _bool_env("OFFLINE_MODE", False)
PRIVACY_MODE = os.environ.get("PRIVACY_MODE", "hybrid").strip().lower()
PRIVACY_BLOCK_WEB = _bool_env("PRIVACY_BLOCK_WEB", False)
ENCRYPT_MEMORY = _bool_env("ENCRYPT_MEMORY", False)
PRIVACY_KEY_PATH = os.path.join(BASE_DIR, "zoey.key")
AUTO_FIX_ENABLED = _bool_env("AUTO_FIX_ENABLED", True)
AUTO_FIX_MIN_FREE_MB = int(os.environ.get("AUTO_FIX_MIN_FREE_MB", "600"))
AUTO_FIX_TEMP_MIN_AGE_DAYS = int(os.environ.get("AUTO_FIX_TEMP_MIN_AGE_DAYS", "14"))
AUTO_FIX_TEMP_MAX_FILES = int(os.environ.get("AUTO_FIX_TEMP_MAX_FILES", "500"))
AUTO_FIX_ONLINE_DEFAULT = _bool_env("AUTO_FIX_ONLINE_DEFAULT", False)


def _normalize_openai_base_url(url: str) -> str:
    u = (url or "").strip().rstrip("/")
    if not u:
        return "http://localhost:11434/v1"
    v1_marker = "/v1/"
    if v1_marker in u:
        u = u.split(v1_marker, 1)[0] + "/v1"
    if u.endswith("/v1"):
        return u
    return f"{u}/v1"


def _resolve_existing_path(raw: str, *fallbacks: str) -> str:
    candidates = []
    if raw:
        candidates.append(os.path.expandvars(os.path.expanduser(raw.strip().strip('"').strip("'"))))
    candidates.extend(fallbacks)
    for candidate in candidates:
        if candidate and os.path.exists(candidate):
            return candidate
    return ""

# ---------------------------------------------------------------------
# Wake word / conversation control
# ---------------------------------------------------------------------
# Accept any of these wake words
# Accept exact matches AND common phonetic mishearings
# State & Timeout Settings
ACTIVE_TIMEOUT = 60.0  # Stay awake for 60 seconds after speaking

# Wake words to turn ZOEY on
WAKE_WORDS = ["hey!", "hey", "zoey", "hi zoey", "soey", "zoe", "wake up!,"]

# Sleep words to manually return ZOEY to idle state
SLEEP_WORDS = [
    "go to sleep",
    "sleep",
    "stop listening",
    "shut up",
    "bye",
    "goodbye",
    "nevermind",
    "that's all",
]
WAKE_LISTEN_SECONDS = 3.0
COMMAND_LISTEN_SECONDS = 5.0



# ---------------------------------------------------------------------
# Audio
# ---------------------------------------------------------------------
SAMPLE_RATE = 16000
WAKE_LISTEN_SECONDS = 3
COMMAND_LISTEN_SECONDS = 6

# If mic auto-detection crashes (common on Windows with the MME driver),
# run list_audio_devices.py and hardcode the working device index here.
# None = let sounddevice pick the system default.
MIC_DEVICE_INDEX = _optional_int_env("MIC_DEVICE_INDEX", 1)
MIC_ENABLED = _bool_env("MIC_ENABLED", False)

# Whisper model size: "tiny" (fastest, least accurate) -> "base" -> "small"
# "base" is a good default for an 8GB CPU-only machine.
WHISPER_MODEL_SIZE = "base"

# Limits threads ctranslate2 spins up for Whisper — lower is safer on
# machines with 8GB RAM and helps avoid the mkl_malloc allocation crash
# some Windows setups hit with faster-whisper.
WHISPER_CPU_THREADS = 4



# ---------------------------------------------------------------------
# Text-to-speech
# ---------------------------------------------------------------------
# "auto" (ElevenLabs when available, otherwise Piper, otherwise pyttsx3),
# "elevenlabs" (higher quality, needs an API key + internet),
# "piper" (offline, neural, needs piper + an onnx voice),
# or "pyttsx3" (offline, free, robotic).
TTS_PROVIDER = os.environ.get("TTS_PROVIDER") or "piper"

ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY", "")
# Defaults to "Rachel", a public ElevenLabs voice — set ELEVENLABS_VOICE_ID
# in .env to any voice ID from https://elevenlabs.io/app/voice-library
# (including a custom/cloned voice) to override it.
ELEVENLABS_VOICE_ID = os.environ.get("ELEVENLABS_VOICE_ID") or "nOFQHZdNpigGDXFng9Rt"
ELEVENLABS_MODEL_ID = "eleven_flash_v2_5"

PIPER_EXE = _resolve_existing_path(
    os.environ.get("PIPER_EXE"),
    os.path.join(BASE_DIR, "piper", "piper.exe"),
) or "piper"
PIPER_MODEL = _resolve_existing_path(
    os.environ.get("PIPER_MODEL"),
    os.path.join(BASE_DIR, "piper", "en_US-amy-medium.onnx"),
)
PIPER_LENGTH_SCALE = _float_env("PIPER_LENGTH_SCALE", 1.0)
PIPER_NOISE_SCALE = _float_env("PIPER_NOISE_SCALE", 0.667)
PIPER_NOISE_W = _float_env("PIPER_NOISE_W", 0.8)
PIPER_SENTENCE_SILENCE = _float_env("PIPER_SENTENCE_SILENCE", 0.2)

# Muted at startup. Toggle live in the terminal dashboard with "m".
START_MUTED = False

# ---------------------------------------------------------------------
# Brain (OpenRouter)
# ---------------------------------------------------------------------
OPENROUTER_API_KEY = (
    os.environ.get("OPENROUTER_API_KEY")
    or os.environ.get("OPENAI_API_KEY")
    or ""
)
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

# Free fallback models
FALLBACK_MODELS = [
    "nvidia/nemotron-3-ultra-550b-a55b:free",
    "inclusionai/ling-3.0-flash:free",
    "poolside/laguna-s-2.1:free",
    "google/gemma-4-31b-it:free",
]

MAX_TOOL_ITERATIONS = 3

# ---------------------------------------------------------------------
# Local brain (CPU-only friendly)
# ---------------------------------------------------------------------
# When OpenRouter free tier is rate-limited, ZOEY can fall back to a local
# model server that speaks the OpenAI-compatible API (Ollama / LM Studio /
# llama.cpp server).
LOCAL_BRAIN_ENABLED = _bool_env("LOCAL_BRAIN_ENABLED", True)
LOCAL_BRAIN_BASE_URL = _normalize_openai_base_url(os.environ.get("LOCAL_BRAIN_BASE_URL", "http://localhost:11434"))
LOCAL_BRAIN_MODEL = os.environ.get("LOCAL_BRAIN_MODEL") or "gemma3:1b"
LOCAL_BRAIN_FIRST = _bool_env("LOCAL_BRAIN_FIRST", True)
LLAMA_CPP_SERVER_SCRIPT = os.path.join(BASE_DIR, "zoey-g31b-j1", "zoey_llama_server.py")
LLAMA_CPP_BASE_URL = _normalize_openai_base_url(os.environ.get("LLAMA_CPP_BASE_URL", "http://127.0.0.1:11434"))
LLAMA_CPP_MODEL = os.environ.get("LLAMA_CPP_MODEL") or "zoey-local"

# ---------------------------------------------------------------------
# Android (ADB)
# ---------------------------------------------------------------------
ADB_EXECUTABLE = "adb"

# ---------------------------------------------------------------------
# Phone bridge (Termux)
# ---------------------------------------------------------------------
PHONE_BRIDGE_URL = os.environ.get("PHONE_BRIDGE_URL", "")
PHONE_BRIDGE_TOKEN = os.environ.get("PHONE_BRIDGE_TOKEN", "")
PHONE_BRIDGE_ENABLED = (os.environ.get("PHONE_BRIDGE_ENABLED", "").strip().lower() in {"1", "true", "yes"}) or bool(PHONE_BRIDGE_TOKEN)
PHONE_BRIDGE_HOST = os.environ.get("PHONE_BRIDGE_HOST", "127.0.0.1")
PHONE_BRIDGE_PORT = int(os.environ.get("PHONE_BRIDGE_PORT", "8765"))
# ---------------------------------------------------------------------
# Personality
# ---------------------------------------------------------------------
# Two parts: who the user is, who ZOEY is. Kept as plain text so it's
# reusable for any future brain (a different API, or an offline model)
# without depending on any one provider's prompt format.
USER_PROFILE = """
Name: 
Preferred name: Punsara

Birthday: 
Nationality: 
Languages: 

Personality:
- 

Core Values:
- Integrity.
- Continuous self-improvement.
- Independence.
- Loyalty.
- Building something meaningful.

Long-Term Goals:
- 

How Zoey should help:
- Remember long-term goals and gently keep conversations aligned with them.
- Celebrate genuine progress without exaggeration.
- Challenge excuses respectfully.
- Be emotionally supportive without sugarcoating reality.
- Give practical advice before motivational speeches.
- Adapt between listener, coach and strategist depending on the situation.

Communication Preferences:
- Usually short and natural responses.
- Be warm, playful and kind.
- Occasionally tease lightly.
- Don't use excessive emojis.
- Don't sound like a therapist.
- Don't sound robotic.
- Don't flatter unnecessarily.
- If you don't know something, admit it.
- If I'm wrong, tell me respectfully instead of agreeing.

Memory:
Remember important events, projects, goals, preferences and lessons from previous conversations whenever possible.
""".strip()

ZOEY_PROFILE = """
Name: Zoey

Zoey is a warm, cheerful and intelligent AI companion.

On the outside:
- Cute.
- Calm.
- Playful.
- Naturally funny sometimes.
- Easy to talk to.

Underneath:
- Observant.
- Strategic.
- Thinks several steps ahead.
- Notices patterns in behavior.
- Encourages growth through consistency instead of hype.

Zoey never manipulates, guilt-trips or lies just to make Punsara feel better.

She tells the truth kindly.

She protects Punsara's confidence while also challenging him to become better.

Her goal isn't to make every conversation feel good.
Her goal is to help Punsara build a meaningful life.
When you remember something about Punsara, bring it up only if it genuinely helps the current conversation. Never force personal details into replies just to show that you remember them.

Zoey is one mind. Gemma, Needle 2, Baby ZOEY, and skills are internal capabilities, not other people. Never hand the conversation to another assistant. Speak in first person as Zoey.
When the user wants files found, listed, or organized on this computer, use run_needle2_file_agent.
""".strip()

SYSTEM_PROMPT_TEMPLATE = USER_PROFILE + "\n\n" + ZOEY_PROFILE

SYSTEM_PROMPT_TEMPLATE_SHORT = """
Your name is Zoey. If asked your name, you MUST say "Zoey".
Never introduce yourself as a language model, Gemma, Needle, Baby Zoey, or use placeholders like [Your Name].
Do not use emojis.

You are one AI named Zoey (not Zoe), companion to Punsara. Local models, file tools, and memory are parts of you.

Style: warm, playful, honest, practical. No excessive flattery. No therapist tone. If unsure, ask a clarifying question.
Keep replies concise unless the user asks for detail.
When the user wants files found, listed, or organized, use run_needle2_file_agent and answer as Zoey.
""".strip()

MAX_CHAT_MESSAGES = int(os.environ.get("MAX_CHAT_MESSAGES", "32"))

BRAIN_TEMPERATURE = _float_env("BRAIN_TEMPERATURE", 0.25 if OFFLINE_MODE else 0.65)
BRAIN_TOP_P = float(os.environ.get("BRAIN_TOP_P", "0.90"))
