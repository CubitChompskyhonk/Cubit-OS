"""Reflection: synthesize journal + chronicle + advisor. No invented facts."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cubit.advisor.store import Advisor
from cubit.chronicle.historian import Historian
from cubit.journal.store import Journal
from cubit.utils import load_json, safe_write_json, data_root
DATA_DIR = data_root() / "reflection_data"


class Reflection:
    def __init__(
        self,
        journal: Journal | None = None,
        historian: Historian | None = None,
        advisor: Advisor | None = None,
        data_dir: Path | str | None = None,
    ):
        self.journal = journal or Journal()
        self.historian = historian or Historian()
        self.advisor = advisor or Advisor()
        self.data_dir = Path(data_dir) if data_dir else DATA_DIR
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.path = self.data_dir / "insights.json"
        if not self.path.exists():
            safe_write_json(self.path, {"insights": []})

    def add_insight(self, insight: str, source: str = "") -> dict[str, Any]:
        data = load_json(self.path, {"insights": []})
        entry = {
            "insight": insight,
            "source": source,
            "created": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        }
        data.setdefault("insights", []).append(entry)
        safe_write_json(self.path, data)
        return entry

    def synthesize(self) -> dict[str, Any]:
        """Synthesize from existing records only; do not invent facts."""
        recent_journal = self.journal.recent(5)
        recent_events = self.historian.recent_history(5)
        open_recs = self.advisor.list(status="open")
        insights = load_json(self.path, {"insights": []}).get("insights", [])[-5:]

        decisions = [e for e in recent_journal if e.get("type") == "decision"]
        lessons = [e for e in recent_journal if e.get("type") == "lesson"]

        summary_parts = []
        if decisions:
            summary_parts.append(f"{len(decisions)} recent decision(s) recorded.")
        if lessons:
            summary_parts.append(f"{len(lessons)} lesson(s) captured.")
        if recent_events:
            summary_parts.append(f"{len(recent_events)} chronicle event(s).")
        if open_recs:
            summary_parts.append(f"{len(open_recs)} open recommendation(s).")

        return {
            "summary": " ".join(summary_parts) or "No recent synthesis data.",
            "recent_decisions": decisions,
            "recent_lessons": lessons,
            "recent_events": recent_events,
            "open_recommendations": open_recs,
            "insights": insights,
        }
