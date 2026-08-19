"""Registry: track departments and status."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cubit.utils import load_json, safe_write_json, data_root

DATA_DIR = data_root() / "registry_data"

_BUILTINS = [
    ("Steward", "Are we aligned?"),
    ("Advisor", "What should we consider?"),
    ("Historian", "Why did we become this?"),
    ("Builder", "How do we create?"),
    ("Cubitz", "Living garden simulation — start the world"),
    ("Cubits", "MS-DOS puzzle — save the cubits (Lemmings-inspired)"),
    ("Advocate", "Personal agent — offline calls, mail, appointments, sales, PR"),
]


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
                        {"name": n, "description": d, "status": "active"}
                        for n, d in _BUILTINS
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

    def ensure_builtins(self) -> None:
        """Ensure core departments exist (uses _load only — no list/get recursion)."""
        data = self._load()
        depts = data.get("departments", [])
        names = {d.get("name") for d in depts}
        changed = False
        for name, desc in _BUILTINS:
            if name not in names:
                depts.append(
                    {
                        "name": name,
                        "description": desc,
                        "status": "active",
                        "created": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                    }
                )
                changed = True
        if changed:
            data["departments"] = depts
            self._save(data)

    def list(self) -> list[dict[str, Any]]:
        self.ensure_builtins()
        return self._load().get("departments", [])

    def get(self, name: str) -> dict[str, Any] | None:
        # Do not call list() here — avoid recursion with ensure_builtins
        for d in self._load().get("departments", []):
            if d.get("name") == name:
                return d
        return None
