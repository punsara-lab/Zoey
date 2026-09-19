"""Transparent confidence heuristics for ZOEY's local runtime."""


def estimate(prompt: str, reply: str, used_tool: bool = False) -> tuple[float, str]:
    prompt_text = (prompt or "").strip()
    reply_text = (reply or "").strip()
    if not reply_text:
        return 0.0, "empty reply"
    if used_tool:
        return 0.95, "completed by a concrete local tool"
    if any(marker in reply_text.lower() for marker in ("i'm not sure", "i am not sure", "i don't know", "i cannot verify")):
        return 0.35, "reply contains an uncertainty marker"
    if len(prompt_text.split()) >= 18:
        return 0.62, "long request may contain unresolved intent"
    if "?" in prompt_text or any(word in prompt_text.lower().split() for word in ("latest", "current", "today")):
        return 0.68, "question or time-sensitive request routed through a language model"
    return 0.78, "short conversational response without an explicit uncertainty marker"


def should_disclose(confidence: float) -> bool:
    return confidence < 0.55
