"""
ZOEY — api.py
The LLM layer handles messages, OpenRouter fallback models, tool calls,
and key cleaning to ensure reliable connections.
"""

import json
import os
import socket
from urllib.parse import urlparse
from dotenv import load_dotenv
from openai import OpenAI

import config
import privacy
import tools

# Force load .env so cached system variables do not override your key
load_dotenv(override=True)


_stats = {"brain_calls": 0, "last_model_used": None}


def get_stats() -> dict:
    return dict(_stats)


def get_clean_key() -> str:
    """Retrieves and cleans the OpenRouter API key from env or config."""
    key = (
        os.getenv("OPENROUTER_API_KEY")
        or os.getenv("OPENAI_API_KEY")
        or getattr(config, "OPENROUTER_API_KEY", "")
    )
    # Strip whitespace, quotation marks, and invisible Windows characters
    return key.strip().strip('"').strip("'").replace("\ufeff", "").replace("\r", "")


def make_client() -> OpenAI:
    if bool(getattr(config, "OFFLINE_MODE", False)) or privacy.mode() == "local":
        if getattr(config, "LOCAL_BRAIN_ENABLED", False):
            return make_local_client()
        raise RuntimeError("OFFLINE_MODE is enabled but LOCAL_BRAIN_ENABLED is false.")
    api_key = get_clean_key()
    base_url = getattr(config, "OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")

    if not api_key:
        if getattr(config, "LOCAL_BRAIN_ENABLED", False):
            return make_local_client()
        raise RuntimeError(
            "OPENROUTER_API_KEY is missing or empty. Get a key at "
            "https://openrouter.ai/keys and set it in your .env file."
        )

    return OpenAI(
        base_url=base_url,
        api_key=api_key,
        default_headers={
            "HTTP-Referer": "http://localhost",
            "X-Title": "ZOEY Assistant",
        },
    )


def make_local_client() -> OpenAI:
    base_url = getattr(config, "LOCAL_BRAIN_BASE_URL", "http://localhost:11434/v1")
    return OpenAI(base_url=base_url, api_key="local")


def _is_openrouter_free_daily_limit_error(e: Exception) -> bool:
    s = str(e)
    return "free-models-per-day" in s or "openrouter_free_tier_daily" in s


def _call_model(client: OpenAI, model: str, messages: list, log=None, external=False) -> tuple:
    request_messages = privacy.sanitize_messages(messages) if external else messages
    kwargs = {"model": model, "messages": request_messages}
    temperature = getattr(config, "BRAIN_TEMPERATURE", None)
    top_p = getattr(config, "BRAIN_TOP_P", None)
    if temperature is not None:
        kwargs["temperature"] = float(temperature)
    if top_p is not None:
        kwargs["top_p"] = float(top_p)
    if hasattr(tools, "TOOL_DEFINITIONS") and tools.TOOL_DEFINITIONS:
        kwargs["tools"] = tools.TOOL_DEFINITIONS
    try:
        response = client.chat.completions.create(**kwargs)
        return response, model
    except Exception as e:
        if "tools" in kwargs:
            try:
                kwargs.pop("tools", None)
                response = client.chat.completions.create(**kwargs)
                return response, model
            except Exception:
                pass
        if log:
            log(f"(brain: {model}) failed: {e}", "warn")
        raise


def _can_use_openrouter() -> bool:
    if bool(getattr(config, "OFFLINE_MODE", False)):
        return False
    api_key = get_clean_key()
    if not api_key:
        return False
    try:
        base_url = getattr(config, "OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
        u = urlparse(base_url)
        host = u.hostname or "openrouter.ai"
        port = 443 if (u.scheme or "https") == "https" else 80
        socket.create_connection((host, port), timeout=1.5).close()
        return True
    except Exception:
        return False


def call_brain_with_fallback(client: OpenAI, messages: list, log=None) -> tuple:
    """Tries each model in config.FALLBACK_MODELS in order until one
    responds successfully. Returns (response, model_name_used)."""
    last_error = None
    local_enabled = bool(getattr(config, "LOCAL_BRAIN_ENABLED", False))
    local_model = getattr(config, "LOCAL_BRAIN_MODEL", "llama3.2:1b-instruct")
    local_first = bool(getattr(config, "LOCAL_BRAIN_FIRST", True))
    offline_mode = bool(getattr(config, "OFFLINE_MODE", False))
    online_ok = (not offline_mode) and privacy.allow_external("llm") and _can_use_openrouter()

    if local_enabled and local_first:
        try:
            local_client = make_local_client()
            response, _used = _call_model(local_client, local_model, messages, log=log)
            choices = getattr(response, "choices", None)
            if choices is None and isinstance(response, dict):
                choices = response.get("choices")
            if not choices:
                raise RuntimeError("Local model returned no choices")
            _stats["brain_calls"] += 1
            _stats["last_model_used"] = f"local:{local_model}"
            return response, f"local:{local_model}"
        except Exception as le:
            if log:
                log(f"(local base_url: {getattr(config, 'LOCAL_BRAIN_BASE_URL', None)})", "warn")
            last_error = le

    if online_ok:
        for model_name in config.FALLBACK_MODELS:
            try:
                response, _used = _call_model(client, model_name, messages, log=log, external=True)

                choices = getattr(response, "choices", None)
                if choices is None and isinstance(response, dict):
                    choices = response.get("choices")
                if not choices:
                    raise RuntimeError("Model returned no choices")

                _stats["brain_calls"] += 1
                _stats["last_model_used"] = model_name
                return response, model_name
            except Exception as e:
                last_error = e
                if local_enabled and _is_openrouter_free_daily_limit_error(e):
                    try:
                        local_client = make_local_client()
                        response, _used = _call_model(local_client, local_model, messages, log=log)

                        choices = getattr(response, "choices", None)
                        if choices is None and isinstance(response, dict):
                            choices = response.get("choices")
                        if not choices:
                            raise RuntimeError("Local model returned no choices")

                        _stats["brain_calls"] += 1
                        _stats["last_model_used"] = f"local:{local_model}"
                        return response, f"local:{local_model}"
                    except Exception as le:
                        last_error = le
                        break
                continue

    if local_enabled:
        try:
            local_client = make_local_client()
            response, _used = _call_model(local_client, local_model, messages, log=log)
            choices = getattr(response, "choices", None)
            if choices is None and isinstance(response, dict):
                choices = response.get("choices")
            if not choices:
                raise RuntimeError("Local model returned no choices")
            _stats["brain_calls"] += 1
            _stats["last_model_used"] = f"local:{local_model}"
            return response, f"local:{local_model}"
        except Exception as le:
            last_error = le

    raise RuntimeError(
        "All brain backends failed. If OpenRouter is rate-limited, install a local model server "
        "(Ollama recommended) and set LOCAL_BRAIN_BASE_URL/LOCAL_BRAIN_MODEL in config.py. "
        f"Last error: {last_error}"
    )


def run_brain_turn(client: OpenAI, messages: list, log=None) -> str:
    """Runs one full turn: send message -> if the model calls a tool,
    execute it and feed the result back -> repeat until the model gives
    a plain text reply, or the iteration cap is hit."""

    for _ in range(config.MAX_TOOL_ITERATIONS):
        response, model_used = call_brain_with_fallback(client, messages, log=log)

        choices = getattr(response, "choices", None)
        if choices is None and isinstance(response, dict):
            choices = response.get("choices")
        if not choices:
            raise RuntimeError(f"Empty choices from model: {model_used}")

        choice0 = choices[0]
        message = getattr(choice0, "message", None)
        if message is None and isinstance(choice0, dict):
            message = choice0.get("message")
        if message is None:
            raise RuntimeError(f"Missing message from model: {model_used}")

        tool_calls = getattr(message, "tool_calls", None)
        if tool_calls is None and isinstance(message, dict):
            tool_calls = message.get("tool_calls")
        if not tool_calls:
            content = getattr(message, "content", None)
            if content is None and isinstance(message, dict):
                content = message.get("content")
            reply_text = privacy.restore((content or "")).strip()
            if log:
                log(f"(brain: {model_used})", "info")
            return reply_text or "..."

        # The model wants to call one or more tools.
        messages.append(
            {
                "role": "assistant",
                "content": getattr(message, "content", "") or "",
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in tool_calls
                ],
            }
        )

        for tc in tool_calls:
            import json as _json

            try:
                args = _json.loads(privacy.restore(tc.function.arguments or "{}"))
            except _json.JSONDecodeError:
                args = {}

            if log:
                log(f"tool call: {tc.function.name}({args})", "tool")

            result = tools.execute_tool(tc.function.name, args)

            if log:
                log(f"tool result: {result}", "tool")

            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": str(result),
                }
            )

    for item in reversed(messages):
        if item.get("role") != "tool":
            continue
        try:
            payload = json.loads(privacy.restore(item.get("content", "")))
        except (TypeError, json.JSONDecodeError):
            continue
        if payload.get("type") != "web_search_results":
            continue
        results = payload.get("results") or []
        lines = [f"I found these current sources for {payload.get('query', 'your search')}:"]
        for result in results[:8]:
            title = (result.get("title") or "Untitled source").strip()
            snippet = (result.get("snippet") or "").strip()
            url = (result.get("url") or "").strip()
            line = f"- {title}"
            if snippet:
                line += f": {snippet}"
            if url:
                line += f" ({url})"
            lines.append(line)
        if log:
            log("Tool loop limit reached; returning the latest web results.", "warn")
        return "\n".join(lines)

    if log:
        log("Tool loop limit reached without a usable result.", "warn")
    return "I could not finish that request after several tool steps. Please try a narrower question."
