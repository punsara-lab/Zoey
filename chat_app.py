"""Local browser chat interface for ZOEY.

Run with: python chat_app.py
Then open: http://127.0.0.1:8765
"""

import json
import importlib.util
import os
import subprocess
import sys
import urllib.request
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from queue import Queue

import config
import engine
import cellular_brain
import growing_brain
import skills
import supervisor
import tools
import world_model
import baby_zoey
import mind

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def sanitize_terminal_text(text):
    if text is None:
        return ""
    s = str(text)
    replacements = {
        "⚠": "WARNING",
        "⚠️": "WARNING",
        "✨": "*",
        "💤": "[sleep]",
        "🎤": "[voice]",
        "✓": "OK",
        "👶": "[infant]",
        "👦": "[child]",
        "🔊": "[sound]",
        "📡": "[network]",
        "ℹ": "INFO",
        "—": "-",
        "“": '"',
        "”": '"',
        "‘": "'",
        "’": "'",
    }
    for src, dst in replacements.items():
        s = s.replace(src, dst)
    return s.encode("ascii", "ignore").decode("ascii")


HTML = r'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Zoey | Chat</title>
<style>
* { box-sizing:border-box; }
body { margin:0; min-height:100vh; color:#eaf5f2; background:#04030a; font:12px Inter,Segoe UI,Arial,sans-serif; position:relative; overflow:hidden; }
body::before { content:''; position:fixed; inset:0; z-index:0; background:radial-gradient(ellipse at center, rgba(60,30,120,.18) 0%, rgba(6,4,16,.82) 62%, #04030a 100%); pointer-events:none; }
body::after { content:''; position:fixed; inset:0; z-index:1; background-image:url('/static/pinsnap-1407443631143203.gif'); background-repeat:no-repeat; background-position:center center; background-size:cover; mix-blend-mode:screen; opacity:.72; animation:bgfade 14s ease-in forwards; pointer-events:none; filter:saturate(1.08) contrast(1.05); }
@keyframes bgfade { from { opacity:0; } 60% { opacity:.2; } to { opacity:.72; } }
.shell { position:relative; z-index:2; width:min(1320px,100%); height:100vh; margin:auto; display:grid; grid-template-columns:minmax(420px,1fr) 380px; overflow:hidden; background:rgba(9,10,24,.58); backdrop-filter:blur(6px) saturate(1.15); -webkit-backdrop-filter:blur(6px) saturate(1.15); border-left:1px solid rgba(120,100,220,.18); border-right:1px solid rgba(120,100,220,.18); }
main { min-width:0; display:grid; grid-template-rows:58px 1fr auto; border-right:1px solid rgba(120,100,220,.22); }
.topbar { display:flex; justify-content:space-between; align-items:center; padding:0 20px; background:rgba(14,12,36,.72); border-bottom:1px solid rgba(120,100,220,.22); backdrop-filter:blur(4px); }
.topbar h1 { margin:0; color:#e5fbf2; font:600 15px Inter,Segoe UI,Arial,sans-serif; letter-spacing:.06em; }
.topbar h1::first-letter { color:#b9a2ff; text-shadow:0 0 12px rgba(140,90,255,.55); }
.topbar span { display:block; margin-top:3px; color:#9fa5c9; font:11px Consolas,monospace; }
.phase { display:inline-flex; align-items:center; gap:6px; color:#b9a2ff !important; }
.phase::before { content:''; width:7px; height:7px; background:#b9a2ff; border-radius:50%; box-shadow:0 0 0 0 rgba(180,130,255,.7); }
.phase.active::before { animation:pulse 1.2s infinite; }
@keyframes pulse { 0% { box-shadow:0 0 0 0 rgba(180,130,255,.65); } 70% { box-shadow:0 0 0 7px rgba(180,130,255,0); } 100% { box-shadow:0 0 0 0 rgba(180,130,255,0); } }
button { border:1px solid #564794; cursor:pointer; font:11px Inter,Segoe UI,Arial,sans-serif; transition:background .15s ease,color .15s ease,border-color .15s ease; }
.tool { padding:7px 11px; color:#cdbfff; background:rgba(38,28,78,.7); border-color:rgba(130,100,220,.45); }
.tool:hover { background:rgba(80,60,160,.65); color:#f3edff; }
#messages { padding:22px 24px; overflow:auto; display:flex; flex-direction:column; gap:12px; background:linear-gradient(180deg, rgba(10,8,28,.55) 0%, rgba(14,10,36,.42) 50%, rgba(18,12,44,.58) 100%); }
.message { max-width:82%; }
.message .label { margin-bottom:4px; color:#8f92bd; font:10px Consolas,monospace; letter-spacing:.08em; text-transform:uppercase; }
.message p { margin:0; padding:11px 13px; line-height:1.5; white-space:pre-wrap; border:1px solid rgba(120,100,220,.28); border-radius:12px; backdrop-filter:blur(3px); }
.message.user { align-self:flex-end; text-align:right; }
.message.user p { color:#14082a; background:rgba(185,162,255,.92); border-color:rgba(185,162,255,.95); border-bottom-right-radius:3px; box-shadow:0 3px 18px rgba(140,90,255,.22); }
.message.zoey { align-self:flex-start; }
.message.zoey p { background:rgba(20,16,48,.72); border-bottom-left-radius:3px; }
.message.system { align-self:stretch; max-width:100%; }
.message.system p { padding:6px 9px; color:#9ea3cf; background:rgba(12,10,32,.6); border-radius:6px; border-color:rgba(110,90,200,.18); font:11px Consolas,monospace; }
.composer { padding:13px 18px 15px; border-top:1px solid rgba(120,100,220,.22); background:rgba(14,12,36,.72); backdrop-filter:blur(4px); }
form { display:flex; gap:8px; }
textarea { flex:1; min-height:43px; max-height:120px; padding:10px 12px; resize:none; color:#effaf3; background:rgba(8,6,22,.7); border:1px solid rgba(120,100,220,.38); border-radius:8px; outline:none; font:12px Consolas,monospace; }
textarea:focus { border-color:#b9a2ff; box-shadow:0 0 0 2px rgba(180,130,255,.14); }
.send { padding:0 17px; color:#14082a; background:rgba(185,162,255,.92); border-color:rgba(185,162,255,.95); border-radius:8px; }
.send:hover { background:#cab3ff; }
.toolbar { display:flex; justify-content:space-between; margin-top:7px; color:#8689b5; font:10px Consolas,monospace; }
.toolbar button { padding:0; color:#b5a8e8; background:none; border:0; }
.toolbar button:hover { color:#e5ddff; }
aside { min-width:0; padding:13px; overflow:auto; background:rgba(12,10,32,.55); backdrop-filter:blur(4px); }
.panel { margin-bottom:10px; border:1px solid rgba(120,100,220,.28); border-radius:10px; background:rgba(18,14,44,.58); box-shadow:0 5px 16px rgba(0,0,0,.22); backdrop-filter:blur(3px); }
.panel h2 { margin:0; padding:9px 11px; color:#cfc2ff; background:rgba(32,24,72,.55); border-bottom:1px solid rgba(120,100,220,.26); border-radius:10px 10px 0 0; font:600 10px Consolas,monospace; letter-spacing:.1em; text-transform:uppercase; }
.panel-body { padding:9px; }
.metric-grid { display:grid; grid-template-columns:repeat(3,1fr); gap:6px; }
.metric { min-width:0; padding:8px 7px; background:rgba(12,10,30,.7); border:1px solid rgba(110,90,200,.24); border-radius:7px; }
.metric b { display:block; margin-top:3px; color:#f2edff; font:600 16px Consolas,monospace; }
.metric small { display:block; overflow:hidden; color:#8d90bd; font:9px Consolas,monospace; text-overflow:ellipsis; white-space:nowrap; }
.runtime-grid { display:grid; grid-template-columns:1fr 1fr; gap:6px; }
.runtime-item { min-width:0; padding:7px 8px; background:rgba(12,10,30,.7); border:1px solid rgba(110,90,200,.24); border-radius:7px; }
.runtime-item small { display:block; color:#8d90bd; font:9px Consolas,monospace; text-transform:uppercase; }
.runtime-item strong { display:block; overflow:hidden; margin-top:3px; color:#e5deff; font:11px Consolas,monospace; text-overflow:ellipsis; white-space:nowrap; }
.runtime-item strong.good { color:#b5f7d5; }
.runtime-item strong.warn { color:#f3dda0; }
.brain-controls { display:grid; grid-template-columns:1fr 1fr; gap:6px; margin-top:9px; }
.brain-controls button { padding:7px 5px; color:#cdbfff; background:rgba(34,24,74,.65); border-color:rgba(120,95,220,.4); border-radius:6px; }
.brain-controls button:hover { color:#14082a; background:#c9b2ff; border-color:#c9b2ff; }
.brain-controls button.primary { color:#14082a; background:rgba(185,162,255,.92); border-color:rgba(185,162,255,.95); }
.brain-controls button.primary:hover { background:#dcc9ff; }
.section-note { margin:0 0 8px; color:#8d90bd; font:10px/1.35 Consolas,monospace; }
.network { min-height:92px; display:flex; flex-wrap:wrap; align-content:center; justify-content:center; gap:6px; padding:9px; background:rgba(6,4,18,.72); border:1px solid rgba(110,90,200,.24); border-radius:7px; }
.node { display:grid; place-items:center; width:25px; height:25px; color:#14082a; background:#b9a2ff; border-radius:50%; font:9px Consolas,monospace; box-shadow:0 0 8px rgba(180,130,255,.35); }
.node.hidden { background:#f3dda0; box-shadow:0 0 8px rgba(240,200,100,.3); }
.node.output { background:#9fd8ff; box-shadow:0 0 8px rgba(120,180,255,.35); }
#activity { max-height:160px; overflow:auto; }
.event { padding:4px 0; color:#c7c1ea; border-bottom:1px solid rgba(100,85,180,.18); font:10px/1.3 Consolas,monospace; }
.event .kind { color:#cdbcff; }
#skills { max-height:185px; overflow:auto; line-height:1.45; }
.skill { padding:3px 0; color:#bbb6dd; border-bottom:1px solid rgba(100,85,180,.18); font:10px Consolas,monospace; }
.skill b { color:#cdbcff; font-weight:400; }
.news-modal { position:fixed; inset:0; display:none; align-items:center; justify-content:center; padding:20px; background:rgba(22,16,44,.65); z-index:5; backdrop-filter:blur(3px); }
.news-modal.open { display:flex; }
.news-window { width:min(760px,100%); max-height:min(720px,100%); overflow:auto; background:#fff; border:1px solid #8b82c9; box-shadow:0 12px 35px rgba(80,40,180,.28); }
.news-head { display:flex; justify-content:space-between; gap:12px; padding:14px 16px; color:#fff; background:linear-gradient(135deg,#2a1c66 0%,#1a123e 100%); }
.news-head h2 { margin:0; font-size:15px; font-weight:400; }
.news-head small { color:#c9bfff; }
.news-close { color:#fff; background:transparent; border-color:rgba(200,180,255,.55); }
.news-brief { margin:0; padding:13px 16px; line-height:1.5; background:#f3efff; border-bottom:1px solid #d7cff5; }
.news-list { padding:8px 16px 16px; }
.news-item { padding:12px 0; border-bottom:1px solid #e7e0fb; }
.news-item a { color:#4a2fa6; font-size:14px; }
.news-item p { margin:5px 0 0; color:#453e67; line-height:1.45; }
@media (max-width:850px) { body::after { background-size:cover; opacity:.55; } body { background:#0d2024; overflow:auto; } .shell { height:auto; min-height:100vh; grid-template-columns:1fr; overflow:visible; } main { height:70vh; min-height:520px; border-right:0; } aside { border-top:1px solid rgba(120,100,220,.22); } }
</style>
</head>
<body>
<div class="shell">
<main><header class="topbar"><div><h1>ZOEY</h1><span class="phase" id="engineStatus">connecting</span></div><button class="tool" id="muteButton" type="button">voice: on</button></header>
<section id="messages" aria-live="polite"><div class="message system"><div class="label">system</div><p>One mind. Memory, files, local model, and skills are internal. Talk to Zoey.</p></div></section>
<div class="composer"><form id="chatForm"><textarea id="prompt" placeholder="Type a message..." rows="1" autofocus></textarea><button class="send" type="submit">send</button></form><div class="toolbar"><span>enter = send · shift+enter = newline</span><button id="clearButton" type="button">clear chat</button></div></div></main>
<aside>
<div class="panel"><h2>runtime control</h2><div class="panel-body"><div class="runtime-grid"><div class="runtime-item"><small>mind</small><strong id="model">-</strong></div><div class="runtime-item"><small>network mode</small><strong id="networkMode">-</strong></div><div class="runtime-item"><small>privacy mode</small><strong id="privacyMode">-</strong></div><div class="runtime-item"><small>memory at rest</small><strong id="memoryEncryption">-</strong></div><div class="runtime-item"><small>local speech</small><strong id="localBrain">-</strong></div><div class="runtime-item"><small>files</small><strong id="needleState">-</strong></div><div class="runtime-item"><small>voice</small><strong id="voiceState">-</strong></div><div class="runtime-item"><small>tool calls</small><strong id="toolCalls">-</strong></div></div><div class="brain-controls"><button class="primary" data-brain="auto">zoey auto</button><button data-brain="gemma">local only</button><button data-brain="llama_cpp">llama.cpp</button><button id="startLlama">start local server</button><button id="testNeedle">test files</button></div></div></div>
<div class="panel"><h2>neural learning state</h2><div class="panel-body"><p class="section-note">Live values from Zoey's persisted growing topology and cellular brain.</p><div class="metric-grid"><div class="metric"><small>topology generation</small><b id="generation">-</b></div><div class="metric"><small>topology neurons</small><b id="neurons">-</b></div><div class="metric"><small>connections</small><b id="connections">-</b></div><div class="metric"><small>experiences</small><b id="experiences">-</b></div><div class="metric"><small>cell generation</small><b id="cellGeneration">-</b></div><div class="metric"><small>learned cell rules</small><b id="cellRules">-</b></div></div></div></div>
<div class="panel"><h2>learning</h2><div class="panel-body"><p class="section-note">Local memory answers when confidence &ge;<span id="babyConfHigh">0.75</span>. Language model teaches when &lt;<span id="babyConfLow">0.35</span>.</p><div class="metric-grid"><div class="metric"><small>stage</small><b id="babyStage">-</b></div><div class="metric"><small>symbolic rules</small><b id="babyRules">-</b></div><div class="metric"><small>world observations</small><b id="babyWorld">-</b></div><div class="metric"><small>independence</small><b id="babyInd">-</b></div><div class="metric"><small>conf high</small><b id="babyCH">-</b></div><div class="metric"><small>conf low</small><b id="babyCL">-</b></div></div><p class="section-note" style="margin-top:9px;">Type <b>/baby</b> for the learning report.</p></div></div>
<div class="panel"><h2>world model · curiosity</h2><div class="panel-body"><p class="section-note">Measures surprise = what Zoey didn't predict → drives learning priority.</p><div class="metric-grid"><div class="metric"><small>observations</small><b id="wmObs">-</b></div><div class="metric"><small>surprise</small><b id="wmSurprise">-</b></div><div class="metric"><small>habituation</small><b id="wmHabit">-</b></div><div class="metric"><small>predictions</small><b id="wmPred">-</b></div></div></div></div>
<div class="panel"><h2>concept topology</h2><div class="panel-body"><p class="section-note">Node colors: input/concept, hidden pathway, output.</p><div class="network" id="network"><span class="node">input</span><span class="node output">out</span></div></div></div>
<div class="panel"><h2>live activity</h2><div class="panel-body" id="activity"></div></div>
<div class="panel"><h2>loaded skills / tools</h2><div class="panel-body" id="skills">loading...</div></div>
</aside>
</div>
<div class="news-modal" id="newsModal"><div class="news-window"><div class="news-head"><div><h2 id="newsTitle">Web results</h2><small>Zoey research</small></div><button class="news-close" id="closeNews" type="button">close</button></div><p class="news-brief" id="newsBrief">Zoey is preparing a brief...</p><div class="news-list" id="newsList"></div></div></div>
<script>
const messages = document.querySelector('#messages');
const activity = document.querySelector('#activity');
const promptBox = document.querySelector('#prompt');
let cursor = 0;
let muted = false;
function addMessage(kind, text) { if (!text) return; const item=document.createElement('div'); item.className=`message ${kind}`; item.innerHTML=`<div class="label">${kind === 'zoey' ? 'Zoey' : kind === 'user' ? 'You' : 'System'}</div><p></p>`; item.querySelector('p').textContent=text; messages.appendChild(item); messages.scrollTop=messages.scrollHeight; }
function addActivity(event) { const item=document.createElement('div'); item.className='event'; const kind=event.level === 'system' && event.text.startsWith('ROUTE') ? 'route' : event.level; item.innerHTML=`<span class="kind">[${kind}]</span> `; const text=document.createElement('span'); text.textContent=event.text; item.appendChild(text); activity.prepend(item); while (activity.children.length > 80) activity.lastChild.remove(); }
function openNewsPanel(data) { document.querySelector('#newsTitle').textContent=data.query || 'Web results'; const items=data.results || []; document.querySelector('#newsBrief').textContent=`Found ${items.length} source${items.length === 1 ? '' : 's'}. Zoey's answer below is based on these live results.`; document.querySelector('#newsList').innerHTML=items.map(item=>`<article class="news-item"><a href="${item.url}" target="_blank" rel="noopener noreferrer">${item.title || item.url}</a><p>${item.snippet || 'No summary provided.'}</p></article>`).join(''); document.querySelector('#newsModal').classList.add('open'); }
function setRuntimeValue(id, value, tone) { const element=document.querySelector('#'+id); element.textContent=value ?? '-'; element.className=tone ? tone : ''; }
function updateState(state) { const values={generation:state.growing.generation,neurons:state.growing.neurons,connections:state.growing.connections,experiences:state.growing.experiences,cellGeneration:state.cellular.generation,cellRules:state.cellular.learned_rules}; for (const [id,value] of Object.entries(values)) document.querySelector('#'+id).textContent=value ?? '-'; const runtime=state.runtime || {}; setRuntimeValue('model',runtime.public_model || runtime.last_model_used || 'waiting'); setRuntimeValue('networkMode',runtime.offline_mode ? 'OFFLINE' : 'ONLINE',runtime.offline_mode ? 'warn' : 'good'); setRuntimeValue('privacyMode',runtime.privacy_mode || 'hybrid',runtime.privacy_mode === 'local' ? 'good' : 'warn'); setRuntimeValue('memoryEncryption',runtime.memory_encrypted ? 'encrypted' : 'plaintext',runtime.memory_encrypted ? 'good' : 'warn'); setRuntimeValue('localBrain',runtime.local_brain_enabled ? (runtime.local_brain_first ? 'first' : 'fallback') : 'disabled',runtime.local_brain_enabled ? 'good' : ''); setRuntimeValue('needleState',state.needle_available ? 'loaded' : 'unavailable',state.needle_available ? 'good' : 'warn'); setRuntimeValue('voiceState',runtime.mute ? 'muted' : (runtime.tts_provider || 'ready'),runtime.mute ? 'warn' : 'good'); setRuntimeValue('toolCalls',runtime.tool_calls ?? 0); const baby=state.baby || {}; const babyMap={babyStage:baby.stage,babyRules:baby.symbolic_rules,babyWorld:baby.world_observations,babyInd:baby.independence_score,babyCH:baby.confidence_high,babyCL:baby.confidence_low}; for (const [id,value] of Object.entries(babyMap)) document.querySelector('#'+id).textContent=value ?? '-'; const bch=document.querySelector('#babyConfHigh'); if (bch) bch.textContent=baby.confidence_high ?? '0.75'; const bcl=document.querySelector('#babyConfLow'); if (bcl) bcl.textContent=baby.confidence_low ?? '0.35'; const wm=state.world || {}; const wmMap={wmObs:wm.observations,wmSurprise:wm.surprise,wmHabit:wm.habituation,wmPred:wm.predictions}; for (const [id,value] of Object.entries(wmMap)) document.querySelector('#'+id).textContent=value ?? '-'; if (state.growing.neurons_detail) document.querySelector('#network').innerHTML=state.growing.neurons_detail.slice(0,30).map(node=>`<span class="node ${node.kind === 'hidden' ? 'hidden' : node.kind === 'output' ? 'output' : ''}" title="${node.label}">${node.kind === 'concept' ? 'c' : node.kind === 'hidden' ? 'h' : node.kind === 'output' ? 'out' : 'in'}</span>`).join(''); if (state.skills) document.querySelector('#skills').innerHTML=state.skills.map(item=>`<div class="skill"><b>${item.skill}</b><br>${item.tools.join(', ')}</div>`).join(''); }
async function poll() { try { const res=await fetch(`/api/events?after=${cursor}`); const data=await res.json(); cursor=data.cursor; for (const event of data.events) { addActivity(event); if (event.level === 'web_results') openNewsPanel(event.data); else if (event.level === 'zoey') addMessage('zoey',event.text); else if (event.level === 'user') addMessage('user',event.text); else if (event.level === 'status') { const status=document.querySelector('#engineStatus'); status.textContent=event.text; status.classList.toggle('active',/THINKING|SPEAKING|AWAKE/.test(event.text)); } } const state=await (await fetch('/api/state')).json(); updateState(state); } catch (_) {} setTimeout(poll,700); }
document.querySelector('#chatForm').addEventListener('submit', async (event) => { event.preventDefault(); const text=promptBox.value.trim(); if (!text) return; promptBox.value=''; promptBox.style.height='54px'; await fetch('/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text})}); });
promptBox.addEventListener('keydown', event => { if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); document.querySelector('#chatForm').requestSubmit(); } });
promptBox.addEventListener('input', () => { promptBox.style.height='54px'; promptBox.style.height=Math.min(promptBox.scrollHeight,140)+'px'; });
document.querySelector('#clearButton').addEventListener('click', () => { messages.innerHTML=''; });
document.querySelector('#muteButton').addEventListener('click', async () => { muted=!muted; await fetch('/api/mute',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({muted})}); document.querySelector('#muteButton').textContent=muted ? 'voice: off' : 'voice: on'; });
document.querySelectorAll('[data-brain]').forEach(button => button.addEventListener('click', async () => { await fetch('/api/brain',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({mode:button.dataset.brain})}); }));
document.querySelector('#startLlama').addEventListener('click', async () => { await fetch('/api/llama/start',{method:'POST'}); });
document.querySelector('#testNeedle').addEventListener('click', async () => { await fetch('/api/needle-test',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({query:'list recent files'})}); });
document.querySelector('#closeNews').addEventListener('click', () => document.querySelector('#newsModal').classList.remove('open'));
document.querySelector('#newsModal').addEventListener('click', event => { if (event.target.id === 'newsModal') event.target.classList.remove('open'); });
poll();
</script>
</body>
</html>'''


class ChatApp:
    def __init__(self, host="127.0.0.1", port=8765):
        self.host = host
        self.port = port
        self.queue = Queue()
        self.stop_event = threading.Event()
        self.muted = False
        self.muted_lock = threading.Lock()
        self.events = []
        self.events_lock = threading.Lock()
        self.stats = {}
        self.stats_lock = threading.Lock()
        self.supervisor = None
        self.llama_process = None

    def log(self, message, level="info"):
        if level in {"user", "zoey"}:
            event_level = level
        elif level == "status":
            event_level = "status"
        else:
            event_level = "system"
        safe_text = sanitize_terminal_text(message)
        with self.events_lock:
            self.events.append({"id": len(self.events) + 1, "level": event_level, "text": str(message)})
            self.events = self.events[-200:]
        print(f"[{level}] {safe_text}", flush=True)
        if self.supervisor and not str(message).startswith("AUTO_FIX"):
            try:
                self.supervisor.observe(level, str(message))
            except Exception:
                pass

    def route_event(self, skill, tool_name, phase, detail):
        compact = str(detail).replace("\n", " ")
        if tool_name == "web_search" and phase == "done":
            try:
                payload = json.loads(str(detail))
                if payload.get("type") == "web_search_results":
                    with self.events_lock:
                        self.events.append(
                            {
                                "id": len(self.events) + 1,
                                "level": "web_results",
                                "text": "Web search results ready",
                                "data": payload,
                            }
                        )
                        self.events = self.events[-200:]
                    return
            except (TypeError, ValueError):
                pass
        if len(compact) > 180:
            compact = compact[:177] + "..."
        self.log(f"ROUTE {skill} -> {tool_name} [{phase}] {compact}", "info")

    def set_status(self, status):
        self.log(status, "status")

    def should_mute(self):
        with self.muted_lock:
            return self.muted

    def set_muted(self, value):
        with self.muted_lock:
            self.muted = bool(value)

    def select_brain(self, brain_mode):
        brain_mode = str(brain_mode or "").lower().strip()
        if brain_mode == "auto":
            config.OFFLINE_MODE = False
            config.LOCAL_BRAIN_ENABLED = True
            config.LOCAL_BRAIN_FIRST = True
            config.LOCAL_BRAIN_BASE_URL = config._normalize_openai_base_url("http://127.0.0.1:11434")
            config.LOCAL_BRAIN_MODEL = "gemma3:1b"
            self.log("Zoey mind: AUTO (local first, online if needed).", "info")
        elif brain_mode == "gemma":
            config.OFFLINE_MODE = True
            config.LOCAL_BRAIN_ENABLED = True
            config.LOCAL_BRAIN_FIRST = True
            config.LOCAL_BRAIN_BASE_URL = config._normalize_openai_base_url("http://127.0.0.1:11434")
            config.LOCAL_BRAIN_MODEL = "gemma3:1b"
            self.log("Zoey mind: local-only speech model.", "info")
        elif brain_mode == "llama_cpp":
            config.OFFLINE_MODE = True
            config.LOCAL_BRAIN_ENABLED = True
            config.LOCAL_BRAIN_FIRST = True
            config.LOCAL_BRAIN_BASE_URL = config.LLAMA_CPP_BASE_URL
            config.LOCAL_BRAIN_MODEL = config.LLAMA_CPP_MODEL
            self.log("Zoey mind: llama.cpp speech model.", "info")
        else:
            self.log(f"Unknown brain mode: {brain_mode}", "warn")

    def start_llama(self):
        if self.llama_process and self.llama_process.poll() is None:
            self.log("llama.cpp server is already running.", "info")
            return
        script = getattr(config, "LLAMA_CPP_SERVER_SCRIPT", "")
        if not script or not os.path.exists(script):
            self.log(f"llama.cpp server script not found: {script}", "error")
            return
        try:
            self.llama_process = subprocess.Popen(
                [sys.executable, script],
                cwd=os.path.dirname(script),
            )
            self.log("Starting llama.cpp server with Zoey GGUF model...", "info")
        except Exception as exc:
            self.log(f"Could not start llama.cpp: {exc}", "error")

    def test_needle(self, query):
        result = tools.execute_tool("run_needle2_file_agent", {"query": query or "list recent files"})
        self.log(f"Files: {result}", "info")

    def report_stats(self, stats):
        with self.stats_lock:
            self.stats = dict(stats or {})

    def state(self):
        growing = growing_brain.summary()
        cellular = cellular_brain.summary()
        world = world_model.summary()
        try:
            symbolic_raw = baby_zoey.symbolic_brain.summary()
        except Exception:
            symbolic_raw = {}
        symbolic = symbolic_raw if isinstance(symbolic_raw, dict) else {}
        try:
            baby_state_raw = baby_zoey.get_state()
        except Exception:
            baby_state_raw = {}
        baby_state = baby_state_raw if isinstance(baby_state_raw, dict) else {}
        with self.stats_lock:
            runtime = dict(self.stats)
        runtime.update(
            {
                "offline_mode": bool(getattr(config, "OFFLINE_MODE", False)),
                "local_brain_enabled": bool(getattr(config, "LOCAL_BRAIN_ENABLED", False)),
                "local_brain_first": bool(getattr(config, "LOCAL_BRAIN_FIRST", False)),
                "tts_provider": getattr(config, "TTS_PROVIDER", "unknown"),
                "tool_calls": tools.get_stats().get("tool_calls", 0),
                "privacy_mode": getattr(config, "PRIVACY_MODE", "hybrid"),
                "memory_encrypted": bool(getattr(config, "ENCRYPT_MEMORY", False)),
                "local_base_url": getattr(config, "LOCAL_BRAIN_BASE_URL", ""),
                "local_model": getattr(config, "LOCAL_BRAIN_MODEL", ""),
                "public_model": mind.public_model_name(runtime.get("last_model_used") or ""),
            }
        )
        # Calculate developmental stage
        exp = int(growing.get("experiences", 0) or 0)
        if exp >= 500:
            stage = "Young Adult"
        elif exp >= 200:
            stage = "Child"
        elif exp >= 50:
            stage = "Toddler"
        elif exp >= 10:
            stage = "Infant"
        else:
            stage = "Newborn"
        symbolic_count = int(symbolic.get("rule_count") or symbolic.get("rules_count") or len(symbolic.get("rules", []) or []))
        world_obs = int(world.get("observations") or 0)
        world_surprise = float(world.get("surprise") or 0.0) if isinstance(world.get("surprise"), (int, float)) else 0.0
        independence = 0.0
        total = int(runtime.get("brain_calls", 0) or 0)
        if total > 0:
            last_model = str(runtime.get("last_model_used", "") or "")
            baby_uses = sum(1 for _k in [0] if "baby:" in last_model)
            independence = min(1.0, (baby_uses + exp / max(1, total)) / 2.0)
        return {
            "runtime": runtime,
            "growing": {
                "generation": growing.get("generation", 0),
                "neurons": len(growing.get("neurons", [])),
                "connections": len(growing.get("connections", [])),
                "experiences": exp,
                "last_reward": growing.get("last_reward"),
                "neurons_detail": growing.get("neurons", [])[:30],
            },
            "cellular": {
                "generation": cellular.get("generation", 0),
                "experiences": cellular.get("experiences", 0),
                "active_cells": cellular.get("active_cells", 0),
                "learned_rules": cellular.get("learned_rules", 0),
                "last_reward": cellular.get("last_reward"),
            },
            "world": {
                "observations": world_obs,
                "surprise": round(world_surprise, 4),
                "habituation": round(float(world.get("habituation") or 0.0), 4),
                "predictions": int(world.get("predictions") or 0),
            },
            "baby": {
                "stage": stage,
                "symbolic_rules": symbolic_count,
                "growing_experiences": exp,
                "cellular_generation": int(cellular.get("generation", 0) or 0),
                "world_observations": world_obs,
                "independence_score": round(independence, 3),
                "confidence_high": baby_zoey.CONFIDENCE_THRESHOLD_HIGH,
                "confidence_low": baby_zoey.CONFIDENCE_THRESHOLD_LOW,
                "novelty_threshold": baby_zoey.NOVELTY_THRESHOLD,
                "last_state": {
                    "growing": (baby_state.get("growing") or {}) if isinstance(baby_state.get("growing"), dict) else {},
                    "cellular": (baby_state.get("cellular") or {}) if isinstance(baby_state.get("cellular"), dict) else {},
                },
            },
            "skills": skills.catalog(),
            "needle_available": importlib.util.find_spec("needle") is not None,
            "llama_running": bool(self.llama_process and self.llama_process.poll() is None),
        }

    def run_engine(self):
        try:
            engine.run(
                log=self.log,
                set_status=self.set_status,
                should_stop=self.stop_event.is_set,
                should_mute=self.should_mute,
                report_stats=self.report_stats,
                typed_input_queue=self.queue,
            )
        except BaseException as exc:
            self.log(f"Engine stopped: {exc}", "error")

    def handler(self):
        app = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_args):
                return

            def send_body(self, status, content_type, body):
                body = body.encode("utf-8") if isinstance(body, str) else body
                self.send_response(status)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def json_body(self):
                length = int(self.headers.get("Content-Length") or "0")
                if length <= 0 or length > 64_000:
                    return {}
                try:
                    return json.loads(self.rfile.read(length).decode("utf-8"))
                except (ValueError, UnicodeDecodeError):
                    return {}

            def do_GET(self):
                parsed = self.path.split("?", 1)
                req_path = parsed[0]
                if req_path == "/":
                    self.send_body(200, "text/html; charset=utf-8", HTML)
                    return
                if req_path == "/api/events":
                    after = 0
                    try:
                        after = int(parsed[1].split("after=", 1)[1]) if "after=" in parsed[1] else 0
                    except (ValueError, IndexError):
                        pass
                    with app.events_lock:
                        events = [event for event in app.events if event["id"] > after]
                        cursor = app.events[-1]["id"] if app.events else after
                    self.send_body(200, "application/json; charset=utf-8", json.dumps({"events": events, "cursor": cursor}))
                    return
                if req_path == "/api/state":
                    self.send_body(200, "application/json; charset=utf-8", json.dumps(app.state()))
                    return
                if req_path.startswith("/static/"):
                    rel = req_path[len("/static/"):]
                    safe = os.path.normpath(rel).lstrip("\\").lstrip("/")
                    if ".." in safe.split(os.sep) or ".." in safe.split("/"):
                        self.send_body(403, "text/plain; charset=utf-8", "Forbidden")
                        return
                    full = os.path.join(BASE_DIR, safe)
                    if not os.path.isfile(full):
                        self.send_body(404, "text/plain; charset=utf-8", "Not found")
                        return
                    ext = os.path.splitext(full)[1].lower()
                    mime = {
                        ".gif": "image/gif",
                        ".png": "image/png",
                        ".jpg": "image/jpeg",
                        ".jpeg": "image/jpeg",
                        ".svg": "image/svg+xml",
                        ".webp": "image/webp",
                        ".mp4": "video/mp4",
                        ".webm": "video/webm",
                        ".css": "text/css",
                        ".js": "application/javascript",
                    }.get(ext, "application/octet-stream")
                    try:
                        with open(full, "rb") as fh:
                            data = fh.read()
                        self.send_response(200)
                        self.send_header("Content-Type", mime)
                        self.send_header("Content-Length", str(len(data)))
                        self.send_header("Cache-Control", "public, max-age=3600")
                        self.end_headers()
                        self.wfile.write(data)
                    except OSError:
                        self.send_body(500, "text/plain; charset=utf-8", "Read error")
                    return
                self.send_body(404, "text/plain; charset=utf-8", "Not found")

            def do_POST(self):
                if self.path == "/api/brain":
                    app.select_brain(app.json_body_from_request(self).get("mode"))
                    self.send_body(200, "application/json", '{"ok":true}')
                    return
                if self.path == "/api/llama/start":
                    app.start_llama()
                    self.send_body(200, "application/json", '{"ok":true}')
                    return
                if self.path == "/api/needle-test":
                    payload = app.json_body_from_request(self)
                    threading.Thread(target=app.test_needle, args=(payload.get("query"),), daemon=True).start()
                    self.send_body(200, "application/json", '{"ok":true}')
                    return
                if self.path == "/api/chat":
                    text = str(self.json_body().get("text") or "").strip()
                    if not text:
                        self.send_body(400, "application/json", '{"ok":false}')
                        return
                    app.queue.put(text)
                    self.send_body(200, "application/json", '{"ok":true}')
                    return
                if self.path == "/api/mute":
                    app.set_muted(bool(self.json_body().get("muted")))
                    self.send_body(200, "application/json", '{"ok":true}')
                    return
                self.send_body(404, "application/json", '{"ok":false}')

        return Handler

    @staticmethod
    def json_body_from_request(handler):
        length = int(handler.headers.get("Content-Length") or "0")
        if length <= 0 or length > 64_000:
            return {}
        try:
            return json.loads(handler.rfile.read(length).decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            return {}

    def run(self):
        self.supervisor = supervisor.Supervisor(self.log)
        tools.set_route_logger(self.route_event)
        threading.Thread(target=self.run_engine, daemon=True).start()
        server = ThreadingHTTPServer((self.host, self.port), self.handler())
        url = f"http://{self.host}:{self.port}"
        self.log(f"Chat interface: {url}", "info")
        try:
            console_script = os.path.join(BASE_DIR, "console_app.py")
            if os.name == "nt":
                creation_flags = getattr(subprocess, "CREATE_NEW_CONSOLE", 0)
                subprocess.Popen(["cmd", "/k", sys.executable, console_script], cwd=BASE_DIR, creationflags=creation_flags)
            else:
                subprocess.Popen([sys.executable, console_script], cwd=BASE_DIR, start_new_session=True)
        except Exception:
            pass
        try:
            webbrowser.open(url)
        except Exception:
            pass
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            self.stop_event.set()
            server.server_close()


def main():
    ChatApp(
        host=getattr(config, "CHAT_HOST", "127.0.0.1"),
        port=int(getattr(config, "CHAT_PORT", 8765)),
    ).run()


if __name__ == "__main__":
    main()
