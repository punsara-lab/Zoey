import pytest

from chat_app import sanitize_terminal_text


def test_sanitize_terminal_text_removes_emoji_and_keeps_ascii():
    assert sanitize_terminal_text("[info] ZOEY Engine initialized. Mic disabled. Type below!") == (
        "[info] ZOEY Engine initialized. Mic disabled. Type below!"
    )
    assert sanitize_terminal_text("[warn] ⚠️ Parent bridge not available") == "[warn] WARNING Parent bridge not available"
    assert sanitize_terminal_text("[status] PASSIVE (Listening for wake word)") == "[status] PASSIVE (Listening for wake word)"
