"""Steward: deterministic alignment review. Are we aligned?"""
from __future__ import annotations

from typing import Any

from cubit.agents.task_agent import TaskAgent
from cubit.memory.loader import MemoryLoader
from cubit.projects.agent import ProjectAgent


class Steward:
    def __init__(
        self,
        memory: MemoryLoader | None = None,
        projects: ProjectAgent | None = None,
        tasks: TaskAgent | None = None,
    ):
        self.memory = memory or MemoryLoader()
        self.projects = projects or ProjectAgent()
        self.tasks = tasks or TaskAgent()

    def review(self) -> dict[str, Any]:
        purpose = self.memory.load_purpose()
        purpose_status = purpose.get("status", "UNDEFINED")
        project_count = self.projects.project_count(include_archived=False)
        task_stats = self.tasks.execution_stats()
        open_ip = task_stats["open"] + task_stats["in_progress"]

        # Focus heuristic
        if project_count <= 3 and open_ip <= 8:
            focus_status = "MANAGEABLE"
        elif project_count <= 6 and open_ip <= 15:
            focus_status = "STRETCHED"
        else:
            focus_status = "OVERLOADED"

        aligned = purpose_status == "DEFINED" and focus_status in ("MANAGEABLE", "STRETCHED")

        return {
            "purpose_status": purpose_status,
            "purpose_statement": purpose.get("purpose_statement", ""),
            "project_count": project_count,
            "execution_rate": task_stats["execution_rate"],
            "focus_status": focus_status,
            "aligned": aligned,
            "task_stats": task_stats,
            "open_in_progress": open_ip,
        }
