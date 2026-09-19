import json

import brain_store
import data_store
import zoey_dreams
import growing_brain
import cellular_brain
import zoey_genome
import world_model
import symbolic_brain
import qd_archive
import episodic_programs


def _json_out(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=2)


def get_user_profile(args: dict) -> str:
    key = (args.get("key") or "").strip()
    if key:
        return _json_out({"key": key, "value": data_store.get_user_value(key)})
    return _json_out(data_store.get_user_data())


def get_zoey_identity(args: dict) -> str:
    return _json_out(data_store.get_zoey_data())


def remember(args: dict) -> str:
    text = (args.get("text") or "").strip()
    tags = args.get("tags") or []
    source = (args.get("source") or "user").strip() or "user"
    brain_store.remember(text=text, tags=list(tags) if isinstance(tags, list) else [], source=source)
    return "OK"


def add_lesson(args: dict) -> str:
    problem = (args.get("problem") or "").strip()
    fix = (args.get("fix") or "").strip()
    tags = args.get("tags") or []
    brain_store.add_lesson(problem=problem, fix=fix, tags=list(tags) if isinstance(tags, list) else [])
    return "OK"


def add_error_fix(args: dict) -> str:
    error = (args.get("error") or "").strip()
    fix = (args.get("fix") or "").strip()
    tags = args.get("tags") or []
    brain_store.add_error(error=error, fix=fix, tags=list(tags) if isinstance(tags, list) else [])
    return "OK"


def add_research(args: dict) -> str:
    note = (args.get("note") or "").strip()
    source = (args.get("source") or "").strip()
    url = (args.get("url") or "").strip()
    tags = args.get("tags") or []
    brain_store.add_research(note=note, source=source, url=url, tags=list(tags) if isinstance(tags, list) else [])
    return "OK"


def search_brain(args: dict) -> str:
    query = (args.get("query") or "").strip()
    files = args.get("files")
    limit = args.get("limit", 8)
    res = brain_store.search(query=query, files=files if isinstance(files, list) else None, limit=int(limit or 8))
    return _json_out(res)


def run_dream_cycle(args: dict) -> str:
    hours = int(args.get("hours", 24) or 24)
    return _json_out(zoey_dreams.dream_cycle(hours=max(1, min(hours, 168))))


def get_morning_brief(args: dict) -> str:
    limit = int(args.get("limit", 5) or 5)
    return _json_out(zoey_dreams.get_morning_brief(limit=max(1, min(limit, 20))))


def record_brain_experience(args: dict) -> str:
    features = args.get("features") or []
    reward = float(args.get("reward", 0.0) or 0.0)
    confused = bool(args.get("confused", False))
    if not isinstance(features, list):
        features = [str(features)]
    return _json_out(growing_brain.experience(features, reward, confused))


def inspect_growing_brain(_args: dict) -> str:
    return _json_out(growing_brain.summary())


def run_cellular_experience(args: dict) -> str:
    reward = float(args.get("reward", 0.0) or 0.0)
    return _json_out(cellular_brain.experience(reward))


def inspect_cellular_brain(_args: dict) -> str:
    return _json_out(cellular_brain.summary())


def propose_genome_mutation(args: dict) -> str:
    target = (args.get("target_path") or "").strip()
    source = args.get("replacement_source") or ""
    reason = (args.get("reason") or "").strip()
    if not target or not source or not reason:
        return "target_path, replacement_source, and reason are required."
    return _json_out(zoey_genome.propose_mutation(target, source, reason))


def list_genome_proposals(_args: dict) -> str:
    return _json_out(zoey_genome.list_proposals())


def observe_world(args: dict) -> str:
    sensation = args.get("sensation") or []
    action = args.get("action") or []
    if not isinstance(sensation, list) or not isinstance(action, list):
        return "sensation and action must be numeric arrays."
    return _json_out(world_model.observe(sensation, action))


def inspect_world_model(_args: dict) -> str:
    return _json_out(world_model.summary())


def learn_symbolic_rule(args: dict) -> str:
    conditions = args.get("conditions") or []
    return _json_out(symbolic_brain.learn(conditions, args.get("action", ""), args.get("reward", 0.0)))


def fire_symbolic_rule(args: dict) -> str:
    return _json_out(symbolic_brain.fire(args.get("features") or []))


def inspect_symbolic_rules(_args: dict) -> str:
    return _json_out(symbolic_brain.summary())


def select_strategy(args: dict) -> str:
    return _json_out(qd_archive.select((args.get("descriptor") or "").strip()))


def evaluate_strategy(args: dict) -> str:
    return _json_out(qd_archive.evaluate(args.get("member_id", ""), args.get("score", 0.0)))


def mutate_strategy(args: dict) -> str:
    return _json_out(qd_archive.mutate(args.get("parent_id", "")))


def inspect_strategy_archive(_args: dict) -> str:
    return _json_out(qd_archive.summary())


def compile_episode(args: dict) -> str:
    steps = args.get("steps") or []
    return _json_out(episodic_programs.compile_episode(args.get("name", "learned_episode"), steps, bool(args.get("success", False))))


TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "get_user_profile",
            "description": "Returns user's real profile data from data/user.json. Optionally provide key like 'preferred_name' or 'communication_preferences.style'.",
            "parameters": {
                "type": "object",
                "properties": {"key": {"type": "string"}},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_zoey_identity",
            "description": "Returns Zoey identity/style rules from data/zoey.json.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "remember",
            "description": "Append a memory item into brain/memory.jsonl.",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {"type": "string"},
                    "tags": {"type": "array", "items": {"type": "string"}},
                    "source": {"type": "string"},
                },
                "required": ["text"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "add_lesson",
            "description": "Store a problem + fix into brain/lessons.jsonl (lessons learned).",
            "parameters": {
                "type": "object",
                "properties": {
                    "problem": {"type": "string"},
                    "fix": {"type": "string"},
                    "tags": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["problem", "fix"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "add_error_fix",
            "description": "Store an error + fix into brain/errors.jsonl.",
            "parameters": {
                "type": "object",
                "properties": {
                    "error": {"type": "string"},
                    "fix": {"type": "string"},
                    "tags": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["error"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "add_research",
            "description": "Store a research note into brain/research.jsonl.",
            "parameters": {
                "type": "object",
                "properties": {
                    "note": {"type": "string"},
                    "source": {"type": "string"},
                    "url": {"type": "string"},
                    "tags": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["note"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_brain",
            "description": "Search brain JSONL files for a query string (simple substring search).",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "files": {"type": "array", "items": {"type": "string"}},
                    "limit": {"type": "integer"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_dream_cycle",
            "description": "Consolidate recent memories and create a local morning brief while ZOEY sleeps.",
            "parameters": {
                "type": "object",
                "properties": {"hours": {"type": "integer"}},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_morning_brief",
            "description": "Read the latest insights created by ZOEY's dream cycle.",
            "parameters": {
                "type": "object",
                "properties": {"limit": {"type": "integer"}},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "record_brain_experience",
            "description": "Train ZOEY's small persistent concept topology from features, reward, and confusion.",
            "parameters": {
                "type": "object",
                "properties": {
                    "features": {"type": "array", "items": {"type": "string"}},
                    "reward": {"type": "number", "description": "Outcome from -1 (bad) to 1 (good)."},
                    "confused": {"type": "boolean"},
                },
                "required": ["features", "reward"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "inspect_growing_brain",
            "description": "Inspect the current NEAT-style concept topology and its growth history.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_cellular_experience",
            "description": "Update ZOEY's distributed cellular brain from an interaction reward between -1 and 1.",
            "parameters": {
                "type": "object",
                "properties": {"reward": {"type": "number"}},
                "required": ["reward"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "inspect_cellular_brain",
            "description": "Inspect the current cellular brain grid and learned local rules.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "propose_genome_mutation",
            "description": "Create a validated source mutation proposal for user review; never edits or executes the target automatically.",
            "parameters": {
                "type": "object",
                "properties": {
                    "target_path": {"type": "string"},
                    "replacement_source": {"type": "string"},
                    "reason": {"type": "string"},
                },
                "required": ["target_path", "replacement_source", "reason"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_genome_proposals",
            "description": "List pending and historical self-modification proposals.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "observe_world",
            "description": "Train the from-scratch local world model on a numeric sensation and action transition.",
            "parameters": {
                "type": "object",
                "properties": {
                    "sensation": {"type": "array", "items": {"type": "number"}},
                    "action": {"type": "array", "items": {"type": "number"}},
                },
                "required": ["sensation"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "inspect_world_model",
            "description": "Inspect local prediction error, surprise, and habituation statistics.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "learn_symbolic_rule",
            "description": "Learn an explainable production rule from conditions, action, and reward.",
            "parameters": {
                "type": "object",
                "properties": {
                    "conditions": {"type": "array", "items": {"type": "string"}},
                    "action": {"type": "string"},
                    "reward": {"type": "number"},
                },
                "required": ["conditions", "action", "reward"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "fire_symbolic_rule",
            "description": "Fire the strongest explainable learned rule matching the supplied features.",
            "parameters": {
                "type": "object",
                "properties": {"features": {"type": "array", "items": {"type": "string"}}},
                "required": ["features"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "inspect_symbolic_rules",
            "description": "Inspect learned symbolic rules, strengths, uses, and regrets.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "select_strategy",
            "description": "Select or create a strategy in the bounded quality-diversity archive.",
            "parameters": {
                "type": "object",
                "properties": {"descriptor": {"type": "string"}},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "evaluate_strategy",
            "description": "Score a quality-diversity strategy from -1 to 1.",
            "parameters": {
                "type": "object",
                "properties": {"member_id": {"type": "string"}, "score": {"type": "number"}},
                "required": ["member_id", "score"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "mutate_strategy",
            "description": "Create a bounded mutation of a quality-diversity strategy.",
            "parameters": {
                "type": "object",
                "properties": {"parent_id": {"type": "string"}},
                "required": ["parent_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "inspect_strategy_archive",
            "description": "Inspect the quality-diversity archive and its top strategies.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "compile_episode",
            "description": "Turn a successful approved action episode into a quarantined Python candidate for review.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "steps": {"type": "array", "items": {"type": "object"}},
                    "success": {"type": "boolean"},
                },
                "required": ["name", "steps", "success"],
            },
        },
    },
]


DISPATCH = {
    "get_user_profile": get_user_profile,
    "get_zoey_identity": get_zoey_identity,
    "remember": remember,
    "add_lesson": add_lesson,
    "add_error_fix": add_error_fix,
    "add_research": add_research,
    "search_brain": search_brain,
    "run_dream_cycle": run_dream_cycle,
    "get_morning_brief": get_morning_brief,
    "record_brain_experience": record_brain_experience,
    "inspect_growing_brain": inspect_growing_brain,
    "run_cellular_experience": run_cellular_experience,
    "inspect_cellular_brain": inspect_cellular_brain,
    "propose_genome_mutation": propose_genome_mutation,
    "list_genome_proposals": list_genome_proposals,
    "observe_world": observe_world,
    "inspect_world_model": inspect_world_model,
    "learn_symbolic_rule": learn_symbolic_rule,
    "fire_symbolic_rule": fire_symbolic_rule,
    "inspect_symbolic_rules": inspect_symbolic_rules,
    "select_strategy": select_strategy,
    "evaluate_strategy": evaluate_strategy,
    "mutate_strategy": mutate_strategy,
    "inspect_strategy_archive": inspect_strategy_archive,
    "compile_episode": compile_episode,
}
