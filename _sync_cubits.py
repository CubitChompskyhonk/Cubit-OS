from pathlib import Path

src = Path("/home/workdir/artifacts/cubit_os/cubit/web/static/cubits.html")
dst = Path("/home/workdir/artifacts/cubit_os/android/app/src/main/python/cubit_static/cubits.html")
t = src.read_text(encoding="utf-8", errors="replace")
dst.write_text(t, encoding="utf-8")
print("android_size", dst.stat().st_size)

srv_path = Path("/home/workdir/artifacts/cubit_os/android/app/src/main/python/cubit_android_server.py")
srv = srv_path.read_text(encoding="utf-8", errors="replace")
print("has_cubits_route", "/cubits" in srv)
print("has_page_cubits", "_page_cubits" in srv)
print("has_load_cubits", "_load_cubits" in srv)

# Ensure load helper and routes if missing
if "_load_cubits_html" not in srv:
    srv = srv.replace(
        "def _load_cubitz_html() -> str:",
        '''def _load_cubits_html() -> str:
    candidates = [
        Path(__file__).resolve().parent / "cubit_static" / "cubits.html",
        Path(__file__).resolve().parent / "cubit" / "web" / "static" / "cubits.html",
    ]
    for c in candidates:
        if c.exists():
            return c.read_text(encoding="utf-8")
    return "<html><body style='background:#000;color:#55ff55;font-family:monospace;padding:2rem'><h1>CUBITS.EXE</h1><p>Asset missing.</p></body></html>"

def _load_cubitz_html() -> str:'''
    )
    print("added_load_helper")

if 'href="/dept/cubits"' not in srv:
    srv = srv.replace(
        'href="/dept/cubitz">Cubitz</a>',
        'href="/dept/cubitz">Cubitz</a>\n  <a class="dept-chip {\'active\' if active==\'cubits\' else \'\'}" href="/dept/cubits">Cubits</a>',
    )
    print("added_chip")

if '"Cubits"' not in srv:
    srv = srv.replace(
        '"Cubitz": "/dept/cubitz",',
        '"Cubitz": "/dept/cubitz",\n                "Cubits": "/dept/cubits",',
    )
    print("added_builder_link")

if "_page_cubits_dept" not in srv:
    method = '''
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
                <a class="btn" href="/cubits" style="display:inline-block;text-align:center;padding:0.75rem 1.25rem">Start CUBITS.EXE</a>
                <a class="btn secondary" href="/" style="display:inline-block;text-align:center;padding:0.75rem 1rem">Home</a>
              </div>
            </div>
            """
            return _shell("Cubits", body, active_dept="cubits", active_nav="builder")

'''
    srv = srv.replace("        def _page_cubitz_dept(self):", method + "        def _page_cubitz_dept(self):")
    print("added_page")

if '"/dept/cubits": self._page_cubits_dept' not in srv:
    srv = srv.replace(
        '"/dept/cubitz": self._page_cubitz_dept,',
        '"/dept/cubitz": self._page_cubitz_dept,\n                "/dept/cubits": self._page_cubits_dept,',
    )
    print("added_route")

if 'path == "/cubits"' not in srv:
    srv = srv.replace(
        'if path == "/cubitz":\n                return self._send(200, _load_cubitz_html())',
        'if path == "/cubits":\n                return self._send(200, _load_cubits_html())\n            if path == "/cubitz":\n                return self._send(200, _load_cubitz_html())',
    )
    print("added_get")

srv_path.write_text(srv, encoding="utf-8")
print("server_written", len(srv))

# registry
reg = Path("/home/workdir/artifacts/cubit_os/cubit/registry/store.py")
rt = reg.read_text(encoding="utf-8")
if "Cubits" not in rt:
    rt = rt.replace(
        '("Cubitz", "Living garden simulation — start the world"),\n',
        '("Cubitz", "Living garden simulation — start the world"),\n    ("Cubits", "MS-DOS puzzle — save the cubits (Lemmings-inspired)"),\n',
    )
    reg.write_text(rt, encoding="utf-8")
    print("registry_ok")
else:
    print("registry_has_cubits")

# web app
app = Path("/home/workdir/artifacts/cubit_os/cubit/web/app.py")
at = app.read_text(encoding="utf-8")
if "page_cubits" not in at:
    at = at.rstrip() + '''

@app.get("/cubits", response_class=HTMLResponse)
def page_cubits():
    """Launch CUBITS.EXE (Lemmings-inspired DOS puzzle)."""
    html_path = BASE / "static" / "cubits.html"
    return HTMLResponse(html_path.read_text(encoding="utf-8"))


@app.get("/dept/cubits", response_class=HTMLResponse)
def page_dept_cubits(request: Request):
    """Department shell for CUBITS.EXE."""
    return templates.TemplateResponse(
        "cubits_dept.html",
        {"request": request, "active": "cubits"},
    )
'''
    app.write_text(at, encoding="utf-8")
    print("app_routes_added")
else:
    print("app_has_routes")

print("DONE")
