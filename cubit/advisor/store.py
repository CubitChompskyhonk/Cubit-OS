"""Advisor: structured recommendations store. What should we consider?"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cubit.utils import load_json, safe_write_json, data_root
DATA_DIR = data_root() / "advisor_data"


class Advisor:
    def __init__(self, data_dir: Path | str | None = None):
        self.data_dir = Path(data_dir) if data_dir else DATA_DIR
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.path = self.data_dir / "recommendations.json"
        if not self.path.exists():
            safe_write_json(self.path, {"recommendations": []})

    def _load(self) -> dict[str, Any]:
        return load_json(self.path, {"recommendations": []})

    def _save(self, data: dict[str, Any]) -> None:
        safe_write_json(self.path, data)

    def _next_id(self, items: list[dict[str, Any]]) -> str:
        max_n = 0
        for r in items:
            rid = r.get("id", "")
            if rid.startswith("rec-"):
                try:
                    n = int(rid.split("-", 1)[1])
                    if n > max_n:
                        max_n = n
                except ValueError:
                    pass
        return f"rec-{max_n + 1:03d}"

    def add(
        self,
        observation: str,
        evidence: str = "",
        recommendation: str = "",
    ) -> dict[str, Any]:
        data = self._load()
        items = data.get("recommendations", [])
        rec = {
            "id": self._next_id(items),
            "observation": observation,
            "evidence": evidence,
            "recommendation": recommendation,
            "status": "open",
            "created": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        }
        items.append(rec)
        data["recommendations"] = items
        self._save(data)
        return rec

    def list(self, status: str | None = "open") -> list[dict[str, Any]]:
        items = self._load().get("recommendations", [])
        if status:
            items = [r for r in items if r.get("status") == status]
        return items

    def close(self, rec_id: str) -> dict[str, Any] | None:
        data = self._load()
        for r in data.get("recommendations", []):
            if r.get("id") == rec_id:
                r["status"] = "closed"
                self._save(data)
                return r
        return None
