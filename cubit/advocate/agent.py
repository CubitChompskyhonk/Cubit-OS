"""Advocate agent: queue and process offline work for the Founder.

Task types (local queue — no automatic external spam):
  phonecall, email, appointment, sales, pr, research, followup

Significant external sends still prefer Approval Gate proposals when
CUBIT_ADVOCATE_AUTO is not enabled. Default: queue + simulate progress offline.
"""
from __future__ import annotations

import time
import uuid
from pathlib import Path
from typing import Any

from cubit.utils import data_root, load_json, safe_write_json

TASK_TYPES = (
    "phonecall",
    "email",
    "appointment",
    "sales",
    "pr",
    "research",
    "followup",
)

STATUS = ("queued", "running", "blocked", "done", "cancelled", "failed")


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


class AdvocateAgent:
    """Personal advocate: holds a durable offline task queue for the Founder."""

    def __init__(self, data_dir: Path | str | None = None):
        root = Path(data_dir) if data_dir else data_root() / "advocate_data"
        root.mkdir(parents=True, exist_ok=True)
        self.path = root / "queue.json"
        if not self.path.exists():
            safe_write_json(
                self.path,
                {
                    "tasks": [],
                    "profile": {
                        "name": "Advocate",
                        "mandate": "Act for the Founder offline: queue calls, mail, appointments, sales, PR — report back.",
                        "mode": "offline_queue",
                    },
                    "stats": {"created": 0, "completed": 0, "failed": 0},
                },
            )

    def _load(self) -> dict[str, Any]:
        return load_json(
            self.path,
            {"tasks": [], "profile": {}, "stats": {"created": 0, "completed": 0, "failed": 0}},
        )

    def _save(self, data: dict[str, Any]) -> None:
        safe_write_json(self.path, data)

    def status(self) -> dict[str, Any]:
        data = self._load()
        tasks = data.get("tasks") or []
        by = {s: 0 for s in STATUS}
        for t in tasks:
            st = t.get("status") or "queued"
            by[st] = by.get(st, 0) + 1
        return {
            "agent": "advocate",
            "profile": data.get("profile") or {},
            "counts": by,
            "stats": data.get("stats") or {},
            "pending": [t for t in tasks if t.get("status") in ("queued", "running", "blocked")],
            "note": (
                "Offline queue agent. Tasks progress locally; external phone/email adapters "
                "are optional connectors — never silent mass outreach."
            ),
        }

    def list_tasks(self, status: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
        tasks = list(reversed(self._load().get("tasks") or []))
        if status:
            tasks = [t for t in tasks if t.get("status") == status]
        return tasks[:limit]

    def enqueue(
        self,
        task_type: str,
        title: str,
        details: str = "",
        contact: str = "",
        due: str | None = None,
        priority: str = "normal",
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        tt = (task_type or "").lower().strip()
        if tt not in TASK_TYPES:
            raise ValueError(f"task_type must be one of {TASK_TYPES}")
        if not (title or "").strip():
            raise ValueError("title required")
        data = self._load()
        task = {
            "id": f"adv-{uuid.uuid4().hex[:8]}",
            "type": tt,
            "title": title.strip(),
            "details": details or "",
            "contact": contact or "",
            "due": due,
            "priority": priority if priority in ("low", "normal", "high") else "normal",
            "status": "queued",
            "progress": 0,
            "result": None,
            "created": _now(),
            "updated": _now(),
            "metadata": metadata or {},
            "log": [f"Queued as {tt}"],
        }
        data.setdefault("tasks", []).append(task)
        data.setdefault("stats", {})
        data["stats"]["created"] = int(data["stats"].get("created") or 0) + 1
        self._save(data)
        try:
            from cubit.chronicle.historian import Historian
            Historian().record(
                event=f"Advocate queued {tt}: {title.strip()[:60]}",
                significance="Offline background work for Founder",
            )
        except Exception:
            pass
        return task

    def cancel(self, task_id: str) -> dict[str, Any] | None:
        data = self._load()
        for t in data.get("tasks") or []:
            if t.get("id") == task_id and t.get("status") in ("queued", "running", "blocked"):
                t["status"] = "cancelled"
                t["updated"] = _now()
                t.setdefault("log", []).append("Cancelled by Founder")
                self._save(data)
                return t
        return None

    def process_offline(self, max_steps: int = 5) -> dict[str, Any]:
        """Advance queued tasks while 'offline' — simulated progress, durable state.

        Does not place real phone calls or send external email. Marks work done
        with a structured result the Founder can act on when back online.
        """
        data = self._load()
        tasks = data.get("tasks") or []
        advanced = []
        steps = 0
        for t in tasks:
            if steps >= max_steps:
                break
            if t.get("status") not in ("queued", "running"):
                continue
            t["status"] = "running"
            t["progress"] = min(100, int(t.get("progress") or 0) + 34)
            t["updated"] = _now()
            t.setdefault("log", []).append(f"Offline step → {t['progress']}%")
            if t["progress"] >= 100:
                t["status"] = "done"
                t["result"] = self._simulate_result(t)
                t["log"].append("Completed offline draft/result")
                data.setdefault("stats", {})
                data["stats"]["completed"] = int(data["stats"].get("completed") or 0) + 1
                try:
                    from cubit.journal.store import Journal
                    Journal().record_decision(
                        decision=f"Advocate completed {t.get('type')}: {t.get('title')}",
                        reason="Offline queue processed",
                        outcome="done",
                        tags=["advocate", t.get("type") or ""],
                    )
                except Exception:
                    pass
            advanced.append({"id": t["id"], "status": t["status"], "progress": t["progress"]})
            steps += 1
        self._save(data)
        return {"advanced": advanced, "status": self.status()}

    def _simulate_result(self, task: dict[str, Any]) -> dict[str, Any]:
        tt = task.get("type")
        title = task.get("title") or ""
        contact = task.get("contact") or "contact"
        templates = {
            "phonecall": {
                "summary": f"Call script ready for {contact} re: {title}",
                "script": f"Opening: confirm availability. Purpose: {title}. Close: agree next step.",
                "action_required": "Founder places or approves the real call",
            },
            "email": {
                "summary": f"Draft email for {contact}: {title}",
                "draft_subject": title[:80],
                "draft_body": (task.get("details") or f"Regarding {title}.")[:500],
                "action_required": "Founder reviews and sends",
            },
            "appointment": {
                "summary": f"Appointment proposal: {title}",
                "suggested_slots": ["next business morning", "next business afternoon"],
                "action_required": "Founder confirms calendar",
            },
            "sales": {
                "summary": f"Sales outreach pack: {title}",
                "talking_points": ["value", "fit", "ask"],
                "action_required": "Founder approves outreach channel",
            },
            "pr": {
                "summary": f"PR outline: {title}",
                "angles": ["founder story", "product proof", "community"],
                "action_required": "Founder approves public message",
            },
            "research": {
                "summary": f"Research brief skeleton: {title}",
                "sections": ["context", "findings", "risks", "next questions"],
                "action_required": "Founder reviews sources",
            },
            "followup": {
                "summary": f"Follow-up checklist: {title}",
                "steps": ["acknowledge", "update status", "propose next"],
                "action_required": "Founder sends when ready",
            },
        }
        return templates.get(tt, {"summary": title, "action_required": "Founder review"})

    def get(self, task_id: str) -> dict[str, Any] | None:
        for t in self._load().get("tasks") or []:
            if t.get("id") == task_id:
                return t
        return None
