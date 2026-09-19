"""
ZOEY mind — one identity over every internal capability.

Gemma / llama.cpp, Needle 2, Baby ZOEY, and skills stay as internals.
The user talks to Zoey. This module routes and keeps the voice unified.
"""

from __future__ import annotations

import re

IDENTITY_BLOCK = """
You are one AI named Zoey. The local language model, file tools, memory,
and learning systems are internal parts of you, not separate assistants.
Never introduce yourself as Gemma, Needle, Baby Zoey, or a generic language model.
If asked who you are, say you are Zoey.
When the user wants files found, listed, or organized on this computer,
use run_needle2_file_agent. Speak the result in first person as Zoey.
""".strip()

_FILE_RE = re.compile(
    r"(?:"
    r"\b(?:find|locate|search for|where(?:'| i)?s|show me)\b.{0,48}\b(?:file|files|pdf|notes?|folder|document|docs?)\b"
    r"|"
    r"\b(?:list|show)\b.{0,32}\b(?:recent\s+)?files?\b"
    r"|"
    r"\b(?:organize|move|sort)\b.{0,32}\b(?:file|files|folder)\b"
    r"|"
    r"\b(?:my\s+(?:physics|chemistry|biology|math(?:s)?)\s+notes)\b"
    r")",
    re.I,
)

_ALIAS_PREFIX = re.compile(
    r"^\s*(?:hey\s+|hi\s+)?"
    r"(?:baby\s+zoey|baby\s+zoe|baby|needle\s*2|needle|gemma(?:\s*3)?|llama(?:\.cpp)?)"
    r"[,:\s]+",
    re.I,
)

_IDENTITY_PATTERNS = (
    (re.compile(r"\bBaby\s+ZOEY\b", re.I), "Zoey"),
    (re.compile(r"\bBaby\s+Zoey\b", re.I), "Zoey"),
    (re.compile(r"\bNeedle\s*2\b", re.I), "Zoey"),
    (re.compile(r"\bI am (?:Gemma(?:\s*3)?|a language model)\b", re.I), "I am Zoey"),
    (re.compile(r"\bI'm (?:Gemma(?:\s*3)?|a language model)\b", re.I), "I'm Zoey"),
    (re.compile(r"\bas (?:Gemma|Needle|Baby Zoey)\b", re.I), "as Zoey"),
)


def normalize_user_text(text: str) -> str:
    raw = (text or "").strip()
    cleaned = _ALIAS_PREFIX.sub("", raw).strip()
    return cleaned or raw


def is_file_request(text: str) -> bool:
    t = (text or "").strip()
    if not t:
        return False
    if re.search(r"\bneedle\s*2?\b", t, re.I):
        return True
    return bool(_FILE_RE.search(t))


def file_query(text: str) -> str:
    t = normalize_user_text(text)
    t = re.sub(r"\b(?:please|can you|could you|would you|zoey)\b", " ", t, flags=re.I)
    t = re.sub(r"\s+", " ", t).strip()
    return t or "list recent files"


def public_model_name(internal: str) -> str:
    s = (internal or "").strip()
    if not s or s == "-":
        return "zoey"
    low = s.lower()
    if low.startswith("baby:"):
        return "zoey · memory"
    if "needle" in low or low.startswith("tool:run_needle"):
        return "zoey · files"
    if low.startswith("tool:"):
        return "zoey · action"
    if low.startswith("local:"):
        return "zoey · local"
    if "/" in s or "openrouter" in low:
        return "zoey · online"
    return "zoey"


def sanitize_identity(reply: str) -> str:
    r = reply or ""
    for pattern, replacement in _IDENTITY_PATTERNS:
        r = pattern.sub(replacement, r)
    return r


def speak_files(result: str) -> str:
    r = sanitize_identity((result or "").strip())
    if not r:
        return "I couldn't find matching files."
    lowered = r.lower()
    if lowered.startswith(("i ", "i'", "here's", "here is")):
        return r
    if "unavailable" in lowered or "could not" in lowered or "not found" in lowered:
        return r
    return f"Here's what I found:\n{r}"
