"""Turn successful episodes into quarantined, readable Python candidates."""

import ast
import json
import os
import re
import time
import uuid


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.join(BASE_DIR, "learned_skills", "candidates")
ALLOWED_ACTIONS = {"open_app", "open_url", "list_directory", "search_files", "get_current_time"}


def _safe_name(name: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9_]+", "_", name.strip().lower()).strip("_")
    return value or "learned_episode"


def _validate(source: str) -> str:
    try:
        ast.parse(source)
        return "valid"
    except SyntaxError as exc:
        return str(exc)


def compile_episode(name: str, steps: list[dict], success: bool) -> dict:
    """Write a candidate function only after a successful episode.

    The generated function returns an action plan; it does not execute PC
    actions and is not imported by ZOEY automatically.
    """
    if not success:
        return {"status": "ignored", "reason": "only successful episodes become candidates"}
    clean_steps = []
    for step in steps[:20]:
        action = str(step.get("action", "")).strip()
        arguments = step.get("arguments", {})
        if action not in ALLOWED_ACTIONS or not isinstance(arguments, dict):
            return {"status": "rejected", "reason": f"action not allowed: {action}"}
        clean_steps.append({"action": action, "arguments": arguments})
    if not clean_steps:
        return {"status": "rejected", "reason": "episode has no steps"}

    function_name = _safe_name(name)
    source = (
        "\"\"\"Candidate learned skill. Review before loading.\"\"\"\n"
        f"def {function_name}():\n"
        "    return " + repr(clean_steps) + "\n"
    )
    validation = _validate(source)
    if validation != "valid":
        return {"status": "rejected", "reason": validation}

    os.makedirs(SKILL_DIR, exist_ok=True)
    candidate_id = uuid.uuid4().hex[:10]
    py_path = os.path.join(SKILL_DIR, f"{candidate_id}_{function_name}.py")
    meta_path = py_path + ".json"
    with open(py_path, "w", encoding="utf-8") as handle:
        handle.write(source)
    with open(meta_path, "w", encoding="utf-8") as handle:
        json.dump(
            {
                "id": candidate_id,
                "name": function_name,
                "status": "pending_review",
                "created_at": time.time(),
                "steps": clean_steps,
                "source_path": py_path,
            },
            handle,
            indent=2,
        )
    return {"status": "pending_review", "id": candidate_id, "path": py_path, "steps": len(clean_steps)}
