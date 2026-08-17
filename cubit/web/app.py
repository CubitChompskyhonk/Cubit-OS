"""FastAPI + HTMX dashboard for Cubit OS."""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
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
