"""Privacy controls for ZOEY's external calls and local records."""

import re
import threading

import config


_PATTERNS = {
    "email": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
    "phone": re.compile(r"(?<!\d)(?:\+?\d[\d .()-]{7,}\d)(?!\d)"),
    "credit_card": re.compile(r"(?<!\d)(?:\d[ -]?){13,19}(?!\d)"),
    "ssn": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    "api_key": re.compile(r"\b(?:sk-|sk-or-v1-|xai-|AIza)[A-Za-z0-9_-]{12,}\b"),
}

_last_session = threading.local()


class PrivacySession:
    def __init__(self):
        self.replacements = {}
        self.counter = 0

    def sanitize(self, text: str) -> str:
        sanitized = str(text or "")
        for pii_type, pattern in _PATTERNS.items():
            for match in list(pattern.finditer(sanitized)):
                original = match.group(0)
                token = f"<zoey_{pii_type}_{self.counter}>"
                self.counter += 1
                self.replacements[token] = original
                sanitized = sanitized.replace(original, token, 1)
        return sanitized

    def restore(self, text: str) -> str:
        restored = str(text or "")
        for token, original in self.replacements.items():
            restored = restored.replace(token, original)
        return restored


def mode() -> str:
    value = str(getattr(config, "PRIVACY_MODE", "hybrid") or "hybrid").lower().strip()
    return value if value in {"local", "hybrid", "encrypted_proxy"} else "hybrid"


def allow_external(service: str) -> bool:
    if mode() == "local":
        return False
    if service == "web" and bool(getattr(config, "PRIVACY_BLOCK_WEB", False)):
        return False
    return True


def sanitize_messages(messages: list[dict]) -> list[dict]:
    if mode() == "local":
        return messages
    session = PrivacySession()
    _last_session.session = session

    def clean(value):
        if isinstance(value, str):
            return session.sanitize(value)
        if isinstance(value, list):
            return [clean(item) for item in value]
        if isinstance(value, dict):
            return {key: clean(item) for key, item in value.items()}
        return value

    return clean(messages)


def restore(text: str) -> str:
    session = getattr(_last_session, "session", None)
    return session.restore(text) if session else text


def redact_for_log(text: str) -> str:
    return PrivacySession().sanitize(text)


def sanitize_text(text: str) -> str:
    session = PrivacySession()
    _last_session.session = session
    return session.sanitize(text)


def encryption_enabled() -> bool:
    return bool(getattr(config, "ENCRYPT_MEMORY", False))


def encrypt_line(line: str) -> str:
    if not encryption_enabled():
        return line
    try:
        from cryptography.fernet import Fernet
    except ImportError as exc:
        raise RuntimeError("ENCRYPT_MEMORY is enabled but cryptography is not installed.") from exc
    key_path = getattr(config, "PRIVACY_KEY_PATH", "zoey.key")
    try:
        with open(key_path, "rb") as handle:
            key = handle.read()
    except FileNotFoundError:
        key = Fernet.generate_key()
        with open(key_path, "wb") as handle:
            handle.write(key)
    return Fernet(key).encrypt(line.encode("utf-8")).decode("ascii") + "\n"


def decrypt_line(line: str) -> str:
    if not encryption_enabled():
        return line
    try:
        from cryptography.fernet import Fernet
    except ImportError as exc:
        raise RuntimeError("ENCRYPT_MEMORY is enabled but cryptography is not installed.") from exc
    key_path = getattr(config, "PRIVACY_KEY_PATH", "zoey.key")
    with open(key_path, "rb") as handle:
        key = handle.read()
    return Fernet(key).decrypt(line.strip().encode("ascii")).decode("utf-8")
