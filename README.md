<p align="center">
  <img src="https://img.shields.io/badge/status-live-purple?style=for-the-badge" alt="Live">
  <img src="https://img.shields.io/badge/license-MIT-blue?style=for-the-badge" alt="MIT">
  <img src="https://img.shields.io/badge/python-3.9+-green?style=for-the-badge&logo=python" alt="Python 3.9+">
</p>

<h1 align="center">🌱 ZOEY</h1>
<p align="center"><em>A developmental intelligence, growing where no one is watching.</em></p>

---

## ⚡ Quick Start — 3 commands

```bash
# 1. Install
pip install -r requirements.txt

# 2. Add your OpenRouter key (get one at openrouter.ai/keys)
#    copy .env.example to .env and paste OPENROUTER_API_KEY=...

# 3. Wake her up
python zoey.py
```

That's it. The terminal shows the **Dream Visualizer** (memory consolidation animation), then opens:
- 🌐 **Chat UI** — http://127.0.0.1:8765
- 💻 **Terminal** — a separate console opens for typed chat + logs

---

## 🧠 What she actually is

ZOEY is **not** a chatbot. Not a wrapper. She is a **developmental AI** that begins with near-zero knowledge and learns from one conversation at a time.

| Layer | What it does |
|-------|-------------|
| 👶 Baby Zoey | Local learner. Can be wrong. Remembers being wrong. |
| 🌉 Parent Bridge | LLM teaches only when she is uncertain. Help shrinks over time. |
| 🧠 Cellular Brain | Connection strengths change via reward, not gradient descent. |
| 📜 Symbolic Mind | Readable rules with evidence. Inspectable, reversible. |
| 🌍 World Model | Predicts local transitions, measures its own surprise. |
| 🌙 Dream Cycles | Offline consolidation. Failure is processed, not erased. |
| 🧬 Growing Brain | Persisted topology. Neurons + synapses evolve per experience. |
| 🛠️ Skills | File search, web research, music, media, system, study, android… |

---

## 🎛️ Inside the Chat UI

The sidebar is a live window into Zoey's inner state:

- **Runtime** — which mind is active (online / local / files / memory), network, privacy, voice
- **Neural Growth** — generation, neurons, synapses, experiences, learned cell rules
- **Development** — stage (Newborn → Infant → Toddler → Child → Young Adult), independence score
- **World Model** — observations, surprise, habituation, predictions
- **Concept Topology** — live rendering of the concept graph
- **Activity Stream + Capabilities** — every tool route, every loaded skill

---

## 🔑 Required: OpenRouter key

Free tier works perfectly. Get one at https://openrouter.ai/keys and paste it into `.env`:

```
OPENROUTER_API_KEY=sk-or-v1-...
```

Zoey auto-falls back through several free models. If you hit rate limits and have Ollama running locally, set `LOCAL_BRAIN_FIRST=true` in `.env`.

---

## 🖥️ Commands in the terminal

| Command | What it does |
|---------|-------------|
| `/quit` `/exit` | Close Zoey |
| `/mute` `/unmute` | Toggle voice |
| `/status` | Current phase + uptime + model used |
| `/skills` | List every loaded skill and tool |
| `/baby` | Developmental growth report |
| `/help` | Full command list |

---

## 📁 Repository

```
zoey/
├── zoey.py               ← ONE ENTRY POINT · Dream Visualizer → Chat UI
├── config.py             · all tunables + .env loader
├── api.py                · OpenRouter + local brain, fallback chain
├── chat_app.py           · web UI + HTTP server + stats stream
├── console_app.py        · terminal REPL (launched by zoey.py)
├── engine.py             · voice + text orchestrator, tool loop, TTS/STT
├── mind.py               · identity unification (always "Zoey")
├── baby_zoey.py          · confidence-based local-vs-parent routing
├── growing_brain.py      · persisted topology of neurons/synapses
├── cellular_brain.py     · cellular automaton with Hebbian learning
├── symbolic_brain.py     · readable rules with evidence trails
├── world_model.py        · prediction + surprise = curiosity
├── zoey_dreams.py        · offline memory consolidation
├── skills/               · auto-discovered modules (files, web, music…)
├── piper/                · bundled offline TTS
├── zoey-g31b-j1/         · local GGUF model slot
├── requirements.txt
└── .env.example
```

---

## 🎨 Video Background

Drop a cinematic ambient video (mp4 or webm) as `bg-ambient.mp4` in the root folder. It fades in 15 seconds after page load, using `mix-blend-mode: screen` so it stays subtle and organic. If the file isn't present the UI still works perfectly with the gradient + drifting organic cells + gif layer.

---

## 🧭 Principles

1. **One identity.** No "as the language model." No handing off. She is Zoey.
2. **Growth over scale.** Interesting AI comes from memory, history, regret.
3. **Everything inspectable.** Every rule, memory, skill is plain JSON.
4. **Privacy by default.** Local learner works fully offline. `.env.example` flags every knob.
5. **Self-modification requires approval.** Zoey proposes, human decides.

---

<p align="center">
  <strong>🌱 Punsara Lab</strong><br>
  <em>Building what remembers why it is being built.</em>
</p>
