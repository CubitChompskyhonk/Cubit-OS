"""Declarative route table + dispatch for API v1."""
from __future__ import annotations

import re
from typing import Any, Callable

from cubit.api.framework import ApiFramework, ApiResponse

Handler = Callable[..., ApiResponse]


class ApiRouter:
    def __init__(self, framework: ApiFramework | None = None):
        self.fw = framework or ApiFramework()
        self._routes: list[tuple[str, re.Pattern[str], str, str, Handler]] = []
        self._register_core()

    def add(self, method: str, path: str, scope: str, handler: Handler) -> None:
        # Convert /foo/{id}/bar -> regex
        pattern = re.sub(r"\{(\w+)\}", r"(?P<\1>[^/]+)", path)
        pattern = "^" + pattern + "$"
        self._routes.append((method.upper(), re.compile(pattern), path, scope, handler))

    def dispatch(
        self,
        method: str,
        path: str,
        body: dict[str, Any] | None = None,
        query: dict[str, Any] | None = None,
        authorization: str | None = None,
    ) -> ApiResponse:
        path = path or "/"
        if path.startswith("/api/v1"):
            path = path[len("/api/v1") :] or "/"
        if not path.startswith("/"):
            path = "/" + path

        method = method.upper()
        for m, cre, template, scope, handler in self._routes:
            if m != method:
                continue
            match = cre.match(path)
            if not match:
                continue
            params = match.groupdict()
            principal, err = self.fw.require_auth(authorization, scope=scope)
            # Stripe webhook may use signature instead of API key when commerce enabled
            if err and path == "/commerce/webhook/stripe":
                principal = {"id": "stripe", "scopes": ["write"]}
                err = None
            if err:
                return err
            merged_body = {**(body or {}), **params}
            merged_query = {**(query or {}), **params}
            try:
                return handler(principal=principal, body=merged_body, query=merged_query)
            except Exception as e:
                return ApiResponse.fail("internal", str(e))

        return ApiResponse.fail("not_found", f"No route {method} {path}")

    def list_routes(self) -> list[dict[str, str]]:
        return [
            {"method": m, "path": f"/api/v1{template}", "scope": scope}
            for m, _, template, scope, _ in self._routes
        ]

    def _register_core(self) -> None:
        from cubit.api import handlers as h

        self.add("GET", "/health", "read", h.health)
        self.add("GET", "/routes", "read", h.routes)
        self.add("GET", "/briefing", "read", h.briefing)
        self.add("GET", "/steward", "read", h.steward_review)
        self.add("GET", "/context", "read", h.context)

        self.add("GET", "/projects", "read", h.list_projects)
        self.add("POST", "/projects", "write", h.propose_create_project)
        self.add("GET", "/tasks", "read", h.list_tasks)
        self.add("POST", "/tasks", "write", h.propose_add_task)

        self.add("GET", "/proposals", "read", h.list_proposals)
        self.add("POST", "/proposals/{id}/approve", "admin", h.approve_proposal)
        self.add("POST", "/proposals/{id}/reject", "admin", h.reject_proposal)

        self.add("GET", "/advisor/recommendations", "read", h.list_recommendations)
        self.add("POST", "/advisor/recommendations", "write", h.add_recommendation)
        self.add("GET", "/chronicle", "read", h.chronicle)
        self.add("GET", "/journal", "read", h.journal)
        self.add("GET", "/registry", "read", h.registry)
        self.add("POST", "/builder/departments", "write", h.propose_department)

        self.add("POST", "/chat", "write", h.chat)

        self.add("GET", "/keys", "admin", h.list_keys)
        self.add("POST", "/keys", "admin", h.create_key)
        self.add("POST", "/keys/{id}/revoke", "admin", h.revoke_key)

        self.add("GET", "/commerce/status", "read", h.commerce_status)
        self.add("GET", "/commerce/wallet", "read", h.commerce_wallet)
        self.add("POST", "/commerce/checkout", "write", h.commerce_checkout)
        self.add("POST", "/commerce/webhook/stripe", "write", h.commerce_stripe_webhook)
