"""ConversationalLayer: intent detection, proposals, approval flow."""
from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cubit.ai.briefing_builder import BriefingBuilder
from cubit.ai.context_builder import ContextBuilder
from cubit.council.steward import Steward
from cubit.governance.gate import ApprovalGate, SIGNIFICANT_ACTIONS
from cubit.projects.agent import ProjectAgent
from cubit.agents.task_agent import TaskAgent
from cubit.chronicle.historian import Historian
from cubit.utils import load_json, safe_write_json

PENDING_PATH = Path(__file__).resolve().parent / "pending_proposals.json"


class ConversationalLayer:
    def __init__(self):
        self.context = ContextBuilder()
        self.briefing = BriefingBuilder()
        self.steward = Steward()
        self.projects = ProjectAgent()
        self.tasks = TaskAgent()
        self.historian = Historian()
        self.gate = ApprovalGate()
        self._ensure_pending()

    def _ensure_pending(self) -> None:
        if not PENDING_PATH.exists():
            safe_write_json(PENDING_PATH, {"proposals": []})

    def _load_pending(self) -> dict[str, Any]:
        return load_json(PENDING_PATH, {"proposals": []})

    def _save_pending(self, data: dict[str, Any]) -> None:
        safe_write_json(PENDING_PATH, data)

    def _next_prop_id(self, proposals: list[dict[str, Any]]) -> str:
        max_n = 0
        for p in proposals:
            pid = p.get("id", "")
            if pid.startswith("prop-"):
                try:
                    n = int(pid.split("-", 1)[1])
                    if n > max_n:
                        max_n = n
                except ValueError:
                    pass
        return f"prop-{max_n + 1:03d}"

    def create_proposal(
        self,
        action: str,
        description: str,
        params: dict[str, Any],
        risk_notes: str = "",
    ) -> dict[str, Any]:
        data = self._load_pending()
        proposals = data.get("proposals", [])
        prop = {
            "id": self._next_prop_id(proposals),
            "action": action,
            "description": description,
            "params": params,
            "risk_notes": risk_notes or "Review carefully before approving.",
            "requires_approval": True,
            "status": "pending",
            "created": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        }
        proposals.append(prop)
        data["proposals"] = proposals
        self._save_pending(data)
        return prop

    def get_pending(self) -> list[dict[str, Any]]:
        return [p for p in self._load_pending().get("proposals", []) if p.get("status") == "pending"]

    def get_proposal(self, prop_id: str) -> dict[str, Any] | None:
        for p in self._load_pending().get("proposals", []):
            if p.get("id") == prop_id:
                return p
        return None

    def approve(self, prop_id: str) -> dict[str, Any]:
        data = self._load_pending()
        for p in data.get("proposals", []):
            if p.get("id") == prop_id and p.get("status") == "pending":
                result = self.gate.execute(p)
                p["status"] = result.get("status", "executed")
                self._save_pending(data)
                return {"proposal": p, "execution": result}
        return {"error": f"Proposal not found or not pending: {prop_id}"}

    def reject(self, prop_id: str) -> dict[str, Any]:
        data = self._load_pending()
        for p in data.get("proposals", []):
            if p.get("id") == prop_id and p.get("status") == "pending":
                p["status"] = "rejected"
                self._save_pending(data)
                return {"proposal": p, "message": "Rejected. No state change."}
        return {"error": f"Proposal not found or not pending: {prop_id}"}

    def detect_intent(self, text: str) -> str:
        t = text.strip().lower()
        if not t:
            return "unknown"
        if t in ("help", "?", "commands"):
            return "help"
        if t.startswith("approve "):
            return "approve"
        if t.startswith("reject "):
            return "reject"
        if any(k in t for k in ("briefing", "brief me", "summary")):
            return "briefing"
        if any(k in t for k in ("status", "alignment", "aligned", "steward")):
            return "status"
        if any(k in t for k in ("focus", "overloaded", "manageable")):
            return "focus"
        if any(k in t for k in ("next", "what next", "next action")):
            return "next"
        if t.startswith("create project") or t.startswith("new project") or "create a project" in t:
            return "create_project"
        if any(k in t for k in ("list projects", "projects", "show projects")):
            return "list_projects"
        if any(k in t for k in ("list tasks", "tasks", "show tasks")):
            return "list_tasks"
        if t.startswith("add task") or t.startswith("new task") or "add a task" in t:
            return "add_task"
        if any(k in t for k in ("history", "chronicle", "what happened")):
            return "history"
        if t.startswith("complete task") or t.startswith("done task"):
            return "complete_task"
        return "unknown"

    def handle(self, text: str) -> dict[str, Any]:
        intent = self.detect_intent(text)
        msg = ""
        proposal = None

        if intent == "help":
            msg = (
                "Cubit commands (chat or CLI):\n"
                "- briefing / status / focus / next\n"
                "- list projects / list tasks\n"
                "- create project <name>\n"
                "- add task <title> [--project X]\n"
                "- complete task <id>\n"
                "- history\n"
                "- approve prop-XXX / reject prop-XXX\n"
                "Significant actions create a Proposal; approve to execute."
            )
        elif intent == "briefing":
            msg = self.briefing.render()
        elif intent == "status":
            r = self.steward.review()
            msg = (
                f"Purpose: {r['purpose_status']}\n"
                f"Aligned: {'Yes' if r['aligned'] else 'No'}\n"
                f"Focus: {r['focus_status']}\n"
                f"Projects: {r['project_count']}\n"
                f"Execution rate: {r['execution_rate']}%\n"
                f"Open/In-progress tasks: {r['open_in_progress']}"
            )
        elif intent == "focus":
            r = self.steward.review()
            msg = f"Focus status: {r['focus_status']}\nProjects: {r['project_count']}, open/IP tasks: {r['open_in_progress']}"
        elif intent == "next":
            projects = self.projects.get_projects()
            if not projects:
                msg = "No active projects. Consider creating one (will require approval)."
            else:
                lines = ["Next actions:"]
                for p in projects[:5]:
                    lines.append(f"- {p['name']}: {p.get('next_action', '—')}")
                msg = "\n".join(lines)
        elif intent == "list_projects":
            projects = self.projects.get_projects()
            if not projects:
                msg = "No active projects."
            else:
                lines = ["Projects:"]
                for p in projects:
                    lines.append(f"- [{p.get('status')}] {p['name']} — next: {p.get('next_action', '—')}")
                msg = "\n".join(lines)
        elif intent == "list_tasks":
            groups = self.tasks.grouped_by_project()
            if not groups:
                msg = "No tasks."
            else:
                lines = ["Tasks by project:"]
                for proj, tasks in groups.items():
                    lines.append(f"\n## {proj}")
                    for t in tasks:
                        lines.append(f"  [{t['status']}] {t['id']}: {t['title']}")
                msg = "\n".join(lines)
        elif intent == "history":
            events = self.historian.recent_history(10)
            if not events:
                msg = "No chronicle events yet."
            else:
                lines = ["Recent history:"]
                for e in events:
                    lines.append(f"- [{e.get('date', '')[:10]}] {e.get('event', '')}")
                msg = "\n".join(lines)
        elif intent == "create_project":
            # Extract name
            m = re.search(r"(?:create|new)\s+(?:a\s+)?project\s+(.+)", text, re.I)
            name = m.group(1).strip() if m else text.replace("create project", "").strip()
            if not name:
                msg = "Please specify a project name. Example: create project Website Redesign"
            else:
                proposal = self.create_proposal(
                    action="create_project",
                    description=f"Create project '{name}'",
                    params={"name": name, "next_action": "Define first milestone", "status": "Concept"},
                    risk_notes="Adds a new active concern. Ensure capacity (focus status).",
                )
                msg = (
                    f"Proposal created: {proposal['id']}\n"
                    f"Action: create_project — {name}\n"
                    f"Risk notes: {proposal['risk_notes']}\n"
                    f"Reply: approve {proposal['id']}  or  reject {proposal['id']}"
                )
        elif intent == "add_task":
            m = re.search(r"(?:add|new)\s+(?:a\s+)?task\s+(.+)", text, re.I)
            rest = m.group(1).strip() if m else text
            project = None
            if " --project " in rest.lower() or " project " in rest.lower():
                parts = re.split(r"\s+--?project\s+", rest, flags=re.I)
                title = parts[0].strip()
                if len(parts) > 1:
                    project = parts[1].strip()
            else:
                title = rest.strip()
            if not title:
                msg = "Please specify a task title. Example: add task Write README --project Cubit OS"
            else:
                proposal = self.create_proposal(
                    action="add_task",
                    description=f"Add task '{title}'" + (f" to project {project}" if project else ""),
                    params={"title": title, "project": project, "description": ""},
                    risk_notes="Increases open work. Check focus status.",
                )
                msg = (
                    f"Proposal created: {proposal['id']}\n"
                    f"Action: add_task — {title}\n"
                    f"Reply: approve {proposal['id']}  or  reject {proposal['id']}"
                )
        elif intent == "complete_task":
            m = re.search(r"(?:complete|done)\s+task\s+(\S+)", text, re.I)
            task_id = m.group(1) if m else ""
            if not task_id:
                msg = "Please specify task id. Example: complete task task-001"
            else:
                proposal = self.create_proposal(
                    action="complete_task",
                    description=f"Complete task {task_id}",
                    params={"task_id": task_id},
                    risk_notes="Marks task done permanently (can be reviewed in journal).",
                )
                msg = (
                    f"Proposal created: {proposal['id']}\n"
                    f"Action: complete_task — {task_id}\n"
                    f"Reply: approve {proposal['id']}  or  reject {proposal['id']}"
                )
        elif intent == "approve":
            m = re.search(r"approve\s+(prop-\S+)", text, re.I)
            prop_id = m.group(1) if m else ""
            if not prop_id:
                msg = "Usage: approve prop-XXX"
            else:
                result = self.approve(prop_id)
                if "error" in result:
                    msg = result["error"]
                else:
                    msg = f"Approved {prop_id}. Execution status: {result['execution'].get('status')}"
                    if result["execution"].get("result"):
                        msg += f"\nResult: {result['execution']['result']}"
        elif intent == "reject":
            m = re.search(r"reject\s+(prop-\S+)", text, re.I)
            prop_id = m.group(1) if m else ""
            if not prop_id:
                msg = "Usage: reject prop-XXX"
            else:
                result = self.reject(prop_id)
                if "error" in result:
                    msg = result["error"]
                else:
                    msg = f"Rejected {prop_id}. No organizational state change."
        else:
            msg = (
                "I didn't catch a clear intent. Try: briefing, status, list projects, "
                "create project <name>, add task <title>, approve prop-XXX, or help."
            )

        return {
            "intent": intent,
            "message": msg,
            "proposal": proposal,
            "pending": self.get_pending(),
        }
