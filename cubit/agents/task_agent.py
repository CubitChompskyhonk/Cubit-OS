"""TaskAgent: manage tasks.json."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cubit.utils import load_json, safe_write_json

DATA_DIR = Path(__file__).resolve().parent / "data"


class TaskAgent:
    def __init__(self, data_dir: Path | str | None = None):
        self.data_dir = Path(data_dir) if data_dir else DATA_DIR
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.path = self.data_dir / "tasks.json"
        if not self.path.exists():
            safe_write_json(self.path, {"tasks": []})

    def _load(self) -> dict[str, Any]:
        return load_json(self.path, {"tasks": []})

    def _save(self, data: dict[str, Any]) -> None:
        safe_write_json(self.path, data)

    def _next_id(self, tasks: list[dict[str, Any]]) -> str:
        max_n = 0
        for t in tasks:
            tid = t.get("id", "")
            if tid.startswith("task-"):
                try:
                    n = int(tid.split("-", 1)[1])
                    if n > max_n:
                        max_n = n
                except ValueError:
                    pass
        return f"task-{max_n + 1:03d}"

    def add_task(
        self,
        title: str,
        description: str = "",
        project: str | None = None,
        status: str = "open",
    ) -> dict[str, Any]:
        data = self._load()
        tasks = data.get("tasks", [])
        task = {
            "id": self._next_id(tasks),
            "title": title,
            "description": description,
            "project": project,
            "status": status if status in ("open", "in_progress", "done", "cancelled") else "open",
            "created": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "completed": None,
        }
        tasks.append(task)
        data["tasks"] = tasks
        self._save(data)
        return task

    def complete_task(self, task_id: str) -> dict[str, Any] | None:
        data = self._load()
        for t in data.get("tasks", []):
            if t.get("id") == task_id:
                t["status"] = "done"
                t["completed"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
                self._save(data)
                return t
        return None

    def update_status(self, task_id: str, status: str) -> dict[str, Any] | None:
        if status not in ("open", "in_progress", "done", "cancelled"):
            raise ValueError(f"Invalid status: {status}")
        data = self._load()
        for t in data.get("tasks", []):
            if t.get("id") == task_id:
                t["status"] = status
                if status == "done" and not t.get("completed"):
                    t["completed"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
                elif status != "done":
                    t["completed"] = None
                self._save(data)
                return t
        return None

    def get_tasks(self, status: str | None = None, project: str | None = None) -> list[dict[str, Any]]:
        tasks = self._load().get("tasks", [])
        if status:
            tasks = [t for t in tasks if t.get("status") == status]
        if project is not None:
            tasks = [t for t in tasks if t.get("project") == project]
        return tasks

    def get_task(self, task_id: str) -> dict[str, Any] | None:
        for t in self._load().get("tasks", []):
            if t.get("id") == task_id:
                return t
        return None

    def execution_stats(self) -> dict[str, Any]:
        tasks = self._load().get("tasks", [])
        total = len(tasks)
        done = sum(1 for t in tasks if t.get("status") == "done")
        open_ = sum(1 for t in tasks if t.get("status") == "open")
        in_progress = sum(1 for t in tasks if t.get("status") == "in_progress")
        cancelled = sum(1 for t in tasks if t.get("status") == "cancelled")
        rate = (done / total * 100) if total else 0.0
        return {
            "total": total,
            "done": done,
            "open": open_,
            "in_progress": in_progress,
            "cancelled": cancelled,
            "execution_rate": round(rate, 1),
        }

    def grouped_by_project(self) -> dict[str, list[dict[str, Any]]]:
        tasks = self._load().get("tasks", [])
        groups: dict[str, list[dict[str, Any]]] = {}
        for t in tasks:
            key = t.get("project") or "(ungrouped)"
            groups.setdefault(key, []).append(t)
        return groups
