"""Bootstrap Cubit on Android via Chaquopy — stdlib HTTP server only.

No fastapi/uvicorn/pydantic (native wheels unavailable on Android).
Serves the same control flow: chat, briefing, proposals approve/reject.
"""
from __future__ import annotations

import json
import os
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs

_server_thread: threading.Thread | None = None
_started = False
_port = 8765


def _ensure_cubit_on_path() -> None:
    here = Path(__file__).resolve().parent
    if str(here) not in sys.path:
        sys.path.insert(0, str(here))


def _html_page(title: str, body: str, steward: dict | None = None) -> str:
    focus = ""
    if steward:
        aligned = steward.get("aligned")
        badge = "Aligned" if aligned else "Review"
        focus = f"""
        <aside class="focus">
          <h3>Steward</h3>
          <p><span class="badge">{badge}</span></p>
          <p class="muted">Focus: {steward.get('focus_status')}</p>
          <p class="muted">Projects: {steward.get('project_count')}</p>
          <p class="muted">Exec rate: {steward.get('execution_rate')}%</p>
        </aside>"""
    return f"""<!DOCTYPE html>
<html lang="en"><head>
<meta charset="utf-8"/><meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>{title} — Cubit OS</title>
<style>
:root {{ --bg:#0f1115; --panel:#1a1d24; --border:#2a2f3a; --text:#e6e8ec; --muted:#8b93a7; --accent:#6c9eff; --good:#3dd68c; --bad:#f76b6b; }}
* {{ box-sizing:border-box; }}
body {{ margin:0; font-family:system-ui,sans-serif; background:var(--bg); color:var(--text); line-height:1.5; }}
a {{ color:var(--accent); text-decoration:none; }}
.layout {{ display:grid; grid-template-columns:200px 1fr 240px; min-height:100vh; }}
@media(max-width:800px) {{ .layout {{ grid-template-columns:1fr; }} .side,.focus {{ display:none; }} }}
.side,.focus {{ background:var(--panel); border-right:1px solid var(--border); padding:1rem; }}
.focus {{ border-right:none; border-left:1px solid var(--border); }}
.main {{ padding:1.25rem; max-width:900px; }}
nav a {{ display:block; padding:.4rem .6rem; color:var(--muted); border-radius:6px; margin-bottom:.2rem; }}
nav a:hover {{ background:#252a35; color:var(--text); }}
.card {{ background:var(--panel); border:1px solid var(--border); border-radius:10px; padding:1rem; margin-bottom:1rem; }}
.badge {{ display:inline-block; font-size:.75rem; padding:.15rem .5rem; border-radius:999px; background:#252a35; color:var(--muted); }}
.muted {{ color:var(--muted); font-size:.9rem; }}
input[type=text] {{ width:100%; background:#12151b; border:1px solid var(--border); color:var(--text); border-radius:8px; padding:.6rem; font:inherit; }}
button {{ background:var(--accent); color:#0b0d12; border:none; border-radius:8px; padding:.55rem 1rem; font-weight:600; cursor:pointer; font:inherit; }}
button.good {{ background:var(--good); }} button.danger {{ background:var(--bad); color:#fff; }}
.chat-log {{ min-height:280px; max-height:50vh; overflow-y:auto; white-space:pre-wrap; }}
.msg {{ margin-bottom:.75rem; }} .msg.user {{ color:var(--accent); }}
.row {{ display:flex; gap:.5rem; margin-top:.5rem; }}
pre {{ white-space:pre-wrap; }}
table {{ width:100%; border-collapse:collapse; }} th,td {{ text-align:left; padding:.5rem; border-bottom:1px solid var(--border); }}
</style></head>
<body><div class="layout">
<aside class="side"><h2>Cubit</h2><p class="muted">AI Operations Manager</p>
<nav>
<a href="/">Chat</a><a href="/briefing">Briefing</a><a href="/projects">Projects</a>
<a href="/tasks">Tasks</a><a href="/journal">Journal</a><a href="/chronicle">Chronicle</a>
</nav>
<p class="muted" style="margin-top:2rem;font-size:.8rem;">Foundation before expansion.</p>
</aside>
<main class="main">{body}</main>
{focus}
</div></body></html>"""


def _make_handler():
    from cubit.ai.briefing_builder import BriefingBuilder
    from cubit.ai.conversation import ConversationalLayer
    from cubit.council.steward import Steward
    from cubit.projects.agent import ProjectAgent
    from cubit.agents.task_agent import TaskAgent
    from cubit.journal.store import Journal
    from cubit.chronicle.historian import Historian

    cl = ConversationalLayer()
    briefing = BriefingBuilder()
    steward = Steward()
    projects = ProjectAgent()
    tasks = TaskAgent()
    journal = Journal()
    historian = Historian()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):
            pass  # quiet

        def _send(self, code: int, body: str | bytes, content_type: str = "text/html; charset=utf-8"):
            data = body.encode("utf-8") if isinstance(body, str) else body
            self.send_response(code)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
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

        def do_GET(self):
            path = urlparse(self.path).path
            if path == "/api/health":
                return self._json(200, {"status": "ok", "service": "Cubit OS", "version": "0.1.0", "android": True})
            if path == "/api/briefing":
                return self._json(200, briefing.build())
            if path == "/" or path == "/chat":
                review = steward.review()
                pending = cl.get_pending()
                pending_html = ""
                for p in pending:
                    pending_html += f"""<div class="card"><div class="muted">{p['id']}</div>
                    <div>{p.get('description','')}</div>
                    <div class="row">
                    <button class="good" onclick="approve('{p['id']}')">Approve</button>
                    <button class="danger" onclick="reject('{p['id']}')">Reject</button>
                    </div></div>"""
                body = f"""
                <h1>Chat</h1>
                <p class="muted">Cubit proposes. You decide.</p>
                <div id="log" class="chat-log card"></div>
                <div class="row">
                  <input type="text" id="msg" placeholder="briefing · create project X · approve prop-001"/>
                  <button onclick="send()">Send</button>
                </div>
                <div id="pending">{pending_html}</div>
                <script>
                const log=document.getElementById('log');
                function add(role,t){{const d=document.createElement('div');d.className='msg '+role;d.textContent=(role==='user'?'You: ':'Cubit: ')+t;log.appendChild(d);log.scrollTop=log.scrollHeight;}}
                async function send(){{const i=document.getElementById('msg');const t=i.value.trim();if(!t)return;add('user',t);i.value='';
                  const r=await fetch('/api/chat',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{message:t}})}});
                  const d=await r.json();add('bot',d.message||JSON.stringify(d));if(d.pending&&d.pending.length)location.reload();}}
                async function approve(id){{const r=await fetch('/api/proposals/'+id+'/approve',{{method:'POST'}});const d=await r.json();add('bot','Approved '+id+': '+(d.execution?d.execution.status:JSON.stringify(d)));setTimeout(()=>location.reload(),600);}}
                async function reject(id){{const r=await fetch('/api/proposals/'+id+'/reject',{{method:'POST'}});const d=await r.json();add('bot',d.message||JSON.stringify(d));setTimeout(()=>location.reload(),600);}}
                document.getElementById('msg').addEventListener('keydown',e=>{{if(e.key==='Enter')send();}});
                </script>"""
                return self._send(200, _html_page("Chat", body, review))
            if path == "/briefing":
                text = briefing.render()
                body = f"<h1>Founder Briefing</h1><pre class='card'>{_esc(text)}</pre>"
                return self._send(200, _html_page("Briefing", body))
            if path == "/projects":
                rows = "".join(
                    f"<tr><td><span class='badge'>{_esc(p.get('status',''))}</span></td>"
                    f"<td>{_esc(p.get('name',''))}</td><td class='muted'>{_esc(p.get('next_action',''))}</td></tr>"
                    for p in projects.get_projects(include_archived=True)
                ) or "<tr><td colspan='3' class='muted'>No projects yet.</td></tr>"
                body = f"<h1>Projects</h1><table><thead><tr><th>Status</th><th>Name</th><th>Next</th></tr></thead><tbody>{rows}</tbody></table>"
                return self._send(200, _html_page("Projects", body))
            if path == "/tasks":
                groups = tasks.grouped_by_project()
                parts = []
                for proj, tasklist in groups.items():
                    rows = "".join(
                        f"<tr><td class='muted'>{_esc(t.get('id',''))}</td>"
                        f"<td><span class='badge'>{_esc(t.get('status',''))}</span></td>"
                        f"<td>{_esc(t.get('title',''))}</td></tr>"
                        for t in tasklist
                    )
                    parts.append(f"<h2>{_esc(proj)}</h2><table><thead><tr><th>ID</th><th>Status</th><th>Title</th></tr></thead><tbody>{rows}</tbody></table>")
                body = "<h1>Tasks</h1>" + ("".join(parts) if parts else "<p class='muted'>No tasks yet.</p>")
                return self._send(200, _html_page("Tasks", body))
            if path == "/journal":
                entries = list(reversed(journal.recent(30)))
                cards = []
                for e in entries:
                    if e.get("type") == "decision":
                        cards.append(
                            f"<div class='card'><span class='badge'>decision</span> "
                            f"<span class='muted'>{_esc(str(e.get('created',''))[:19])}</span>"
                            f"<p><strong>{_esc(e.get('decision',''))}</strong></p>"
                            f"<p class='muted'>{_esc(e.get('reason',''))} — { _esc(e.get('outcome',''))}</p></div>"
                        )
                    else:
                        cards.append(
                            f"<div class='card'><span class='badge'>lesson</span> "
                            f"<p><strong>{_esc(e.get('lesson',''))}</strong></p>"
                            f"<p class='muted'>{_esc(e.get('context',''))}</p></div>"
                        )
                body = "<h1>Journal</h1>" + ("".join(cards) if cards else "<p class='muted'>No entries yet.</p>")
                return self._send(200, _html_page("Journal", body))
            if path == "/chronicle":
                events = list(reversed(historian.get_events()))
                cards = "".join(
                    f"<div class='card'><span class='muted'>{_esc(str(e.get('date',''))[:19])}</span>"
                    f"<p><strong>{_esc(e.get('event',''))}</strong></p>"
                    f"<p class='muted'>{_esc(e.get('significance',''))}</p></div>"
                    for e in events
                ) or "<p class='muted'>No events yet.</p>"
                body = f"<h1>Chronicle</h1>{cards}"
                return self._send(200, _html_page("Chronicle", body))
            return self._send(404, _html_page("404", "<h1>Not found</h1>"))

        def do_POST(self):
            path = urlparse(self.path).path
            if path == "/api/chat":
                body = self._read_json()
                text = body.get("message") or body.get("text") or ""
                return self._json(200, cl.handle(text))
            if path.startswith("/api/proposals/") and path.endswith("/approve"):
                prop_id = path.split("/")[3]
                return self._json(200, cl.approve(prop_id))
            if path.startswith("/api/proposals/") and path.endswith("/reject"):
                prop_id = path.split("/")[3]
                return self._json(200, cl.reject(prop_id))
            return self._json(404, {"error": "not found"})

    return Handler


def _esc(s: str) -> str:
    return (
        str(s)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


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
    handler = _make_handler()

    def run() -> None:
        httpd = ThreadingHTTPServer(("127.0.0.1", _port), handler)
        httpd.serve_forever()

    _server_thread = threading.Thread(target=run, name="cubit-http", daemon=True)
    _server_thread.start()
    _started = True
    return f"started on 127.0.0.1:{_port} data={os.environ.get('CUBIT_DATA_ROOT')}"
