"""Cubit OS Android UI — toolbar + department interfaces (stdlib HTTP).

Departments:
  Steward  — Are we aligned?
  Advisor  — What should we consider?
  Historian — Why did we become this?
  Builder  — How do we create?

Plus Chat, Briefing, Projects, Tasks.
No fastapi/uvicorn/pydantic (Android wheels).
"""
from __future__ import annotations

import json
import os
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

_server_thread: threading.Thread | None = None
_started = False
_port = 8765



def _load_cubits_html() -> str:
    candidates = [
        Path(__file__).resolve().parent / "cubit_static" / "cubits.html",
        Path(__file__).resolve().parent / "cubit" / "web" / "static" / "cubits.html",
    ]
    for c in candidates:
        if c.exists():
            return c.read_text(encoding="utf-8")
    return "<html><body style=\"background:#000;color:#55ff55;font-family:monospace;padding:2rem\"><h1>CUBITS.EXE</h1><p>Asset missing.</p></body></html>"

def _load_cubitz_html() -> str:
    candidates = [
        Path(__file__).resolve().parent / "cubit_static" / "cubitz.html",
        Path(__file__).resolve().parent / "cubit" / "web" / "static" / "cubitz.html",
    ]
    for c in candidates:
        if c.exists():
            return c.read_text(encoding="utf-8")
    return "<html><body style=\"background:#09090b;color:#e4e4e7;font-family:sans-serif;padding:2rem\"><h1>Cubitz</h1><p>Asset missing.</p></body></html>"

def _ensure_cubit_on_path() -> None:
    here = Path(__file__).resolve().parent
    if str(here) not in sys.path:
        sys.path.insert(0, str(here))


def _esc(s) -> str:
    return (
        str(s if s is not None else "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


# ── Shared CSS / chrome ──────────────────────────────────────────────

CSS = """
:root {
  --bg: #0b0d12;
  --panel: #141820;
  --panel2: #1a1f2b;
  --border: #2a3140;
  --text: #e8eaef;
  --muted: #8b93a7;
  --accent: #6c9eff;
  --accent2: #8b7cff;
  --good: #3dd68c;
  --warn: #f5a524;
  --bad: #f76b6b;
  --toolbar-h: 56px;
  --bottom-h: 64px;
  --safe-bottom: env(safe-area-inset-bottom, 0px);
}
* { box-sizing: border-box; -webkit-tap-highlight-color: transparent; }
html, body { margin: 0; padding: 0; height: 100%; }
body {
  font-family: "Segoe UI", system-ui, -apple-system, sans-serif;
  background: var(--bg);
  color: var(--text);
  line-height: 1.45;
  overflow-x: hidden;
}
a { color: var(--accent); text-decoration: none; }
button, .btn {
  font: inherit; cursor: pointer; border: none; border-radius: 10px;
  padding: 0.55rem 1rem; font-weight: 600;
  background: var(--accent); color: #0b0d12;
}
button.secondary, .btn.secondary { background: var(--panel2); color: var(--text); border: 1px solid var(--border); }
button.good { background: var(--good); color: #0b0d12; }
button.danger { background: var(--bad); color: #fff; }
button.warn { background: var(--warn); color: #0b0d12; }
button:active { opacity: 0.85; transform: scale(0.98); }
input[type=text], textarea, select {
  width: 100%; background: #0f1218; border: 1px solid var(--border);
  color: var(--text); border-radius: 10px; padding: 0.65rem 0.85rem; font: inherit;
}
textarea { min-height: 88px; resize: vertical; }
.muted { color: var(--muted); font-size: 0.9rem; }
.badge {
  display: inline-block; font-size: 0.72rem; padding: 0.18rem 0.55rem;
  border-radius: 999px; background: #252a35; color: var(--muted); font-weight: 600;
  letter-spacing: 0.02em;
}
.badge.good { background: #163527; color: var(--good); }
.badge.warn { background: #3a2a12; color: var(--warn); }
.badge.bad { background: #3a1616; color: var(--bad); }
.badge.accent { background: #1a2740; color: var(--accent); }
.card {
  background: var(--panel); border: 1px solid var(--border);
  border-radius: 14px; padding: 1rem; margin-bottom: 0.85rem;
}
.card h3 { margin: 0 0 0.35rem; font-size: 1rem; }
.stat-grid {
  display: grid; grid-template-columns: 1fr 1fr; gap: 0.65rem; margin: 0.75rem 0;
}
.stat {
  background: var(--panel2); border: 1px solid var(--border);
  border-radius: 12px; padding: 0.75rem;
}
.stat .label { font-size: 0.72rem; color: var(--muted); text-transform: uppercase; letter-spacing: 0.04em; }
.stat .value { font-size: 1.25rem; font-weight: 700; margin-top: 0.2rem; }
.row { display: flex; gap: 0.5rem; flex-wrap: wrap; align-items: center; }
.stack { display: flex; flex-direction: column; gap: 0.55rem; }
table { width: 100%; border-collapse: collapse; font-size: 0.92rem; }
th, td { text-align: left; padding: 0.55rem 0.35rem; border-bottom: 1px solid var(--border); }
th { color: var(--muted); font-weight: 500; font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.03em; }
pre { white-space: pre-wrap; font-family: ui-monospace, monospace; font-size: 0.86rem; margin: 0; }

/* Toolbar */
.toolbar {
  position: sticky; top: 0; z-index: 50;
  height: var(--toolbar-h);
  display: flex; align-items: center; gap: 0.65rem;
  padding: 0 0.85rem;
  background: linear-gradient(180deg, #12151c 0%, #0e1118 100%);
  border-bottom: 1px solid var(--border);
  box-shadow: 0 2px 12px rgba(0,0,0,0.35);
}
.toolbar .brand {
  display: flex; align-items: center; gap: 0.5rem; font-weight: 700; font-size: 1.05rem;
  flex: 1; min-width: 0;
}
.toolbar .cube {
  width: 28px; height: 28px; border-radius: 7px;
  background: linear-gradient(135deg, #6c9eff, #8b7cff);
  display: grid; place-items: center; color: #0b0d12; font-size: 0.85rem; font-weight: 800;
}
.toolbar .subtitle { font-size: 0.72rem; color: var(--muted); font-weight: 500; display: block; }
.toolbar-actions { display: flex; gap: 0.35rem; }
.icon-btn {
  width: 40px; height: 40px; border-radius: 10px; background: var(--panel2);
  border: 1px solid var(--border); color: var(--text);
  display: grid; place-items: center; padding: 0; font-size: 1.05rem;
}

/* Page shell */
.page {
  padding: 0.9rem 0.9rem calc(var(--bottom-h) + var(--safe-bottom) + 1rem);
  max-width: 720px; margin: 0 auto; min-height: calc(100vh - var(--toolbar-h));
}
.page-title { margin: 0 0 0.25rem; font-size: 1.35rem; font-weight: 700; }
.page-desc { margin: 0 0 1rem; color: var(--muted); font-size: 0.9rem; }
.section-label {
  font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.06em;
  color: var(--muted); margin: 1.1rem 0 0.5rem; font-weight: 600;
}

/* Bottom nav */
.bottom-nav {
  position: fixed; left: 0; right: 0; bottom: 0; z-index: 50;
  height: calc(var(--bottom-h) + var(--safe-bottom));
  padding-bottom: var(--safe-bottom);
  display: flex; justify-content: space-around; align-items: flex-start;
  background: #10131a; border-top: 1px solid var(--border);
  box-shadow: 0 -4px 20px rgba(0,0,0,0.35);
}
.bottom-nav a {
  flex: 1; text-align: center; padding: 0.45rem 0.15rem 0.35rem;
  color: var(--muted); font-size: 0.65rem; font-weight: 600;
  display: flex; flex-direction: column; align-items: center; gap: 0.15rem;
}
.bottom-nav a .ico { font-size: 1.2rem; line-height: 1; }
.bottom-nav a.active { color: var(--accent); }
.bottom-nav a:active { opacity: 0.8; }

/* Dept chips (secondary nav under toolbar) */
.dept-bar {
  display: flex; gap: 0.4rem; overflow-x: auto; padding: 0.55rem 0.9rem;
  background: var(--panel); border-bottom: 1px solid var(--border);
  -webkit-overflow-scrolling: touch;
}
.dept-bar::-webkit-scrollbar { display: none; }
.dept-chip {
  flex: 0 0 auto; padding: 0.4rem 0.75rem; border-radius: 999px;
  background: var(--panel2); border: 1px solid var(--border);
  color: var(--muted); font-size: 0.78rem; font-weight: 600;
}
.dept-chip.active { background: #1a2740; border-color: var(--accent); color: var(--accent); }

/* Splash */
.splash {
  position: fixed; inset: 0; z-index: 9999; background: #0b0d12;
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  transition: opacity 0.6s ease;
}
.splash.hide { opacity: 0; pointer-events: none; }
.splash .cube-big {
  width: 64px; height: 64px; border-radius: 14px;
  background: linear-gradient(135deg, #f5c542, #d4a017);
  display: flex; align-items: center; justify-content: center;
  font-weight: 900; color: #0b0d12; font-size: 1.6rem;
  box-shadow: 0 0 40px rgba(245,197,66,0.25);
  margin-bottom: 1rem;
}
.splash h1 { font-size: 1.25rem; margin: 0; }
.splash p { color: var(--muted); font-size: 0.85rem; margin-top: 0.35rem; }

/* Chat */
.chat-log {
  min-height: 220px; max-height: 42vh; overflow-y: auto;
  padding: 0.5rem; margin-bottom: 0.65rem;
}
.msg { margin-bottom: 0.7rem; white-space: pre-wrap; font-size: 0.92rem; }
.msg.user { color: var(--accent); }
.msg.bot { color: var(--text); }
.composer {
  display: flex; gap: 0.45rem; position: sticky; bottom: calc(var(--bottom-h) + var(--safe-bottom) + 0.4rem);
  background: var(--bg); padding: 0.4rem 0;
}

/* Hero / department header cards */
.hero {
  background: linear-gradient(135deg, #1a2240 0%, #1a1830 50%, #141820 100%);
  border: 1px solid var(--border); border-radius: 16px; padding: 1.15rem;
  margin-bottom: 1rem;
}
.hero .q { font-size: 0.8rem; color: var(--accent); font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; }
.hero h2 { margin: 0.25rem 0 0.35rem; font-size: 1.2rem; }
.list-item {
  display: flex; gap: 0.65rem; align-items: flex-start;
  padding: 0.75rem 0; border-bottom: 1px solid var(--border);
}
.list-item:last-child { border-bottom: none; }
.list-item .idx {
  width: 28px; height: 28px; border-radius: 8px; background: var(--panel2);
  display: grid; place-items: center; font-size: 0.75rem; color: var(--muted); flex-shrink: 0;
}
.empty { text-align: center; padding: 1.5rem 1rem; color: var(--muted); }
.form-actions { display: flex; gap: 0.5rem; margin-top: 0.65rem; }
.progress {
  height: 8px; background: #252a35; border-radius: 999px; overflow: hidden; margin-top: 0.4rem;
}
.progress > span { display: block; height: 100%; background: linear-gradient(90deg, var(--accent), var(--good)); border-radius: 999px; }
"""



def _splash() -> str:
    return """
<div class="splash" id="cubit-splash">
  <div class="cube-big">C</div>
  <h1>Cubit OS</h1>
  <p>Foundation before expansion</p>
  <audio id="boot-audio" src="/static/VOX_BIBLICAL_888.wav" preload="auto" playsinline></audio>
</div>
<script>
(function(){
  if (sessionStorage.getItem('cubit_boot_done') === '1') {
    var s0 = document.getElementById('cubit-splash');
    if (s0) s0.remove();
    return;
  }
  const s = document.getElementById('cubit-splash');
  const a = document.getElementById('boot-audio');
  let done = false;
  function enterApp(){
    if (done) return;
    done = true;
    try { sessionStorage.setItem('cubit_boot_done','1'); } catch(e) {}
    if(s){ s.classList.add('hide'); setTimeout(function(){ if(s&&s.parentNode)s.remove(); },700); }
  }
  function showTap(){
    if (!s || document.getElementById('boot-tap')) return;
    var tip = document.createElement('button');
    tip.id = 'boot-tap';
    tip.textContent = 'Enter Cubit OS';
    tip.style.cssText = 'margin-top:1.25rem;padding:0.7rem 1.4rem;border-radius:10px;border:1px solid #f59e0b;background:#f59e0b;color:#0b0d12;font-weight:800;font-size:0.95rem;cursor:pointer';
    s.appendChild(tip);
    tip.onclick = function(){ playFull(); };
  }
  function playFull(){
    if (!a) { enterApp(); return; }
    a.currentTime = 0;
    a.volume = 1.0;
    a.onended = function(){ enterApp(); };
    a.onerror = function(){ enterApp(); };
    var pr = a.play();
    if (pr && pr.then) {
      pr.then(function(){ setTimeout(function(){ if(!done) enterApp(); }, 22000); })
        .catch(function(){ showTap(); });
    } else setTimeout(enterApp, 2000);
  }
  if (a) {
    a.preload = 'auto';
    try { a.load(); } catch(e) {}
    setTimeout(function(){
      var pr = a.play();
      if (pr && pr.then) {
        pr.then(function(){
          a.onended = function(){ enterApp(); };
          setTimeout(function(){ if(!done) enterApp(); }, 22000);
        }).catch(function(){ showTap(); });
      } else showTap();
    }, 300);
  } else setTimeout(enterApp, 800);
})();
</script>
"""


def _toolbar(active: str = "") -> str:
    return f"""
<header class="toolbar">
  <div class="brand">
    <div class="cube">C</div>
    <div>
      Cubit OS
      <span class="subtitle">Operations Manager</span>
    </div>
  </div>
  <div class="toolbar-actions">
    <a class="icon-btn" href="/briefing" title="Briefing">📋</a>
    <a class="icon-btn" href="/journal" title="Founder Log">📜</a>
    <a class="icon-btn" href="/" title="Chat">💬</a>
    <a class="icon-btn" href="/dept/advocate" title="Advocate">⚑</a>
  </div>
</header>
<div class="dept-bar">
  <a class="dept-chip {'active' if active=='steward' else ''}" href="/dept/steward">Steward</a>
  <a class="dept-chip {'active' if active=='advisor' else ''}" href="/dept/advisor">Advisor</a>
  <a class="dept-chip {'active' if active=='historian' else ''}" href="/dept/historian">Historian</a>
  <a class="dept-chip {'active' if active=='builder' else ''}" href="/dept/builder">Builder</a>
  <a class="dept-chip {'active' if active=='projects' else ''}" href="/projects">Projects</a>
  <a class="dept-chip {'active' if active=='tasks' else ''}" href="/tasks">Tasks</a>
  <a class="dept-chip {'active' if active=='commerce' else ''}" href="/dept/commerce">Commerce</a>
  <a class="dept-chip {'active' if active=='cubitz' else ''}" href="/dept/cubitz">Cubitz</a>
  <a class="dept-chip {'active' if active=='cubits' else ''}" href="/dept/cubits">Cubits</a>
</div>
"""


def _bottom_nav(active: str = "chat") -> str:
    items = [
        ("chat", "/", "💬", "Chat"),
        ("steward", "/dept/steward", "◎", "Steward"),
        ("advisor", "/dept/advisor", "◇", "Advisor"),
        ("historian", "/dept/historian", "◷", "History"),
        ("builder", "/dept/builder", "▦", "Builder"),
    ]
    links = []
    for key, href, ico, label in items:
        cls = "active" if active == key else ""
        links.append(f'<a class="{cls}" href="{href}"><span class="ico">{ico}</span>{label}</a>')
    return f'<nav class="bottom-nav">{"".join(links)}</nav>'


def _shell(title: str, body: str, active_dept: str = "", active_nav: str = "chat", show_splash: bool = False) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover"/>
<meta name="theme-color" content="#0b0d12"/>
<title>{_esc(title)} — Cubit OS</title>
<style>{CSS}</style>
</head>
<body>
{_splash() if show_splash else ""}
{_toolbar(active_dept)}
<div class="page">
{body}
</div>
{_bottom_nav(active_nav)}
</body>
</html>"""


def _make_handler():
    from cubit.ai.briefing_builder import BriefingBuilder
    from cubit.ai.conversation import ConversationalLayer
    from cubit.advisor.store import Advisor
    from cubit.agents.task_agent import TaskAgent
    from cubit.builder.department import Builder
    from cubit.chronicle.historian import Historian
    from cubit.council.steward import Steward
    from cubit.journal.store import Journal
    from cubit.projects.agent import ProjectAgent
    from cubit.registry.store import Registry

    cl = ConversationalLayer()
    briefing = BriefingBuilder()
    steward = Steward()
    projects = ProjectAgent()
    tasks = TaskAgent()
    journal = Journal()
    historian = Historian()
    advisor = Advisor()
    registry = Registry()
    builder = Builder(registry=registry, historian=historian, journal=journal)

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):
            pass

        def _send(self, code: int, body: str | bytes, content_type: str = "text/html; charset=utf-8"):
            data = body.encode("utf-8") if isinstance(body, str) else body
            self.send_response(code)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(data)

        def _json(self, code: int, obj):
            self._send(code, json.dumps(obj, default=str), "application/json; charset=utf-8")

        def _read_json(self):
            n = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(n) if n else b"{}"
            try:
                return json.loads(raw.decode("utf-8") or "{}")
            except json.JSONDecodeError:
                return {}

        # ── pages ────────────────────────────────────────────────

        def _page_chat(self):
            pending = cl.get_pending()
            pending_html = ""
            if pending:
                cards = []
                for p in pending:
                    cards.append(
                        f"""<div class="card">
                        <div class="row" style="justify-content:space-between">
                          <span class="badge accent">{_esc(p.get('id'))}</span>
                          <span class="badge">{_esc(p.get('action'))}</span>
                        </div>
                        <p style="margin:.5rem 0">{_esc(p.get('description'))}</p>
                        <p class="muted" style="margin:0 0 .5rem">{_esc(p.get('risk_notes',''))}</p>
                        <div class="row">
                          <button class="good" onclick="approve('{_esc(p.get('id'))}')">Approve</button>
                          <button class="danger" onclick="reject('{_esc(p.get('id'))}')">Reject</button>
                        </div></div>"""
                    )
                pending_html = '<div class="section-label">Pending proposals</div>' + "".join(cards)

            body = f"""
            <h1 class="page-title">Chat</h1>
            <p class="page-desc">Cubit proposes. You decide. Significant actions require approval.</p>
            <div id="log" class="chat-log card"></div>
            <div class="composer">
              <input type="text" id="msg" placeholder="create project… · status · help" autocomplete="off"/>
              <button onclick="send()">Send</button>
            </div>
            {pending_html}
            <script>
            const log=document.getElementById('log');
            function add(role,t){{const d=document.createElement('div');d.className='msg '+role;
              d.textContent=(role==='user'?'You: ':'Cubit: ')+t;log.appendChild(d);log.scrollTop=log.scrollHeight;}}
            async function send(){{const i=document.getElementById('msg');const t=i.value.trim();if(!t)return;
              add('user',t);i.value='';
              const r=await fetch('/api/chat',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{message:t}})}});
              const d=await r.json();add('bot',d.message||JSON.stringify(d));
              if(d.pending&&d.pending.length) setTimeout(()=>location.reload(),400);}}
            async function approve(id){{const r=await fetch('/api/proposals/'+id+'/approve',{{method:'POST'}});
              const d=await r.json();add('bot','Approved '+id+': '+(d.execution?d.execution.status:JSON.stringify(d)));
              setTimeout(()=>location.reload(),500);}}
            async function reject(id){{const r=await fetch('/api/proposals/'+id+'/reject',{{method:'POST'}});
              const d=await r.json();add('bot',d.message||JSON.stringify(d));setTimeout(()=>location.reload(),500);}}
            document.getElementById('msg').addEventListener('keydown',e=>{{if(e.key==='Enter')send();}});
            </script>"""
            return _shell("Chat", body, active_nav="chat", show_splash=True)

        def _page_steward(self):
            r = steward.review()
            aligned = r.get("aligned")
            focus = r.get("focus_status", "")
            focus_cls = "good" if focus == "MANAGEABLE" else ("warn" if focus == "STRETCHED" else "bad")
            rate = float(r.get("execution_rate") or 0)
            body = f"""
            <div class="hero">
              <div class="q">Department · Steward</div>
              <h2>Are we aligned?</h2>
              <p class="muted" style="margin:0">Purpose, focus load, and execution health — deterministic governance, not a chat persona.</p>
            </div>
            <div class="row" style="margin-bottom:.75rem">
              <span class="badge {'good' if aligned else 'warn'}">{'Aligned' if aligned else 'Needs review'}</span>
              <span class="badge {focus_cls}">{_esc(focus)}</span>
              <span class="badge">Purpose {_esc(r.get('purpose_status'))}</span>
            </div>
            <div class="stat-grid">
              <div class="stat"><div class="label">Projects</div><div class="value">{r.get('project_count',0)}</div></div>
              <div class="stat"><div class="label">Exec rate</div><div class="value">{rate}%</div>
                <div class="progress"><span style="width:{min(rate,100)}%"></span></div>
              </div>
              <div class="stat"><div class="label">Open</div><div class="value">{r.get('task_stats',{}).get('open',0)}</div></div>
              <div class="stat"><div class="label">In progress</div><div class="value">{r.get('task_stats',{}).get('in_progress',0)}</div></div>
            </div>
            <div class="card">
              <h3>Purpose statement</h3>
              <p class="muted" style="margin:0">{_esc(r.get('purpose_statement'))}</p>
            </div>
            <div class="card">
              <h3>Focus heuristic</h3>
              <p class="muted" style="margin:0 0 .5rem">Open + in-progress tasks: <strong>{r.get('open_in_progress',0)}</strong></p>
              <p class="muted" style="margin:0">MANAGEABLE ≤3 projects & ≤8 open/IP · STRETCHED ≤6 & ≤15 · else OVERLOADED. Aligned when purpose is DEFINED and focus is not OVERLOADED.</p>
            </div>
            <div class="row">
              <a class="btn secondary" href="/briefing">Open briefing</a>
              <a class="btn secondary" href="/">Discuss in chat</a>
            </div>"""
            return _shell("Steward", body, active_dept="steward", active_nav="steward")

        def _page_advisor(self):
            open_recs = advisor.list(status="open")
            closed = advisor.list(status="closed")[:5]
            cards = []
            for rec in open_recs:
                cards.append(
                    f"""<div class="card">
                    <div class="row" style="justify-content:space-between">
                      <span class="badge accent">{_esc(rec.get('id'))}</span>
                      <span class="badge">open</span>
                    </div>
                    <h3 style="margin-top:.55rem">{_esc(rec.get('recommendation') or rec.get('observation'))}</h3>
                    <p class="muted">{_esc(rec.get('observation'))}</p>
                    <p class="muted" style="font-size:.82rem">Evidence: {_esc(rec.get('evidence') or '—')}</p>
                    <button class="secondary" onclick="closeRec('{_esc(rec.get('id'))}')">Close</button>
                    </div>"""
                )
            if not cards:
                cards.append('<div class="card empty">No open recommendations. Add one below.</div>')

            body = f"""
            <div class="hero">
              <div class="q">Department · Advisor</div>
              <h2>What should we consider?</h2>
              <p class="muted" style="margin:0">Structured recommendations — observation, evidence, action.</p>
            </div>
            <div class="section-label">Open recommendations ({len(open_recs)})</div>
            {''.join(cards)}
            <div class="section-label">Add recommendation</div>
            <div class="card stack">
              <input type="text" id="obs" placeholder="Observation"/>
              <input type="text" id="ev" placeholder="Evidence (optional)"/>
              <input type="text" id="rec" placeholder="Recommendation"/>
              <div class="form-actions">
                <button onclick="addRec()">Propose add</button>
              </div>
              <p class="muted" style="margin:0">Creates a proposal when gated; here we record via approval flow from chat, or direct add for Advisor store.</p>
            </div>
            <script>
            async function addRec(){{
              const observation=document.getElementById('obs').value.trim();
              const evidence=document.getElementById('ev').value.trim();
              const recommendation=document.getElementById('rec').value.trim();
              if(!observation&&!recommendation){{alert('Need observation or recommendation');return;}}
              const r=await fetch('/api/advisor/add',{{method:'POST',headers:{{'Content-Type':'application/json'}},
                body:JSON.stringify({{observation,evidence,recommendation}})}});
              const d=await r.json();
              if(d.error) alert(d.error); else location.reload();
            }}
            async function closeRec(id){{
              const r=await fetch('/api/advisor/close',{{method:'POST',headers:{{'Content-Type':'application/json'}},
                body:JSON.stringify({{id}})}});
              const d=await r.json();
              if(d.error) alert(d.error); else location.reload();
            }}
            </script>"""
            return _shell("Advisor", body, active_dept="advisor", active_nav="advisor")

        def _page_historian(self):
            events = list(reversed(historian.get_events()))
            decisions = [e for e in reversed(journal.recent(20)) if e.get("type") == "decision"]
            lessons = [e for e in reversed(journal.recent(20)) if e.get("type") == "lesson"]

            ev_html = []
            for e in events[:25]:
                ev_html.append(
                    f"""<div class="list-item">
                    <div class="idx">◷</div>
                    <div>
                      <div class="muted" style="font-size:.75rem">{_esc(str(e.get('date',''))[:19])}</div>
                      <strong>{_esc(e.get('event'))}</strong>
                      <div class="muted">{_esc(e.get('significance'))}</div>
                    </div></div>"""
                )
            if not ev_html:
                ev_html.append('<div class="empty">No chronicle events yet.</div>')

            dec_html = []
            for e in decisions[:10]:
                dec_html.append(
                    f"""<div class="list-item">
                    <div class="idx">✓</div>
                    <div>
                      <strong>{_esc(e.get('decision'))}</strong>
                      <div class="muted">{_esc(e.get('reason'))} · {_esc(e.get('outcome'))}</div>
                    </div></div>"""
                )

            les_html = []
            for e in lessons[:8]:
                les_html.append(
                    f"""<div class="list-item">
                    <div class="idx">★</div>
                    <div>
                      <strong>{_esc(e.get('lesson'))}</strong>
                      <div class="muted">{_esc(e.get('context'))}</div>
                    </div></div>"""
                )

            body = f"""
            <div class="hero">
              <div class="q">Department · Historian</div>
              <h2>Why did we become this?</h2>
              <p class="muted" style="margin:0">Chronicle of structural change and the journal of decisions & lessons.</p>
            </div>
            <div class="section-label">Chronicle</div>
            <div class="card">{''.join(ev_html)}</div>
            <div class="section-label">Recent decisions</div>
            <div class="card">{''.join(dec_html) if dec_html else '<div class="empty">None yet.</div>'}</div>
            <div class="section-label">Lessons</div>
            <div class="card">{''.join(les_html) if les_html else '<div class="empty">None yet.</div>'}</div>
            <div class="section-label">Record lesson</div>
            <div class="card stack">
              <input type="text" id="lesson" placeholder="Lesson learned"/>
              <input type="text" id="ctx" placeholder="Context (optional)"/>
              <div class="form-actions"><button onclick="addLesson()">Save lesson</button></div>
            </div>
            <script>
            async function addLesson(){{
              const lesson=document.getElementById('lesson').value.trim();
              const context=document.getElementById('ctx').value.trim();
              if(!lesson){{alert('Lesson required');return;}}
              const r=await fetch('/api/journal/lesson',{{method:'POST',headers:{{'Content-Type':'application/json'}},
                body:JSON.stringify({{lesson,context}})}});
              const d=await r.json();
              if(d.error) alert(d.error); else location.reload();
            }}
            </script>"""
            return _shell("Historian", body, active_dept="historian", active_nav="historian")

        def _page_builder(self):
            depts = registry.list()
            rows = []
            known = {
                "Steward": "/dept/steward",
                "Advisor": "/dept/advisor",
                "Historian": "/dept/historian",
                "Builder": "/dept/builder",
                "Cubitz": "/dept/cubitz",
                "Cubits": "/dept/cubits",
                "Commerce": "/dept/commerce",
            }
            for d in depts:
                st = d.get("status", "active")
                cls = "good" if st == "active" else "warn"
                name = d.get("name") or ""
                href = known.get(name)
                title = f'<a href="{href}"><strong>{_esc(name)}</strong></a>' if href else f'<strong>{_esc(name)}</strong>'
                rows.append(
                    f"""<div class="list-item">
                    <div class="idx">▦</div>
                    <div style="flex:1">
                      <div class="row" style="justify-content:space-between">
                        {title}
                        <span class="badge {cls}">{_esc(st)}</span>
                      </div>
                      <div class="muted">{_esc(d.get('description'))}</div>
                    </div></div>"""
                )

            body = f"""
            <div class="hero">
              <div class="q">Department · Builder</div>
              <h2>How do we create?</h2>
              <p class="muted" style="margin:0">Register departments and scaffold capabilities. Significant creates go through the Approval Gate.</p>
            </div>
            <div class="section-label">Registry ({len(depts)})</div>
            <div class="card">{''.join(rows) if rows else '<div class="empty">No departments registered.</div>'}</div>
            <div class="section-label">Propose new department</div>
            <div class="card stack">
              <input type="text" id="dname" placeholder="Department name"/>
              <input type="text" id="ddesc" placeholder="Description — what question does it answer?"/>
              <div class="form-actions">
                <button onclick="proposeDept()">Create proposal</button>
              </div>
              <p class="muted" style="margin:0">Opens a proposal (create_department). Approve from Chat or pending cards.</p>
            </div>
            <div class="section-label">Shortcuts</div>
            <div class="row">
              <a class="btn secondary" href="/projects">Projects</a>
              <a class="btn secondary" href="/tasks">Tasks</a>
              <a class="btn secondary" href="/">Chat to approve</a>
            </div>
            <script>
            async function proposeDept(){{
              const name=document.getElementById('dname').value.trim();
              const description=document.getElementById('ddesc').value.trim();
              if(!name){{alert('Name required');return;}}
              const r=await fetch('/api/builder/propose',{{method:'POST',headers:{{'Content-Type':'application/json'}},
                body:JSON.stringify({{name,description}})}});
              const d=await r.json();
              if(d.error) alert(d.error);
              else {{ alert('Proposal '+d.proposal.id+' created. Approve in Chat.'); location.href='/'; }}
            }}
            </script>"""
            return _shell("Builder", body, active_dept="builder", active_nav="builder")

        def _page_briefing(self):
            text = briefing.render()
            body = f"""
            <h1 class="page-title">Founder Briefing</h1>
            <p class="page-desc">Snapshot of identity, purpose, alignment, and recent history.</p>
            <pre class="card">{_esc(text)}</pre>
            <div class="row">
              <a class="btn secondary" href="/dept/steward">Steward detail</a>
              <a class="btn secondary" href="/">Chat</a>
            </div>"""
            return _shell("Briefing", body, active_nav="chat")

        def _page_projects(self):
            plist = projects.get_projects(include_archived=True)
            rows = "".join(
                f"<tr><td><span class='badge'>{_esc(p.get('status'))}</span></td>"
                f"<td>{_esc(p.get('name'))}</td>"
                f"<td class='muted'>{_esc(p.get('next_action'))}</td></tr>"
                for p in plist
            ) or "<tr><td colspan='3' class='muted'>No projects yet.</td></tr>"
            body = f"""
            <h1 class="page-title">Projects</h1>
            <p class="page-desc">Active concerns. Archive and status changes prefer the approval path via Chat.</p>
            <div class="card" style="overflow-x:auto">
              <table><thead><tr><th>Status</th><th>Name</th><th>Next action</th></tr></thead>
              <tbody>{rows}</tbody></table>
            </div>
            <div class="card stack">
              <div class="section-label" style="margin:0">Propose project</div>
              <input type="text" id="pname" placeholder="Project name"/>
              <div class="form-actions"><button onclick="proposeProj()">Create proposal</button></div>
            </div>
            <script>
            async function proposeProj(){{
              const name=document.getElementById('pname').value.trim();
              if(!name)return;
              const r=await fetch('/api/chat',{{method:'POST',headers:{{'Content-Type':'application/json'}},
                body:JSON.stringify({{message:'create project '+name}})}});
              const d=await r.json();
              alert(d.message||'ok'); location.href='/';
            }}
            </script>"""
            return _shell("Projects", body, active_dept="projects", active_nav="builder")

        def _page_tasks(self):
            groups = tasks.grouped_by_project()
            parts = []
            for proj, tasklist in groups.items():
                rows = "".join(
                    f"<tr><td class='muted'>{_esc(t.get('id'))}</td>"
                    f"<td><span class='badge'>{_esc(t.get('status'))}</span></td>"
                    f"<td>{_esc(t.get('title'))}</td></tr>"
                    for t in tasklist
                )
                parts.append(
                    f"<div class='section-label'>{_esc(proj)}</div>"
                    f"<div class='card' style='overflow-x:auto'><table>"
                    f"<thead><tr><th>ID</th><th>Status</th><th>Title</th></tr></thead>"
                    f"<tbody>{rows}</tbody></table></div>"
                )
            body = f"""
            <h1 class="page-title">Tasks</h1>
            <p class="page-desc">Grouped by project. Add/complete via Chat for gated approval.</p>
            {''.join(parts) if parts else '<div class="card empty">No tasks yet.</div>'}
            <div class="card stack">
              <input type="text" id="ttitle" placeholder="New task title"/>
              <input type="text" id="tproj" placeholder="Project (optional)"/>
              <div class="form-actions"><button onclick="proposeTask()">Propose task</button></div>
            </div>
            <script>
            async function proposeTask(){{
              let t=document.getElementById('ttitle').value.trim();
              const p=document.getElementById('tproj').value.trim();
              if(!t)return;
              if(p) t = t + ' --project ' + p;
              const r=await fetch('/api/chat',{{method:'POST',headers:{{'Content-Type':'application/json'}},
                body:JSON.stringify({{message:'add task '+t}})}});
              const d=await r.json();
              alert(d.message||'ok'); location.href='/';
            }}
            </script>"""
            return _shell("Tasks", body, active_dept="tasks", active_nav="builder")


        def _page_commerce(self):
            from cubit.commerce.stripe_wallet import CommerceGateway
            gw = CommerceGateway()
            st = gw.status()
            wallet = gw.wallet_summary() if gw.enabled else None
            if not st.get("enabled"):
                body = """
                <div class="hero">
                  <div class="q">Commerce</div>
                  <h2>Wallet &amp; Stripe</h2>
                  <p class="muted" style="margin:0">Optional. Free Cubit never requires payments on this device.</p>
                </div>
                <div class="card">
                  <span class="badge warn">Disabled</span>
                  <p class="muted">Enable on desktop/server with CUBIT_COMMERCE=1. Free APK has no Play Billing.</p>
                  <p class="muted">Webhook: /api/v1/commerce/webhook/stripe</p>
                </div>"""
            else:
                bal = (wallet or {}).get("balance_cents") or 0
                body = f"""
                <div class="hero">
                  <div class="q">Commerce</div>
                  <h2>Wallet</h2>
                </div>
                <div class="stat-grid">
                  <div class="stat"><div class="label">Balance</div><div class="value">{bal/100:.2f}</div></div>
                  <div class="stat"><div class="label">Paid</div><div class="value">{(wallet or {}).get('paid_count',0)}</div></div>
                </div>
                <div class="card"><p class="muted">Checkout via desktop web or API POST /api/v1/commerce/checkout</p></div>"""
            return _shell("Commerce", body, active_dept="commerce", active_nav="chat")



        def _page_advocate(self):
            body = """
            <div class="hero">
              <div class="q">Department · Advocate</div>
              <h2>Personal offline agent</h2>
              <p class="muted" style="margin:0">Queue calls, email drafts, appointments, sales, PR.</p>
            </div>
            <div class="card stack">
              <select id="atype">
                <option value="email">email</option>
                <option value="phonecall">phonecall</option>
                <option value="appointment">appointment</option>
                <option value="sales">sales</option>
                <option value="pr">pr</option>
                <option value="research">research</option>
                <option value="followup">followup</option>
              </select>
              <input id="atitle" placeholder="Title"/>
              <input id="acontact" placeholder="Contact"/>
              <input id="adetails" placeholder="Details"/>
              <div class="form-actions">
                <button onclick="advAdd()">Enqueue</button>
                <button class="secondary" onclick="advProc()">Process offline</button>
              </div>
            </div>
            <div class="card"><pre id="advout" class="muted" style="white-space:pre-wrap;font-size:0.8rem">—</pre></div>
            <script>
            async function advAdd(){
              const r=await fetch('/api/advocate/enqueue',{method:'POST',headers:{'Content-Type':'application/json'},
                body:JSON.stringify({type:document.getElementById('atype').value,title:document.getElementById('atitle').value,contact:document.getElementById('acontact').value,details:document.getElementById('adetails').value})});
              const d=await r.json(); document.getElementById('advout').textContent=JSON.stringify(d,null,2);
            }
            async function advProc(){
              const r=await fetch('/api/advocate/process',{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'});
              const d=await r.json(); document.getElementById('advout').textContent=JSON.stringify(d,null,2);
            }
            </script>
            """
            return _shell("Advocate", body, active_dept="advocate", active_nav="chat")


        def _page_cubits_dept(self):
            body = """
            <div class="hero">
              <div class="q">Department · Cubits</div>
              <h2>CUBITS.EXE</h2>
              <p class="muted" style="margin:0">MS-DOS puzzle — guide cubits to the exit. Lemmings-inspired.</p>
            </div>
            <div class="card">
              <p>Skills: Climber · Floater · Bomber · Blocker · Builder · Basher · Digger</p>
              <div class="row" style="margin-top:0.85rem;gap:0.5rem;flex-wrap:wrap">
                <a class="btn" href="/cubits" style="display:inline-block;text-align:center;padding:0.75rem 1.25rem">▶ Start CUBITS.EXE</a>
                <a class="btn secondary" href="/" style="display:inline-block;text-align:center;padding:0.75rem 1rem">Home</a>
              </div>
            </div>
            """
            return _shell("Cubits", body, active_dept="cubits", active_nav="builder")

        def _page_cubitz_dept(self):
            body = """
            <div class="hero">
              <div class="q">Department · Cubitz</div>
              <h2>Living garden simulation</h2>
              <p class="muted" style="margin:0">Tribes, lifecycle, economy pulse, Yahweh / Serpent.</p>
            </div>
            <div class="card">
              <p><strong>Cubitz</strong> is ready. Open the world to run the simulation.</p>
              <div class="row" style="margin-top:0.85rem;gap:0.5rem;flex-wrap:wrap">
                <a class="btn" href="/cubitz" style="display:inline-block;text-align:center;padding:0.75rem 1.25rem">▶ Start Cubitz</a>
                <a class="btn secondary" href="/" style="display:inline-block;text-align:center;padding:0.75rem 1rem">Home</a>
              </div>
            </div>
            <div class="card muted">
              Controls inside the game: Pause · Speed · Save/Load · Yahweh Bless · Serpent Corrupt
            </div>
            """
            return _shell("Cubitz", body, active_dept="cubitz", active_nav="builder")

        def do_GET(self):
            path = urlparse(self.path).path
            if path.startswith("/static/"):
                name = path.split("/static/", 1)[-1].split("/")[-1]
                candidates = [
                    Path(__file__).resolve().parent / "cubit_static" / name,
                    Path(__file__).resolve().parent / "cubit" / "web" / "static" / name,
                ]
                for c in candidates:
                    if c.exists() and c.is_file():
                        data = c.read_bytes()
                        ctype = "application/octet-stream"
                        if name.endswith(".wav"): ctype = "audio/wav"
                        elif name.endswith(".css"): ctype = "text/css"
                        elif name.endswith(".html"): ctype = "text/html"
                        self.send_response(200)
                        self.send_header("Content-Type", ctype)
                        self.send_header("Content-Length", str(len(data)))
                        self.send_header("Accept-Ranges", "bytes")
                        self.send_header("Cache-Control", "public, max-age=3600")
                        self.end_headers()
                        self.wfile.write(data)
                        return
                return self._send(404, "missing", content_type="text/plain")
            if path == "/cubits":
                return self._send(200, _load_cubits_html())
            if path == "/cubitz":
                return self._send(200, _load_cubitz_html())
            if path == "/api/health":
                return self._json(200, {"status": "ok", "service": "Cubit OS", "version": "0.1.0", "android": True})
            if path == "/api/briefing":
                return self._json(200, briefing.build())
            if path == "/api/steward":
                return self._json(200, steward.review())
            routes = {
                "/": self._page_chat,
                "/chat": self._page_chat,
                "/briefing": self._page_briefing,
                "/projects": self._page_projects,
                "/tasks": self._page_tasks,
                "/dept/steward": self._page_steward,
                "/dept/advisor": self._page_advisor,
                "/dept/historian": self._page_historian,
                "/dept/builder": self._page_builder,
                "/dept/commerce": self._page_commerce,
                "/dept/cubitz": self._page_cubitz_dept,
                "/dept/cubits": self._page_cubits_dept,
                "/dept/advocate": self._page_advocate,
                "/journal": self._page_historian,
                "/chronicle": self._page_historian,
            }
            fn = routes.get(path)
            if fn:
                return self._send(200, fn())
            return self._send(404, _shell("404", "<h1 class='page-title'>Not found</h1><a href='/'>Home</a>"))

        def do_POST(self):
            path = urlparse(self.path).path
            body = self._read_json()
            if path == "/api/chat":
                text = body.get("message") or body.get("text") or ""
                return self._json(200, cl.handle(text))
            if path.startswith("/api/proposals/") and path.endswith("/approve"):
                return self._json(200, cl.approve(path.split("/")[3]))
            if path.startswith("/api/proposals/") and path.endswith("/reject"):
                return self._json(200, cl.reject(path.split("/")[3]))
            if path == "/api/advisor/add":
                # Direct advisor store for mobile UX; still journals via optional gate later
                rec = advisor.add(
                    observation=body.get("observation") or "",
                    evidence=body.get("evidence") or "",
                    recommendation=body.get("recommendation") or "",
                )
                return self._json(200, {"recommendation": rec})
            if path == "/api/advisor/close":
                out = advisor.close(body.get("id") or "")
                if not out:
                    return self._json(404, {"error": "not found"})
                return self._json(200, {"recommendation": out})
            if path == "/api/journal/lesson":
                entry = journal.record_lesson(
                    lesson=body.get("lesson") or "",
                    context=body.get("context") or "",
                )
                return self._json(200, {"entry": entry})
            if path == "/api/builder/propose":
                name = (body.get("name") or "").strip()
                if not name:
                    return self._json(400, {"error": "name required"})
                prop = cl.create_proposal(
                    action="create_department",
                    description=f"Create department '{name}'",
                    params={
                        "name": name,
                        "description": body.get("description") or "",
                        "status": "active",
                        "scaffold": True,
                    },
                    risk_notes="Adds organizational surface area. Prefer foundation before expansion.",
                )
                return self._json(200, {"proposal": prop})
            return self._json(404, {"error": "not found"})

    return Handler


def start_server(port: int = 8765, data_root: str | None = None) -> str:
    global _server_thread, _started, _port
    if _started:
        return f"already running on 127.0.0.1:{_port}"

    _ensure_cubit_on_path()
    os.environ["CUBIT_ANDROID"] = "1"
    if data_root:
        Path(data_root).mkdir(parents=True, exist_ok=True)
        os.environ["CUBIT_DATA_ROOT"] = str(data_root)
    elif "CUBIT_DATA_ROOT" not in os.environ:
        fallback = Path.home() / "cubit_data"
        fallback.mkdir(parents=True, exist_ok=True)
        os.environ["CUBIT_DATA_ROOT"] = str(fallback)

    _port = int(port)
    handler_cls = _make_handler()

    def run() -> None:
        httpd = ThreadingHTTPServer(("127.0.0.1", _port), handler_cls)
        httpd.serve_forever()

    _server_thread = threading.Thread(target=run, name="cubit-http", daemon=True)
    _server_thread.start()
    _started = True
    return f"started on 127.0.0.1:{_port} data={os.environ.get('CUBIT_DATA_ROOT')}"
