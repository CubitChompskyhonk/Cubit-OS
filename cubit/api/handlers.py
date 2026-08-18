"""API v1 handlers — map HTTP surface to Cubit agents (propose, don't silent-mutate)."""
from __future__ import annotations

from typing import Any

from cubit.api.framework import ApiResponse


def health(principal=None, body=None, query=None) -> ApiResponse:
    return ApiResponse.success({"status": "ok", "service": "Cubit OS", "version": "0.1.0"})


def routes(principal=None, body=None, query=None) -> ApiResponse:
    from cubit.api.router import ApiRouter
    return ApiResponse.success({"routes": ApiRouter().list_routes()})


def briefing(principal=None, body=None, query=None) -> ApiResponse:
    from cubit.ai.briefing_builder import BriefingBuilder
    return ApiResponse.success(BriefingBuilder().build())


def steward_review(principal=None, body=None, query=None) -> ApiResponse:
    from cubit.council.steward import Steward
    return ApiResponse.success(Steward().review())


def context(principal=None, body=None, query=None) -> ApiResponse:
    from cubit.ai.context_builder import ContextBuilder
    return ApiResponse.success(ContextBuilder().build())


def list_projects(principal=None, body=None, query=None) -> ApiResponse:
    from cubit.projects.agent import ProjectAgent
    include = str((query or {}).get("all", "")).lower() in ("1", "true", "yes")
    return ApiResponse.success({"projects": ProjectAgent().get_projects(include_archived=include)})


def propose_create_project(principal=None, body=None, query=None) -> ApiResponse:
    from cubit.ai.conversation import ConversationalLayer
    body = body or {}
    name = (body.get("name") or "").strip()
    if not name:
        return ApiResponse.fail("validation", "name is required")
    cl = ConversationalLayer()
    prop = cl.create_proposal(
        action="create_project",
        description=f"Create project '{name}'",
        params={
            "name": name,
            "next_action": body.get("next_action") or "Define first milestone",
            "status": body.get("status") or "Concept",
        },
        risk_notes="API-originated proposal. Founder approval required.",
    )
    return ApiResponse.success({"proposal": prop}, requires_approval=True)


def list_tasks(principal=None, body=None, query=None) -> ApiResponse:
    from cubit.agents.task_agent import TaskAgent
    ta = TaskAgent()
    q = query or {}
    if q.get("grouped"):
        return ApiResponse.success({"groups": ta.grouped_by_project()})
    return ApiResponse.success({
        "tasks": ta.get_tasks(status=q.get("status"), project=q.get("project")),
        "stats": ta.execution_stats(),
    })


def propose_add_task(principal=None, body=None, query=None) -> ApiResponse:
    from cubit.ai.conversation import ConversationalLayer
    body = body or {}
    title = (body.get("title") or "").strip()
    if not title:
        return ApiResponse.fail("validation", "title is required")
    cl = ConversationalLayer()
    prop = cl.create_proposal(
        action="add_task",
        description=f"Add task '{title}'",
        params={
            "title": title,
            "description": body.get("description") or "",
            "project": body.get("project"),
        },
        risk_notes="API-originated proposal. Founder approval required.",
    )
    return ApiResponse.success({"proposal": prop}, requires_approval=True)


def list_proposals(principal=None, body=None, query=None) -> ApiResponse:
    from cubit.ai.conversation import ConversationalLayer
    return ApiResponse.success({"pending": ConversationalLayer().get_pending()})


def approve_proposal(principal=None, body=None, query=None) -> ApiResponse:
    from cubit.ai.conversation import ConversationalLayer
    prop_id = (body or {}).get("id") or (query or {}).get("id")
    if not prop_id:
        return ApiResponse.fail("validation", "id required")
    return ApiResponse.success(ConversationalLayer().approve(prop_id))


def reject_proposal(principal=None, body=None, query=None) -> ApiResponse:
    from cubit.ai.conversation import ConversationalLayer
    prop_id = (body or {}).get("id") or (query or {}).get("id")
    if not prop_id:
        return ApiResponse.fail("validation", "id required")
    return ApiResponse.success(ConversationalLayer().reject(prop_id))


def list_recommendations(principal=None, body=None, query=None) -> ApiResponse:
    from cubit.advisor.store import Advisor
    status = (query or {}).get("status", "open")
    return ApiResponse.success({"recommendations": Advisor().list(status=status)})


def add_recommendation(principal=None, body=None, query=None) -> ApiResponse:
    from cubit.advisor.store import Advisor
    body = body or {}
    rec = Advisor().add(
        observation=body.get("observation") or "",
        evidence=body.get("evidence") or "",
        recommendation=body.get("recommendation") or "",
    )
    return ApiResponse.success({"recommendation": rec})


def chronicle(principal=None, body=None, query=None) -> ApiResponse:
    from cubit.chronicle.historian import Historian
    limit = int((query or {}).get("limit") or 50)
    return ApiResponse.success({"events": Historian().recent_history(limit)})


def journal(principal=None, body=None, query=None) -> ApiResponse:
    from cubit.journal.store import Journal
    return ApiResponse.success({"entries": Journal().recent(int((query or {}).get("limit") or 30))})


def registry(principal=None, body=None, query=None) -> ApiResponse:
    from cubit.registry.store import Registry
    return ApiResponse.success({"departments": Registry().list()})


def propose_department(principal=None, body=None, query=None) -> ApiResponse:
    from cubit.ai.conversation import ConversationalLayer
    body = body or {}
    name = (body.get("name") or "").strip()
    if not name:
        return ApiResponse.fail("validation", "name is required")
    cl = ConversationalLayer()
    prop = cl.create_proposal(
        action="create_department",
        description=f"Create department '{name}'",
        params={
            "name": name,
            "description": body.get("description") or "",
            "status": "active",
            "scaffold": True,
        },
        risk_notes="API-originated department create. Requires approval.",
    )
    return ApiResponse.success({"proposal": prop}, requires_approval=True)


def chat(principal=None, body=None, query=None) -> ApiResponse:
    from cubit.ai.conversation import ConversationalLayer
    text = (body or {}).get("message") or (body or {}).get("text") or ""
    return ApiResponse.success(ConversationalLayer().handle(text))


def list_keys(principal=None, body=None, query=None) -> ApiResponse:
    from cubit.api.framework import ApiFramework
    return ApiResponse.success({"keys": ApiFramework().keys.list_keys()})


def create_key(principal=None, body=None, query=None) -> ApiResponse:
    from cubit.api.framework import ApiFramework
    body = body or {}
    created = ApiFramework().keys.create_key(
        name=body.get("name") or "default",
        scopes=body.get("scopes"),
    )
    return ApiResponse.success(created, warning="Store the key now; it is shown only once.")


def revoke_key(principal=None, body=None, query=None) -> ApiResponse:
    from cubit.api.framework import ApiFramework
    key_id = (body or {}).get("id") or (query or {}).get("id")
    if not key_id:
        return ApiResponse.fail("validation", "id required")
    ok = ApiFramework().keys.revoke(key_id)
    if not ok:
        return ApiResponse.fail("not_found", "key not found")
    return ApiResponse.success({"revoked": key_id})


# ── Commerce (optional) ─────────────────────────────────────────────

def commerce_status(principal=None, body=None, query=None) -> ApiResponse:
    from cubit.commerce.stripe_wallet import CommerceGateway
    return ApiResponse.success(CommerceGateway().status())


def commerce_wallet(principal=None, body=None, query=None) -> ApiResponse:
    from cubit.commerce.stripe_wallet import CommerceGateway
    gw = CommerceGateway()
    if not gw.enabled:
        return ApiResponse.fail(
            "commerce_disabled",
            "Commerce is off. Set CUBIT_COMMERCE=1 and Stripe keys to enable.",
        )
    return ApiResponse.success(gw.wallet_summary())


def commerce_checkout(principal=None, body=None, query=None) -> ApiResponse:
    from cubit.commerce.stripe_wallet import CommerceGateway
    gw = CommerceGateway()
    if not gw.enabled:
        return ApiResponse.fail("commerce_disabled", "Commerce disabled (CUBIT_COMMERCE not set).")
    body = body or {}
    try:
        session = gw.create_checkout(
            amount_cents=int(body.get("amount_cents") or 0),
            currency=(body.get("currency") or "usd").lower(),
            description=body.get("description") or "Cubit OS",
            success_url=body.get("success_url") or "http://127.0.0.1:8080/commerce?paid=1",
            cancel_url=body.get("cancel_url") or "http://127.0.0.1:8080/commerce?cancelled=1",
            metadata=body.get("metadata") or {},
            customer_email=body.get("customer_email"),
        )
        return ApiResponse.success(session)
    except Exception as e:
        return ApiResponse.fail("commerce_error", str(e))


def commerce_stripe_webhook(principal=None, body=None, query=None) -> ApiResponse:
    from cubit.commerce.stripe_wallet import CommerceGateway
    gw = CommerceGateway()
    if not gw.enabled:
        return ApiResponse.fail("commerce_disabled", "Commerce disabled.")
    try:
        # Prefer pre-verified event from FastAPI raw path (body already event dict)
        if body and body.get("_raw_verified"):
            result = gw.handle_webhook_event(body.get("event") or body)
        else:
            result = gw.handle_webhook(payload=body or {}, signature=(query or {}).get("stripe_signature"))
        return ApiResponse.success(result)
    except Exception as e:
        return ApiResponse.fail("webhook_error", str(e))
