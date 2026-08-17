"""Journal: decisions and lessons."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cubit.utils import load_json, safe_write_json

DATA_DIR = Path(__file__).resolve().parent / "data"


class Journal:
    def __init__(self, data_dir: Path | str | None = None):
        self.data_dir = Path(data_dir) if data_dir else DATA_DIR
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.path = self.data_dir / "journal.json"
        if not self.path.exists():
            safe_write_json(self.path, {"entries": []})

    def _load(self) -> dict[str, Any]:
        return load_json(self.path, {"entries": []})

    def _save(self, data: dict[str, Any]) -> None:
        safe_write_json(self.path, data)

    def record_decision(
        self,
        decision: str,
        reason: str = "",
        outcome: str = "",
        related_proposal: str | None = None,
        tags: list[str] | None = None,
    ) -> dict[str, Any]:
        data = self._load()
        entry = {
            "type": "decision",
            "decision": decision,
            "reason": reason,
            "outcome": outcome,
            "related_proposal": related_proposal,
            "tags": tags or [],
            "created": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        }
        data.setdefault("entries", []).append(entry)
        self._save(data)
        return entry

    def record_lesson(
        self,
        lesson: str,
        context: str = "",
        tags: list[str] | None = None,
    ) -> dict[str, Any]:
        data = self._load()
        entry = {
            "type": "lesson",
            "lesson": lesson,
            "context": context,
            "tags": tags or [],
            "created": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        }
        data.setdefault("entries", []).append(entry)
        self._save(data)
        return entry

    def get_entries(self, entry_type: str | None = None) -> list[dict[str, Any]]:
        entries = self._load().get("entries", [])
        if entry_type:
            entries = [e for e in entries if e.get("type") == entry_type]
        return entries

    def recent(self, limit: int = 10) -> list[dict[str, Any]]:
        return self.get_entries()[-limit:]
