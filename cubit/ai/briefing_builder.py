"""BriefingBuilder: Founder-facing summary."""
from __future__ import annotations

from typing import Any

from cubit.ai.context_builder import ContextBuilder
from cubit.council.steward import Steward
from cubit.memory.loader import MemoryLoader
from cubit.projects.agent import ProjectAgent
from cubit.agents.task_agent import TaskAgent
from cubit.chronicle.historian import Historian
from cubit.advisor.store import Advisor


class BriefingBuilder:
    def __init__(self):
        self.memory = MemoryLoader()
        self.projects = ProjectAgent()
        self.tasks = TaskAgent()
        self.steward = Steward(self.memory, self.projects, self.tasks)
        self.historian = Historian()
        self.advisor = Advisor()

    def build(self) -> dict[str, Any]:
        identity = self.memory.load_identity()
        purpose = self.memory.load_purpose()
        review = self.steward.review()
        return {
            "identity": identity,
            "mission": identity.get("mission", ""),
            "purpose_status": review["purpose_status"],
            "purpose_statement": purpose.get("purpose_statement", ""),
            "project_count": review["project_count"],
            "execution_rate": review["execution_rate"],
            "focus_status": review["focus_status"],
            "aligned": review["aligned"],
            "recent_history": self.historian.recent_history(5),
            "recommendations": self.advisor.list(status="open")[:5],
            "task_stats": review["task_stats"],
        }

    def render(self) -> str:
        b = self.build()
        lines = [
            f"# Cubit Briefing",
            f"",
            f"**{b['identity'].get('name', 'Cubit')}** — {b['identity'].get('role', '')}",
            f"Mission: {b['mission']}",
            f"",
            f"## Purpose",
            f"Status: {b['purpose_status']}",
            f"{b['purpose_statement']}",
            f"",
            f"## Alignment",
            f"Aligned: {'Yes' if b['aligned'] else 'No'}",
            f"Focus: {b['focus_status']}",
            f"Projects (active): {b['project_count']}",
            f"Execution rate: {b['execution_rate']}%",
            f"Tasks — open: {b['task_stats']['open']}, in progress: {b['task_stats']['in_progress']}, done: {b['task_stats']['done']}",
            f"",
            f"## Recent History",
        ]
        for e in b["recent_history"]:
            lines.append(f"- [{e.get('date', '')[:10]}] {e.get('event', '')}")
        if b["recommendations"]:
            lines.append("")
            lines.append("## Open Recommendations")
            for r in b["recommendations"]:
                lines.append(f"- {r.get('id')}: {r.get('recommendation') or r.get('observation')}")
        lines.append("")
        lines.append("---")
        lines.append("Foundation before expansion. Cubit proposes; Founder decides.")
        return "\n".join(lines)
