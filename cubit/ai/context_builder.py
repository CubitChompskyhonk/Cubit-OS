"""ContextBuilder: unified snapshot of organizational state."""
from __future__ import annotations

from typing import Any

from cubit.advisor.store import Advisor
from cubit.agents.task_agent import TaskAgent
from cubit.chronicle.historian import Historian
from cubit.council.steward import Steward
from cubit.journal.store import Journal
from cubit.memory.loader import MemoryLoader
from cubit.projects.agent import ProjectAgent
from cubit.reflection.engine import Reflection


class ContextBuilder:
    def __init__(self):
        self.memory = MemoryLoader()
        self.projects = ProjectAgent()
        self.tasks = TaskAgent()
        self.steward = Steward(self.memory, self.projects, self.tasks)
        self.advisor = Advisor()
        self.historian = Historian()
        self.journal = Journal()
        self.reflection = Reflection(self.journal, self.historian, self.advisor)

    def build(self) -> dict[str, Any]:
        mem = self.memory.load_all()
        steward_report = self.steward.review()
        return {
            "identity": mem["identity"],
            "purpose": mem["purpose"],
            "memories": mem["memories"],
            "projects": self.projects.get_projects(include_archived=False),
            "tasks": self.tasks.get_tasks(),
            "task_stats": self.tasks.execution_stats(),
            "chronicle": self.historian.recent_history(15),
            "recommendations": self.advisor.list(status="open"),
            "journal_recent": self.journal.recent(10),
            "reflection": self.reflection.synthesize(),
            "steward": steward_report,
        }
