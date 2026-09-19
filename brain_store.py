import json
import os
import time
from glob import glob

import privacy


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BRAIN_DIR = os.path.join(BASE_DIR, "brain")


def path_for(filename: str) -> str:
    """Return a path inside the active brain store."""
    return os.path.join(BRAIN_DIR, filename)


def _ensure_brain_dir() -> None:
    os.makedirs(BRAIN_DIR, exist_ok=True)


def _append_jsonl(path: str, obj: dict) -> None:
    _ensure_brain_dir()
    with open(path, "a", encoding="utf-8") as f:
        line = json.dumps(obj, ensure_ascii=False) + "\n"
        f.write(privacy.encrypt_line(line))


def remember(text: str, tags: list | None = None, source: str = "user") -> None:
    if not text:
        return
    _append_jsonl(
        os.path.join(BRAIN_DIR, "memory.jsonl"),
        {"ts": time.time(), "type": "memory", "source": source, "tags": tags or [], "text": text},
    )


def add_lesson(problem: str, fix: str, tags: list | None = None) -> None:
    if not (problem or fix):
        return
    _append_jsonl(
        os.path.join(BRAIN_DIR, "lessons.jsonl"),
        {"ts": time.time(), "type": "lesson", "tags": tags or [], "problem": problem or "", "fix": fix or ""},
    )


def add_error(error: str, fix: str = "", tags: list | None = None) -> None:
    if not error:
        return
    _append_jsonl(
        os.path.join(BRAIN_DIR, "errors.jsonl"),
        {"ts": time.time(), "type": "error", "tags": tags or [], "error": error, "fix": fix or ""},
    )


def add_research(note: str, source: str = "", url: str = "", tags: list | None = None) -> None:
    if not note:
        return
    _append_jsonl(
        os.path.join(BRAIN_DIR, "research.jsonl"),
        {"ts": time.time(), "type": "research", "tags": tags or [], "source": source or "", "url": url or "", "note": note},
    )


def _iter_jsonl_lines(path: str):
    if not os.path.exists(path):
        return
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            s = (line or "").strip()
            if not s:
                continue
            try:
                yield json.loads(privacy.decrypt_line(s))
            except Exception:
                continue


def iter_jsonl(path: str):
    """Public read-only iterator for local processing such as dream cycles."""
    yield from _iter_jsonl_lines(path)


def recent_records(filename: str, limit: int = 5) -> list[dict]:
    records = list(_iter_jsonl_lines(path_for(filename)))
    return records[-max(1, int(limit)) :]


def add_morning_brief(text: str, tags: list | None = None, source: str = "dream_cycle") -> None:
    if not text:
        return
    _append_jsonl(
        path_for("morning_brief.jsonl"),
        {"ts": time.time(), "type": "morning_brief", "source": source, "tags": tags or [], "text": text},
    )


def record_dream_run(memories_seen: int, clusters_found: int, insights_created: int) -> None:
    _append_jsonl(
        path_for("dreams.jsonl"),
        {
            "ts": time.time(),
            "type": "dream_run",
            "memories_seen": memories_seen,
            "clusters_found": clusters_found,
            "insights_created": insights_created,
        },
    )


def record_confidence(prompt: str, reply: str, confidence: float, reason: str) -> None:
    _append_jsonl(
        path_for("confidence.jsonl"),
        {
            "ts": time.time(),
            "type": "confidence",
            "prompt": prompt,
            "reply": reply,
            "confidence": round(max(0.0, min(1.0, confidence)), 2),
            "reason": reason,
        },
    )
def search(query: str, files: list[str] | None = None, limit: int = 8) -> list[dict]:
    q = (query or "").strip().lower()
    if not q:
        return []
    _ensure_brain_dir()
    paths = []
    if files:
        for f in files:
            paths.append(os.path.join(BRAIN_DIR, f))
    else:
        paths = glob(os.path.join(BRAIN_DIR, "*.jsonl"))

    hits = []
    for p in paths:
        for obj in _iter_jsonl_lines(p):
            hay = json.dumps(obj, ensure_ascii=False).lower()
            if q in hay:
                hits.append({"file": os.path.basename(p), "item": obj})
                if len(hits) >= max(1, int(limit)):
                    return hits
    return hits


def build_context(limit_per_file: int = 3) -> str:
    _ensure_brain_dir()
    parts = []
    for fname in ["lessons.jsonl", "errors.jsonl", "memory.jsonl"]:
        path = os.path.join(BRAIN_DIR, fname)
        items = list(_iter_jsonl_lines(path))
        items = [x for x in items if isinstance(x, dict) and x.get("type") != "system"]
        if not items:
            continue
        tail = items[-max(1, int(limit_per_file)) :]
        parts.append(f"{fname}:")
        for it in tail:
            parts.append(json.dumps(it, ensure_ascii=False))
    return "\n".join(parts).strip()
