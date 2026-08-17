"""ProjectAgent: manage projects.json."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cubit.utils import load_json, safe_write_json

DATA_DIR = Path(__file__).resolve().parent / "data"


class ProjectAgent:
    def __init__(self, data_dir: Path | str | None = None):
        self.data_dir = Path(data_dir) if data_dir else DATA_DIR
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.path = self.data_dir / "projects.json"
        if not self.path.exists():
            safe_write_json(self.path, {"projects": []})

    def _load(self) -> dict[str, Any]:
        return load_json(self.path, {"projects": []})

    def _save(self, data: dict[str, Any]) -> None:
        safe_write_json(self.path, data)

    def create_project(self, name: str, next_action: str = "", status: str = "Concept") -> dict[str, Any]:
        data = self._load()
        projects = data.get("projects", [])
        if any(p.get("name") == name for p in projects):
            raise ValueError(f"Project already exists: {name}")
        project = {
            "name": name,
            "status": status if status in ("Concept", "Active", "Completed", "Archived") else "Concept",
            "next_action": next_action or "Define first milestone",
            "created": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        }
        projects.append(project)
        data["projects"] = projects
        self._save(data)
        return project

    def get_projects(self, include_archived: bool = False) -> list[dict[str, Any]]:
        projects = self._load().get("projects", [])
        if not include_archived:
            projects = [p for p in projects if p.get("status") != "Archived"]
        return projects

    def get_project(self, name: str) -> dict[str, Any] | None:
        for p in self._load().get("projects", []):
            if p.get("name") == name:
                return p
        return None

    def update_next_action(self, name: str, next_action: str) -> dict[str, Any] | None:
        data = self._load()
        for p in data.get("projects", []):
            if p.get("name") == name:
                p["next_action"] = next_action
                self._save(data)
                return p
        return None

    def update_status(self, name: str, status: str) -> dict[str, Any] | None:
        if status not in ("Concept", "Active", "Completed", "Archived"):
            raise ValueError(f"Invalid status: {status}")
        data = self._load()
        for p in data.get("projects", []):
            if p.get("name") == name:
                p["status"] = status
                self._save(data)
                return p
        return None

    def archive_project(self, name: str) -> dict[str, Any] | None:
        return self.update_status(name, "Archived")

    def project_count(self, include_archived: bool = False) -> int:
        return len(self.get_projects(include_archived=include_archived))
