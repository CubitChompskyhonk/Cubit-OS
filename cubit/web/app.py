"""FastAPI + HTMX dashboard for Cubit OS — includes API v1 and Stripe webhooks."""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from cubit.ai.briefing_builder import BriefingBuilder
from cubit.ai.conversation import ConversationalLayer
from cubit.ai.reasoner import Reasoner
from cubit.council.steward import Steward
from cubit.projects.agent import ProjectAgent
from cubit.agents.task_agent import TaskAgent
from cubit.journal.store import Journal
from cubit.chronicle.historian import Historian
from cubit.commerce.stripe_wallet import CommerceGateway
from cubit.api.router import ApiRouter

BASE = Path(__file__).resolve().parent
app = FastAPI(title="Cubit OS", version="0.1.0")
app.mount("/static", StaticFiles(directory=str(BASE / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE / "templates"))

cl = ConversationalLayer()
briefing = BriefingBuilder()
steward = Steward()
projects = ProjectAgent()
tasks = TaskAgent()
journal = Journal()
historian = Historian()
reasoner = Reasoner()
_api = ApiRouter()


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "Cubit OS", "version": "0.1.0"}


@app.get("/api/briefing")
def api_briefing():
    return briefing.build()


@app.post("/api/chat")
async def api_chat(request: Request):
    body = await request.json()
    text = body.get("message") or body.get("text") or ""
    result = cl.handle(text)
    return result


@app.post("/api/proposals/{prop_id}/approve")
def api_approve(prop_id: str):
    return cl.approve(prop_id)


@app.post("/api/proposals/{prop_id}/reject")
def api_reject(prop_id: str):
    return cl.reject(prop_id)


@app.post("/api/reason")
async def api_reason(request: Request):
    body = await request.json()
    q = body.get("question") or ""
    return reasoner.reason(q)


# ── Stripe webhook (raw body + signature) ────────────────────────────

@app.post("/api/v1/commerce/webhook/stripe")
async def stripe_webhook(request: Request):
    gw = CommerceGateway()
    if not gw.enabled:
        return JSONResponse(
            {"ok": False, "error": {"code": "commerce_disabled", "message": "Commerce disabled"}},
            status_code=503,
        )
    payload = await request.body()
    sig = request.headers.get("stripe-signature")
    try:
        result = gw.construct_and_handle_webhook(payload, sig)
        return JSONResponse({"ok": True, "api_version": "v1", "data": result})
    except Exception as e:
        return JSONResponse(
            {"ok": False, "error": {"code": "webhook_error", "message": str(e)}},
            status_code=400,
        )


@app.api_route("/api/v1/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def api_v1(path: str, request: Request):
    # Webhook handled by dedicated route above when path matches
    if path == "commerce/webhook/stripe" and request.method == "POST":
        return await stripe_webhook(request)
    body = {}
    if request.method in ("POST", "PUT", "PATCH"):
        try:
            body = await request.json()
        except Exception:
            body = {}
    query = dict(request.query_params)
    auth = request.headers.get("authorization")
    # Pass stripe signature into query for JSON webhook fallback
    if request.headers.get("stripe-signature"):
        query["stripe_signature"] = request.headers.get("stripe-signature")
    result = _api.dispatch(
        method=request.method,
        path="/" + path,
        body=body,
        query=query,
        authorization=auth,
    )
    status = 200 if result.ok else 400
    if result.error:
        if result.error.code == "unauthorized":
            status = 401
        elif result.error.code == "forbidden":
            status = 403
        elif result.error.code == "not_found":
            status = 404
        elif result.error.code == "commerce_disabled":
            status = 503
    return JSONResponse(result.to_dict(), status_code=status)


@app.get("/api/v1")
def api_v1_root():
    return {
        "ok": True,
        "api_version": "v1",
        "docs": "GET /api/v1/routes",
        "auth": "Bearer <key> or CUBIT_API_OPEN=1",
        "commerce_webhook": "/api/v1/commerce/webhook/stripe",
    }


# ── Pages ────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
def page_chat(request: Request):
    pending = cl.get_pending()
    review = steward.review()
    return templates.TemplateResponse(
        "chat.html",
        {"request": request, "pending": pending, "steward": review},
    )


@app.get("/briefing", response_class=HTMLResponse)
def page_briefing(request: Request):
    return templates.TemplateResponse(
        "briefing.html",
        {"request": request, "briefing": briefing.build(), "text": briefing.render()},
    )


@app.get("/projects", response_class=HTMLResponse)
def page_projects(request: Request):
    return templates.TemplateResponse(
        "projects.html",
        {"request": request, "projects": projects.get_projects(include_archived=True)},
    )


@app.get("/tasks", response_class=HTMLResponse)
def page_tasks(request: Request):
    return templates.TemplateResponse(
        "tasks.html",
        {"request": request, "groups": tasks.grouped_by_project()},
    )


@app.get("/journal", response_class=HTMLResponse)
def page_journal(request: Request):
    return templates.TemplateResponse(
        "journal.html",
        {"request": request, "entries": journal.recent(30)},
    )


@app.get("/chronicle", response_class=HTMLResponse)
def page_chronicle(request: Request):
    return templates.TemplateResponse(
        "chronicle.html",
        {"request": request, "events": historian.get_events()},
    )


@app.get("/reason", response_class=HTMLResponse)
def page_reason(request: Request):
    return templates.TemplateResponse("reason.html", {"request": request})


@app.get("/commerce", response_class=HTMLResponse)
def page_commerce(request: Request):
    gw = CommerceGateway()
    status = gw.status()
    wallet = gw.wallet_summary() if gw.enabled else None
    flash = None
    if request.query_params.get("paid"):
        flash = ("good", "Returned from Checkout — wallet updates when the Stripe webhook confirms payment.")
    elif request.query_params.get("cancelled"):
        flash = ("warn", "Checkout cancelled. No charge was made.")
    return templates.TemplateResponse(
        "commerce.html",
        {
            "request": request,
            "status": status,
            "wallet": wallet,
            "flash": flash,
            "active": "commerce",
        },
    )


@app.post("/commerce/checkout")
async def page_commerce_checkout(request: Request):
    gw = CommerceGateway()
    if not gw.enabled:
        return RedirectResponse("/commerce?cancelled=1", status_code=303)
    form = await request.form()
    try:
        amount = int(float(form.get("amount") or 0) * 100)
        session = gw.create_checkout(
            amount_cents=amount,
            currency=(form.get("currency") or "usd").lower(),
            description=str(form.get("description") or "Cubit OS"),
            customer_email=str(form.get("email") or "") or None,
            success_url=str(request.base_url).rstrip("/") + "/commerce?paid=1",
            cancel_url=str(request.base_url).rstrip("/") + "/commerce?cancelled=1",
        )
        url = session.get("url")
        if url and not session.get("dry_run"):
            return RedirectResponse(url, status_code=303)
        # Dry-run: show on commerce page via query
        return RedirectResponse(f"/commerce?dry_run={session.get('id')}", status_code=303)
    except Exception:
        return RedirectResponse("/commerce?cancelled=1", status_code=303)


@app.get("/cubitz", response_class=HTMLResponse)
def page_cubitz():
    """Launch Cubitz simulation (full-page)."""
    html_path = BASE / "static" / "cubitz.html"
    return HTMLResponse(html_path.read_text(encoding="utf-8"))


@app.get("/dept/cubitz", response_class=HTMLResponse)
def page_dept_cubitz(request: Request):
    """Department shell that embeds / starts Cubitz."""
    return templates.TemplateResponse(
        "cubitz_dept.html",
        {"request": request, "active": "cubitz"},
    )

@app.get("/advocate", response_class=HTMLResponse)
def page_advocate(request: Request):
    return templates.TemplateResponse("advocate.html", {"request": request})

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
