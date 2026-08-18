"""Registry: track departments and status."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cubit.utils import load_json, safe_write_json, data_root
DATA_DIR = data_root() / "registry_data"


class Registry:
    def __init__(self, data_dir: Path | str | None = None):
        self.data_dir = Path(data_dir) if data_dir else DATA_DIR
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.path = self.data_dir / "departments.json"
        if not self.path.exists():
            safe_write_json(
                self.path,
                {
                    "departments": [
                        {"name": "Steward", "description": "Are we aligned?", "status": "active"},
                        {"name": "Advisor", "description": "What should we consider?", "status": "active"},
                        {"name": "Historian", "description": "Why did we become this?", "status": "active"},
                        {"name": "Builder", "description": "How do we create?", "status": "active"},
                    ]
                },
            )

    def _load(self) -> dict[str, Any]:
        return load_json(self.path, {"departments": []})

    def _save(self, data: dict[str, Any]) -> None:
        safe_write_json(self.path, data)

    def register(
        self,
        name: str,
        description: str = "",
        status: str = "active",
    ) -> dict[str, Any]:
        data = self._load()
        depts = data.get("departments", [])
        for d in depts:
            if d.get("name") == name:
                d["description"] = description or d.get("description", "")
                d["status"] = status
                self._save(data)
                return d
        entry = {
            "name": name,
            "description": description,
            "status": status if status in ("active", "stub") else "active",
            "created": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        }
        depts.append(entry)
        data["departments"] = depts
        self._save(data)
        return entry

    def list(self) -> list[dict[str, Any]]:
        return self._load().get("departments", [])

    def get(self, name: str) -> dict[str, Any] | None:
        for d in self.list():
            if d.get("name") == name:
                return d
        return None
