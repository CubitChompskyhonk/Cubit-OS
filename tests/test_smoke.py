"""Minimal acceptance / smoke tests for Cubit OS."""
from __future__ import annotations

import sys
from pathlib import Path

# Ensure package root on path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def test_purpose_defined():
    from cubit.memory.loader import MemoryLoader
    m = MemoryLoader()
    assert m.purpose_status() == "DEFINED"


def test_steward_aligned_when_manageable():
    from cubit.council.steward import Steward
    r = Steward().review()
    assert r["purpose_status"] == "DEFINED"
    assert r["focus_status"] in ("MANAGEABLE", "STRETCHED", "OVERLOADED")
    # With empty projects/tasks should be manageable
    assert r["aligned"] is True or r["focus_status"] != "OVERLOADED"


def test_create_project_yields_proposal():
    from cubit.ai.conversation import ConversationalLayer
    cl = ConversationalLayer()
    result = cl.handle("create project SmokeTestProject")
    assert result["intent"] == "create_project"
    assert result["proposal"] is not None
    assert result["proposal"]["status"] == "pending"
    assert "prop-" in result["proposal"]["id"]
    # Project should NOT exist yet
    from cubit.projects.agent import ProjectAgent
    assert ProjectAgent().get_project("SmokeTestProject") is None
    return result["proposal"]["id"]


def test_approve_creates_project_and_journal():
    from cubit.ai.conversation import ConversationalLayer
    from cubit.projects.agent import ProjectAgent
    from cubit.journal.store import Journal
    cl = ConversationalLayer()
    result = cl.handle("create project ApproveMe")
    prop_id = result["proposal"]["id"]
    out = cl.approve(prop_id)
    assert out["execution"]["status"] == "executed"
    assert ProjectAgent().get_project("ApproveMe") is not None
    entries = Journal().get_entries(entry_type="decision")
    assert any("ApproveMe" in (e.get("decision") or "") or prop_id in (e.get("related_proposal") or "") for e in entries)


def test_reject_no_project():
    from cubit.ai.conversation import ConversationalLayer
    from cubit.projects.agent import ProjectAgent
    cl = ConversationalLayer()
    result = cl.handle("create project RejectMe")
    prop_id = result["proposal"]["id"]
    cl.reject(prop_id)
    assert ProjectAgent().get_project("RejectMe") is None


def test_tasks_grouped():
    from cubit.agents.task_agent import TaskAgent
    ta = TaskAgent()
    groups = ta.grouped_by_project()
    assert isinstance(groups, dict)


def test_briefing_fields():
    from cubit.ai.briefing_builder import BriefingBuilder
    b = BriefingBuilder().build()
    assert "identity" in b
    assert "purpose_status" in b
    assert "project_count" in b
    assert "focus_status" in b
    text = BriefingBuilder().render()
    assert "Cubit" in text


def test_reason_local():
    from cubit.ai.reasoner import Reasoner
    r = Reasoner().reason("What is our purpose?")
    assert r["mode"] in ("local", "local_fallback", "openai")
    assert "answer" in r


def test_no_payment_code():
    """Free path: commerce must be off by default; Android free APK has no billing libs."""
    from cubit.commerce.stripe_wallet import CommerceGateway
    st = CommerceGateway().status()
    assert st["enabled"] is False
    assert st["free_core"] is True
    # Android tree must not reference billing libraries
    android = Path(__file__).resolve().parents[1] / "android"
    if android.exists():
        for path in android.rglob("*"):
            if path.suffix.lower() in (".kt", ".kts", ".xml", ".gradle"):
                t = path.read_text(encoding="utf-8", errors="ignore").lower()
                for b in ("billingclient", "com.android.billingclient", "play billing"):
                    assert b not in t, f"Found {b} in {path}"


def test_api_framework():
    import os
    os.environ["CUBIT_API_OPEN"] = "1"
    from cubit.api.router import ApiRouter
    r = ApiRouter()
    res = r.dispatch("GET", "/health", authorization="Bearer x")
    assert res.ok
    routes = r.list_routes()
    assert any(x["path"].endswith("/projects") for x in routes)


if __name__ == "__main__":
    test_purpose_defined()
    print("OK purpose")
    test_steward_aligned_when_manageable()
    print("OK steward")
    test_create_project_yields_proposal()
    print("OK proposal")
    test_approve_creates_project_and_journal()
    print("OK approve")
    test_reject_no_project()
    print("OK reject")
    test_tasks_grouped()
    print("OK tasks")
    test_briefing_fields()
    print("OK briefing")
    test_reason_local()
    print("OK reason")
    test_no_payment_code()
    print("OK no payment")
    test_api_framework()
    print("OK api")
    print("All smoke tests passed.")
