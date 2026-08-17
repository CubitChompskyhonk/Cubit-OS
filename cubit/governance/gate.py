"""ApprovalGate: only path for significant execution."""
from __future__ import annotations

from typing import Any, Callable

from cubit.advisor.store import Advisor
from cubit.agents.task_agent import TaskAgent
from cubit.builder.department import Builder
from cubit.chronicle.historian import Historian
from cubit.journal.store import Journal
from cubit.projects.agent import ProjectAgent


SIGNIFICANT_ACTIONS = {
    "create_project",
    "update_project_status",
    "archive_project",
    "add_task",
    "complete_task",
    "add_recommendation",
    "record_decision",
    "create_department",
}


class ApprovalGate:
    def __init__(
        self,
        projects: ProjectAgent | None = None,
        tasks: TaskAgent | None = None,
        advisor: Advisor | None = None,
        journal: Journal | None = None,
        historian: Historian | None = None,
        builder: Builder | None = None,
    ):
        self.projects = projects or ProjectAgent()
        self.tasks = tasks or TaskAgent()
        self.advisor = advisor or Advisor()
        self.journal = journal or Journal()
        self.historian = historian or Historian()
        self.builder = builder or Builder()

    def execute(self, proposal: dict[str, Any]) -> dict[str, Any]:
        """Execute an approved proposal. Journals outcome."""
        action = proposal.get("action")
        params = proposal.get("params") or {}
        prop_id = proposal.get("id", "")

        try:
            result = self._dispatch(action, params)
            self.journal.record_decision(
                decision=f"Approved and executed: {action}",
                reason=proposal.get("description", ""),
                outcome="success",
                related_proposal=prop_id,
                tags=["approval", action],
            )
            if action in ("create_project", "create_department", "archive_project"):
                self.historian.record(
                    event=f"Executed {action}: {params}",
                    significance=proposal.get("description", action),
                )
            return {"status": "executed", "result": result, "proposal_id": prop_id}
        except Exception as e:
            self.journal.record_decision(
                decision=f"Failed execution of: {action}",
                reason=str(e),
                outcome="failed",
                related_proposal=prop_id,
                tags=["approval", "error", action],
            )
            return {"status": "failed", "error": str(e), "proposal_id": prop_id}

    def _dispatch(self, action: str, params: dict[str, Any]) -> Any:
        if action == "create_project":
            return self.projects.create_project(
                name=params["name"],
                next_action=params.get("next_action", ""),
                status=params.get("status", "Concept"),
            )
        if action == "update_project_status":
            return self.projects.update_status(params["name"], params["status"])
        if action == "archive_project":
            return self.projects.archive_project(params["name"])
        if action == "add_task":
            return self.tasks.add_task(
                title=params["title"],
                description=params.get("description", ""),
                project=params.get("project"),
                status=params.get("status", "open"),
            )
        if action == "complete_task":
            return self.tasks.complete_task(params["task_id"])
        if action == "add_recommendation":
            return self.advisor.add(
                observation=params["observation"],
                evidence=params.get("evidence", ""),
                recommendation=params.get("recommendation", ""),
            )
        if action == "record_decision":
            return self.journal.record_decision(
                decision=params["decision"],
                reason=params.get("reason", ""),
                outcome=params.get("outcome", ""),
                tags=params.get("tags"),
            )
        if action == "create_department":
            return self.builder.create_department(
                name=params["name"],
                description=params.get("description", ""),
                status=params.get("status", "active"),
                scaffold=params.get("scaffold", True),
            )
        raise ValueError(f"Unknown or non-executable action: {action}")
