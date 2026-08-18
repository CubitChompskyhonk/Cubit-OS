"""Stripe wallet / checkout framework for Cubit OS.

POLICY
------
- Free core of Cubit OS does NOT require Stripe, wallet, or payments.
- Commerce is OPT-IN via environment:
    CUBIT_COMMERCE=1
    STRIPE_SECRET_KEY=sk_...
    STRIPE_PUBLISHABLE_KEY=pk_...   (optional, returned to clients)
    STRIPE_WEBHOOK_SECRET=whsec_... (optional)
- Android free APK must not ship billing libraries; this module is desktop/server only.
- Significant monetary configuration should still respect Founder authority
  (enable via env; checkout creates Stripe sessions, does not mutate Cubit projects).

This is a thin framework: session create, wallet summary, webhook acknowledge.
It does not invent ledger truth — Stripe is the payment processor of record when enabled.
"""
from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any

from cubit.utils import data_root, load_json, safe_write_json


class CommerceGateway:
    def __init__(self):
        self.enabled = os.environ.get("CUBIT_COMMERCE", "").lower() in ("1", "true", "yes")
        self.secret_key = os.environ.get("STRIPE_SECRET_KEY") or os.environ.get("CUBIT_STRIPE_SECRET_KEY") or ""
        self.publishable_key = (
            os.environ.get("STRIPE_PUBLISHABLE_KEY")
            or os.environ.get("CUBIT_STRIPE_PUBLISHABLE_KEY")
            or ""
        )
        self.webhook_secret = os.environ.get("STRIPE_WEBHOOK_SECRET") or ""
        self._ledger_path = data_root() / "commerce_data" / "ledger.json"
        self._ledger_path.parent.mkdir(parents=True, exist_ok=True)
        if not self._ledger_path.exists():
            safe_write_json(
                self._ledger_path,
                {
                    "currency": "usd",
                    "sessions": [],
                    "events": [],
                    "note": "Local mirror of commerce events; Stripe remains source of truth when enabled.",
                },
            )

    def status(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "provider": "stripe" if self.enabled else None,
            "configured": bool(self.secret_key) if self.enabled else False,
            "publishable_key_present": bool(self.publishable_key),
            "webhook_configured": bool(self.webhook_secret),
            "free_core": True,
            "policy": (
                "Commerce is optional. Cubit OS free features never require payments. "
                "Set CUBIT_COMMERCE=1 and STRIPE_SECRET_KEY to enable."
            ),
        }

    def _ledger(self) -> dict[str, Any]:
        return load_json(self._ledger_path, {"sessions": [], "events": []})

    def _save_ledger(self, data: dict[str, Any]) -> None:
        safe_write_json(self._ledger_path, data)

    def wallet_summary(self) -> dict[str, Any]:
        data = self._ledger()
        sessions = data.get("sessions") or []
        paid = [s for s in sessions if s.get("status") == "paid"]
        total_cents = sum(int(s.get("amount_cents") or 0) for s in paid)
        return {
            "provider": "stripe",
            "currency": data.get("currency", "usd"),
            "session_count": len(sessions),
            "paid_count": len(paid),
            "paid_total_cents": total_cents,
            "publishable_key": self.publishable_key or None,
            "recent_sessions": sessions[-10:],
            "note": "Summary is a local mirror; verify balances in Stripe Dashboard.",
        }

    def create_checkout(
        self,
        amount_cents: int,
        currency: str = "usd",
        description: str = "Cubit OS",
        success_url: str = "http://127.0.0.1:8080/",
        cancel_url: str = "http://127.0.0.1:8080/",
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if not self.enabled:
            raise RuntimeError("Commerce disabled")
        if not self.secret_key:
            raise RuntimeError("STRIPE_SECRET_KEY not set")
        if amount_cents < 50:
            raise ValueError("amount_cents must be >= 50 (Stripe minimum varies by currency)")

        # Prefer official SDK when installed; fallback to documented shape for offline tests
        session_record: dict[str, Any]
        try:
            import stripe  # type: ignore

            stripe.api_key = self.secret_key
            session = stripe.checkout.Session.create(
                mode="payment",
                line_items=[
                    {
                        "price_data": {
                            "currency": currency,
                            "product_data": {"name": description},
                            "unit_amount": amount_cents,
                        },
                        "quantity": 1,
                    }
                ],
                success_url=success_url,
                cancel_url=cancel_url,
                metadata=metadata or {},
            )
            session_record = {
                "id": session.id,
                "url": session.url,
                "amount_cents": amount_cents,
                "currency": currency,
                "description": description,
                "status": session.status or "open",
                "created": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "metadata": metadata or {},
            }
        except ImportError:
            # Framework present without stripe package — dry-run session for local wiring tests
            sid = f"cs_test_local_{int(time.time())}"
            session_record = {
                "id": sid,
                "url": f"https://checkout.stripe.com/c/pay/{sid}#local-dry-run",
                "amount_cents": amount_cents,
                "currency": currency,
                "description": description,
                "status": "open",
                "created": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "metadata": metadata or {},
                "dry_run": True,
                "note": "Install stripe package and set live keys for real Checkout.",
            }

        data = self._ledger()
        data.setdefault("sessions", []).append(session_record)
        self._save_ledger(data)

        try:
            from cubit.chronicle.historian import Historian

            Historian().record(
                event=f"Commerce checkout created: {session_record['id']}",
                significance=f"{amount_cents} {currency} — {description}",
            )
        except Exception:
            pass

        return session_record

    def handle_webhook(self, payload: dict[str, Any], signature: str | None = None) -> dict[str, Any]:
        if not self.enabled:
            raise RuntimeError("Commerce disabled")
        # Minimal verification hook — production should use stripe.Webhook.construct_event
        event_type = payload.get("type") or payload.get("event") or "unknown"
        obj = payload.get("data", {}).get("object", payload)
        session_id = obj.get("id")

        data = self._ledger()
        data.setdefault("events", []).append(
            {
                "type": event_type,
                "session_id": session_id,
                "received": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            }
        )
        if event_type in ("checkout.session.completed", "payment_intent.succeeded") and session_id:
            for s in data.get("sessions", []):
                if s.get("id") == session_id:
                    s["status"] = "paid"
        self._save_ledger(data)
        return {"received": True, "type": event_type, "session_id": session_id}
