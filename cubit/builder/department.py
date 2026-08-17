"""Builder: How do we create? Create departments."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from cubit.chronicle.historian import Historian
from cubit.journal.store import Journal
from cubit.registry.store import Registry


class Builder:
    def __init__(
        self,
        registry: Registry | None = None,
        historian: Historian | None = None,
        journal: Journal | None = None,
        base_path: Path | str | None = None,
    ):
        self.registry = registry or Registry()
        self.historian = historian or Historian()
        self.journal = journal or Journal()
        self.base_path = Path(base_path) if base_path else Path(__file__).resolve().parent.parent

    def create_department(
        self,
        name: str,
        description: str = "",
        status: str = "active",
        scaffold: bool = True,
    ) -> dict[str, Any]:
        entry = self.registry.register(name, description=description, status=status)
        if scaffold:
            dept_dir = self.base_path / name.lower().replace(" ", "_")
            dept_dir.mkdir(parents=True, exist_ok=True)
            init = dept_dir / "__init__.py"
            if not init.exists():
                init.write_text(f'"""Department: {name}\n{description}\n"""\n', encoding="utf-8")
        self.historian.record(
            event=f"Department created: {name}",
            significance=description or "New organizational capability",
        )
        self.journal.record_decision(
            decision=f"Created department: {name}",
            reason=description,
            outcome="success",
            tags=["builder", "department"],
        )
        return entry
