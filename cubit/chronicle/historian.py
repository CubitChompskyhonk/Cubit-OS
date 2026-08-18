"""Historian: workshop chronicle. Why did we become this?"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cubit.utils import load_json, safe_write_json, data_root
DATA_DIR = data_root() / "chronicle_data"


class Historian:
    def __init__(self, data_dir: Path | str | None = None):
        self.data_dir = Path(data_dir) if data_dir else DATA_DIR
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.path = self.data_dir / "workshop_chronicle.json"
        if not self.path.exists():
            safe_write_json(
                self.path,
                {
                    "events": [
                        {
                            "date": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                            "event": "Cubit OS initialized from Project Domino rebuild",
                            "significance": "Foundation established",
                        }
                    ]
                },
            )

    def _load(self) -> dict[str, Any]:
        return load_json(self.path, {"events": []})

    def _save(self, data: dict[str, Any]) -> None:
        safe_write_json(self.path, data)

    def record(self, event: str, significance: str = "") -> dict[str, Any]:
        data = self._load()
        entry = {
            "date": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "event": event,
            "significance": significance,
        }
        data.setdefault("events", []).append(entry)
        self._save(data)
        return entry

    def get_events(self) -> list[dict[str, Any]]:
        return self._load().get("events", [])

    def recent_history(self, limit: int = 10) -> list[dict[str, Any]]:
        events = self.get_events()
        return events[-limit:]
