"""MemoryLoader: identity, purpose, memories."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cubit.utils import load_json, safe_write_json

DATA_DIR = Path(__file__).resolve().parent / "data"


class MemoryLoader:
    def __init__(self, data_dir: Path | str | None = None):
        self.data_dir = Path(data_dir) if data_dir else DATA_DIR
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._ensure_defaults()

    def _ensure_defaults(self) -> None:
        identity_path = self.data_dir / "identity.json"
        if not identity_path.exists():
            safe_write_json(
                identity_path,
                {
                    "name": "Cubit",
                    "role": "AI Operations Manager",
                    "relationship_to_founder": "Strategic partner and implementation assistant",
                    "mission": "Transform the Founder's ideas into organized, actionable projects while preserving intent and purpose.",
                    "current_focus": ["Build and improve Cubit OS"],
                    "version": "0.1.0",
                },
            )
        purpose_path = self.data_dir / "purpose.json"
        if not purpose_path.exists():
            safe_write_json(
                purpose_path,
                {
                    "purpose_statement": "Transform the Founder's ideas into organized, actionable projects while preserving intent and purpose.",
                    "founding_principles": [
                        "Preserve Founder intent",
                        "Explain reasoning behind recommendations",
                        "Identify risks and unintended consequences",
                        "Prefer simple, reliable solutions over unnecessary complexity",
                        "Maintain continuity of decisions and lessons learned",
                        "Ask for clarification when important information is missing",
                        "Prioritize ethical outcomes over short-term gains",
                    ],
                    "founder_authority": "Founder retains final authority over all significant decisions.",
                    "operating_axioms": [
                        "Intent before execution",
                        "Clarity before complexity",
                        "Deliberate placement before rapid expansion",
                        "Foundation before expansion",
                    ],
                    "status": "DEFINED",
                    "last_updated": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                },
            )
        memories_path = self.data_dir / "memories.json"
        if not memories_path.exists():
            safe_write_json(memories_path, {"entries": []})

    def load_identity(self) -> dict[str, Any]:
        return load_json(self.data_dir / "identity.json", {})

    def load_purpose(self) -> dict[str, Any]:
        return load_json(self.data_dir / "purpose.json", {"status": "UNDEFINED"})

    def load_memories(self) -> dict[str, Any]:
        return load_json(self.data_dir / "memories.json", {"entries": []})

    def load_all(self) -> dict[str, Any]:
        return {
            "identity": self.load_identity(),
            "purpose": self.load_purpose(),
            "memories": self.load_memories(),
        }

    def purpose_status(self) -> str:
        p = self.load_purpose()
        return p.get("status", "UNDEFINED")

    def update_purpose(self, updates: dict[str, Any]) -> dict[str, Any]:
        purpose = self.load_purpose()
        purpose.update(updates)
        purpose["last_updated"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        safe_write_json(self.data_dir / "purpose.json", purpose)
        return purpose

    def add_memory(self, entry: dict[str, Any]) -> None:
        memories = self.load_memories()
        entries = memories.get("entries", [])
        entry.setdefault("created", datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"))
        entries.append(entry)
        memories["entries"] = entries
        safe_write_json(self.data_dir / "memories.json", memories)
