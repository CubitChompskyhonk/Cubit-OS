"""API framework: envelopes, errors, auth, versioning."""
from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Callable

from cubit.utils import data_root, load_json, safe_write_json

API_VERSION = "v1"


@dataclass
class ApiError:
    code: str
    message: str
    details: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"code": self.code, "message": self.message}
        if self.details:
            d["details"] = self.details
        return d


@dataclass
class ApiResponse:
    ok: bool
    data: Any = None
    error: ApiError | None = None
    meta: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "ok": self.ok,
            "api_version": API_VERSION,
            "meta": {**self.meta, "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())},
        }
        if self.ok:
            out["data"] = self.data
        else:
            out["error"] = self.error.to_dict() if self.error else {"code": "unknown", "message": "Unknown error"}
        return out

    @classmethod
    def success(cls, data: Any = None, **meta: Any) -> "ApiResponse":
        return cls(ok=True, data=data, meta=meta)

    @classmethod
    def fail(cls, code: str, message: str, details: dict | None = None, **meta: Any) -> "ApiResponse":
        return cls(ok=False, error=ApiError(code, message, details), meta=meta)


class ApiKeyStore:
    """Local API keys for Founder / integrations. No cloud identity required."""

    def __init__(self, path: Path | None = None):
        self.path = path or (data_root() / "api_data" / "api_keys.json")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            safe_write_json(self.path, {"keys": []})

    def _load(self) -> dict[str, Any]:
        return load_json(self.path, {"keys": []})

    def _save(self, data: dict[str, Any]) -> None:
        safe_write_json(self.path, data)

    @staticmethod
    def _hash(raw: str) -> str:
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def create_key(self, name: str = "default", scopes: list[str] | None = None) -> dict[str, Any]:
        raw = "cubit_" + secrets.token_urlsafe(24)
        entry = {
            "id": "key-" + secrets.token_hex(4),
            "name": name,
            "prefix": raw[:12],
            "hash": self._hash(raw),
            "scopes": scopes or ["read", "write", "admin"],
            "created": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "revoked": False,
        }
        data = self._load()
        data.setdefault("keys", []).append(entry)
        self._save(data)
        # Return raw once
        return {**{k: v for k, v in entry.items() if k != "hash"}, "key": raw}

    def list_keys(self) -> list[dict[str, Any]]:
        return [
            {k: v for k, v in e.items() if k != "hash"}
            for e in self._load().get("keys", [])
        ]

    def revoke(self, key_id: str) -> bool:
        data = self._load()
        for e in data.get("keys", []):
            if e.get("id") == key_id:
                e["revoked"] = True
                self._save(data)
                return True
        return False

    def verify(self, raw: str | None) -> dict[str, Any] | None:
        if not raw:
            return None
        # Dev mode: CUBIT_API_OPEN=1 skips auth (local only)
        if os.environ.get("CUBIT_API_OPEN", "").lower() in ("1", "true", "yes"):
            return {"id": "open", "name": "open", "scopes": ["read", "write", "admin"]}
        # Optional single env key
        env_key = os.environ.get("CUBIT_API_KEY")
        if env_key and hmac.compare_digest(env_key, raw):
            return {"id": "env", "name": "env", "scopes": ["read", "write", "admin"]}
        h = self._hash(raw)
        for e in self._load().get("keys", []):
            if e.get("revoked"):
                continue
            if e.get("hash") and hmac.compare_digest(e["hash"], h):
                return {k: v for k, v in e.items() if k != "hash"}
        return None


class ApiFramework:
    """Central API surface for Cubit OS."""

    def __init__(self):
        self.keys = ApiKeyStore()
        self.version = API_VERSION

    def require_auth(self, authorization: str | None, scope: str = "read") -> tuple[dict | None, ApiResponse | None]:
        token = None
        if authorization:
            parts = authorization.split(" ", 1)
            token = parts[1].strip() if len(parts) == 2 and parts[0].lower() == "bearer" else authorization.strip()
        principal = self.keys.verify(token)
        if not principal:
            return None, ApiResponse.fail("unauthorized", "Valid API key required (Authorization: Bearer <key>)")
        scopes = principal.get("scopes") or []
        if scope not in scopes and "admin" not in scopes:
            return None, ApiResponse.fail("forbidden", f"Missing scope: {scope}")
        return principal, None
