"""Utility helpers for Cubit OS."""
from __future__ import annotations

import json
import os
import tempfile
import time
from pathlib import Path
from typing import Any


def safe_write_json(path: str | Path, data: Any, retries: int = 3, delay: float = 0.05) -> None:
    """Atomic JSON write with retries for flaky filesystems."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(data, indent=2, ensure_ascii=False, default=str)

    for attempt in range(retries):
        try:
            fd, tmp_name = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as f:
                    f.write(content)
                    f.flush()
                    os.fsync(f.fileno())
                os.replace(tmp_name, path)
                return
            except Exception:
                try:
                    os.unlink(tmp_name)
                except OSError:
                    pass
                raise
        except Exception:
            if attempt == retries - 1:
                raise
            time.sleep(delay * (attempt + 1))


def load_json(path: str | Path, default: Any = None) -> Any:
    """Load JSON or return default."""
    path = Path(path)
    if not path.exists():
        return default if default is not None else {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return default if default is not None else {}


def ensure_dir(path: str | Path) -> Path:
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p

def data_root() -> Path:
    """Writable data root. On Android set CUBIT_DATA_ROOT to app files dir."""
    import os
    env = os.environ.get("CUBIT_DATA_ROOT")
    if env:
        root = Path(env)
        root.mkdir(parents=True, exist_ok=True)
        return root
    # Default: package-local data folders (desktop / CLI)
    return Path(__file__).resolve().parent

