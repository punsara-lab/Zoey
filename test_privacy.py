"""Focused tests for ZOEY privacy boundaries."""

import os
import tempfile

import config
import privacy
import brain_store
from skills.web_skill import web_search


def test_hybrid_redacts_pii():
    config.PRIVACY_MODE = "hybrid"
    clean = privacy.sanitize_text("Email me at punsara@example.com and call 555-123-4567")
    assert "punsara@example.com" not in clean
    assert "555-123-4567" not in clean
    assert "<zoey_email_" in clean


def test_local_blocks_web():
    config.PRIVACY_MODE = "local"
    result = web_search({"query": "today news"})
    assert "blocked" in result.lower()


def test_encrypted_memory_round_trip():
    original_dir = brain_store.BRAIN_DIR
    original_enabled = config.ENCRYPT_MEMORY
    original_key = config.PRIVACY_KEY_PATH
    with tempfile.TemporaryDirectory() as folder:
        brain_store.BRAIN_DIR = folder
        config.ENCRYPT_MEMORY = True
        config.PRIVACY_KEY_PATH = os.path.join(folder, "zoey.key")
        brain_store.remember("private@example.com", source="test")
        path = brain_store.path_for("memory.jsonl")
        raw = open(path, "r", encoding="utf-8").read()
        assert "private@example.com" not in raw
        assert brain_store.recent_records("memory.jsonl")[0]["text"] == "private@example.com"
    brain_store.BRAIN_DIR = original_dir
    config.ENCRYPT_MEMORY = original_enabled
    config.PRIVACY_KEY_PATH = original_key


if __name__ == "__main__":
    test_hybrid_redacts_pii()
    test_local_blocks_web()
    test_encrypted_memory_round_trip()
    print("Privacy tests passed: redaction, local blocking, encrypted memory")
