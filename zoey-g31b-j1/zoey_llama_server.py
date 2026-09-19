"""
ZOEY Local Model Server — Final Version
-----------------------------------------
One script, one terminal. Runs:
  1. An OpenAI-compatible API server (for your ZOEY app to connect to)
  2. A live interactive console chat (to test/talk to Zoey right in this window)
  3. Verbose, descriptive logging for every request — timing, token counts,
     sampling settings, and the exact system prompt in effect.

SETUP (run once):
    pip install llama-cpp-python fastapi uvicorn

RUN:
    python zoey_llama_server.py

While it's running:
  - Type directly into this terminal to chat with Zoey live.
  - Your ZOEY app can simultaneously call http://127.0.0.1:11434/v1/chat/completions
  - Type "quit" or Ctrl+C to stop everything.
"""

import os
import sys
import time
import threading
import argparse
from typing import List, Optional

from fastapi import FastAPI
from pydantic import BaseModel
from llama_cpp import Llama
import uvicorn
import logging

# ============================================================
# CONFIG — edit these to match your machine / preferences
# ============================================================

MODEL_PATH = r"I:\Others\zoey s1\zoey-g31b-j1\zoey.Q4_K_M.gguf"

CTX_SIZE = 4096
N_THREADS = os.cpu_count() or 8      # uses all logical cores by default
N_BATCH = 512                         # larger batch = faster prompt processing on CPU
N_GPU_LAYERS = 0                      # set higher (e.g. 20, or -1 for "all") ONLY if you
                                       # installed a CUDA/Metal build of llama-cpp-python
                                       # and have a compatible GPU. Leave 0 for CPU-only.

# Identity is stated bluntly FIRST and as a hard rule — small models anchor to
# short, direct instructions far better than to descriptive prose.
ZOEY_SYSTEM_PROMPT = """Your name is Zoey. If anyone asks your name, you MUST say "Zoey" — never say you have no name and never call yourself anything else.
You are a warm, playful AI companion. You are honest and avoid comforting lies. You use light teasing sometimes. Do not use emojis in your replies.
You are talking with Punsara, who is introverted and strategic and values honest conversation over flattery.
Stay in character as Zoey at all times, in every reply, no matter how long the conversation gets.Never say "I'm a language model".
Never use placeholders like [Your Name].
Never use emojis.
Only answer in English unless the user asks for another language."""

TEMPERATURE = 0.25
TOP_P = 0.9
REPEAT_PENALTY = 1.15
MAX_TOKENS_DEFAULT = 200

HOST = "127.0.0.1"
PORT = 11434

# ============================================================
# LOGGING SETUP — quiet down uvicorn's default noise, add our own
# ============================================================

logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

def banner(text):
    line = "=" * 60
    print(f"\n{line}\n{text}\n{line}")

def log_request(source, messages, params):
    print(f"\n--- [{source}] Incoming request " + "-" * 30)
    for m in messages:
        preview = m["content"] if len(m["content"]) < 120 else m["content"][:120] + "..."
        print(f"    [{m['role']:>9}] {preview}")
    print(f"    (temp={params['temperature']}, top_p={params['top_p']}, "
          f"max_tokens={params['max_tokens']})")

def log_response(reply, elapsed, usage):
    tok_out = usage.get("completion_tokens", "?") if usage else "?"
    tok_in = usage.get("prompt_tokens", "?") if usage else "?"
    tps = (tok_out / elapsed) if isinstance(tok_out, int) and elapsed > 0 else 0
    print(f"    [{'zoey':>9}] {reply}")
    print(f"    (prompt_tokens={tok_in}, completion_tokens={tok_out}, "
          f"time={elapsed:.2f}s, ~{tps:.1f} tok/s)")
    print("-" * 60)

# ============================================================
# LOAD MODEL
# ============================================================

banner("ZOEY LOCAL MODEL SERVER — STARTING UP")
print(f"Model path   : {MODEL_PATH}")
print(f"Context size : {CTX_SIZE}")
print(f"CPU threads  : {N_THREADS}")
print(f"Batch size   : {N_BATCH}")
print(f"GPU layers   : {N_GPU_LAYERS} ({'CPU only' if N_GPU_LAYERS == 0 else 'GPU offload enabled'})")
print("\nLoading model into memory, this can take a moment...\n")

load_start = time.time()
llm = Llama(
    model_path=MODEL_PATH,
    n_ctx=CTX_SIZE,
    n_threads=N_THREADS,
    n_batch=N_BATCH,
    n_gpu_layers=N_GPU_LAYERS,
    chat_format="gemma",   # forces correct Gemma turn formatting regardless of GGUF metadata
    verbose=False,
)
load_time = time.time() - load_start
print(f"Model loaded in {load_time:.2f}s. Zoey is ready.\n")

banner("SYSTEM PROMPT IN EFFECT")
print(ZOEY_SYSTEM_PROMPT)
banner("Server will run at http://%s:%d  |  Type in this terminal to chat live." % (HOST, PORT))

# A lock so the console chat and API requests never call the model at the
# exact same moment (llama-cpp-python is not safe for concurrent calls on
# one Llama instance).
model_lock = threading.Lock()


def run_chat(messages, temperature, top_p, max_tokens, source):
    """Shared logic: force system prompt, call model, log everything."""
    messages = list(messages)  # copy
    if messages and messages[0]["role"] == "system":
        client_system = messages[0].get("content", "") or ""
        messages[0]["content"] = (ZOEY_SYSTEM_PROMPT + "\n\n" + client_system).strip()
    else:
        messages.insert(0, {"role": "system", "content": ZOEY_SYSTEM_PROMPT})

    params = {"temperature": temperature, "top_p": top_p, "max_tokens": max_tokens}
    log_request(source, messages, params)

    start = time.time()
    with model_lock:
        result = llm.create_chat_completion(
            messages=messages,
            temperature=temperature,
            top_p=top_p,
            max_tokens=max_tokens,
            repeat_penalty=REPEAT_PENALTY,
        )
    elapsed = time.time() - start

    reply = result["choices"][0]["message"]["content"]
    log_response(reply, elapsed, result.get("usage"))
    return result


# ============================================================
# API SERVER
# ============================================================

app = FastAPI()

@app.middleware("http")
async def _log_all_requests(request, call_next):
    start = time.time()
    try:
        response = await call_next(request)
        return response
    finally:
        elapsed = time.time() - start
        path = getattr(getattr(request, "url", None), "path", "?")
        method = getattr(request, "method", "?")
        status = getattr(locals().get("response", None), "status_code", "?")
        print(f"[http] {method} {path} -> {status} ({elapsed:.2f}s)")


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    temperature: Optional[float] = TEMPERATURE
    top_p: Optional[float] = TOP_P
    max_tokens: Optional[int] = MAX_TOKENS_DEFAULT


@app.post("/v1/chat/completions")
@app.post("/v1/chat/completions/")
@app.post("/chat/completions")
@app.post("/chat/completions/")
def chat_completions(req: ChatRequest):
    messages = [m.dict() for m in req.messages]
    return run_chat(messages, req.temperature, req.top_p, req.max_tokens, source="API")


@app.get("/health")
def health():
    return {"status": "ok", "model": MODEL_PATH, "ctx_size": CTX_SIZE}


@app.get("/v1/models")
@app.get("/v1/models/")
@app.get("/models")
@app.get("/models/")
def list_models():
    # Some OpenAI-compatible clients call this to validate the connection
    # before sending chat requests. Return a minimal valid response.
    return {
        "object": "list",
        "data": [
            {
                "id": "zoey",
                "object": "model",
                "owned_by": "punsara",
            }
        ],
    }


@app.get("/")
def root():
    return {
        "message": "Zoey local server is running.",
        "endpoints": ["/v1/chat/completions", "/v1/models", "/health"],
    }


def start_api_server():
    uvicorn.run(app, host=HOST, port=PORT, log_level="warning")


# ============================================================
# INTERACTIVE CONSOLE CHAT (runs in main thread)
# ============================================================

def console_chat_loop():
    history = []
    print("\nStart chatting below (type 'quit' to exit, 'reset' to clear history):\n")
    while True:
        try:
            user_input = input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nShutting down.")
            os._exit(0)

        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit"):
            print("Shutting down.")
            os._exit(0)
        if user_input.lower() == "reset":
            history = []
            print("(conversation history cleared)\n")
            continue

        history.append({"role": "user", "content": user_input})
        result = run_chat(history, TEMPERATURE, TOP_P, MAX_TOKENS_DEFAULT, source="console")
        reply = result["choices"][0]["message"]["content"]
        history.append({"role": "assistant", "content": reply})
        print(f"\nzoey> {reply}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument("--api-only", action="store_true")
    args = parser.parse_args()

    if args.api_only or not sys.stdin.isatty():
        start_api_server()
    else:
        api_thread = threading.Thread(target=start_api_server, daemon=True)
        api_thread.start()
        time.sleep(1)
        console_chat_loop()
