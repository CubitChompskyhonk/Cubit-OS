"""Stripe wallet, checkout, and webhooks for Cubit OS.

Enable with:
  CUBIT_COMMERCE=1
  STRIPE_SECRET_KEY=sk_...
  STRIPE_PUBLISHABLE_KEY=pk_...
  STRIPE_WEBHOOK_SECRET=whsec_...

Free core remains available when disabled.
"""
from __future__ import annotations

import hashlib
import hmac
import os
import time
from typing import Any

from cubit.utils import data_root, load_json, safe_write_json


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


class CommerceGateway:
    def __init__(self):
        self.enabled = os.environ.get("CUBIT_COMMERCE", "").lower() in ("1", "true", "yes")
        self.secret_key = (
            os.environ.get("STRIPE_SECRET_KEY")
            or os.environ.get("CUBIT_STRIPE_SECRET_KEY")
            or ""
        )
        self.publishable_key = (
            os.environ.get("STRIPE_PUBLISHABLE_KEY")
            or os.environ.get("CUBIT_STRIPE_PUBLISHABLE_KEY")
            or ""
        )
        self.webhook_secret = (
            os.environ.get("STRIPE_WEBHOOK_SECRET")
            or os.environ.get("CUBIT_STRIPE_WEBHOOK_SECRET")
            or ""
        )
        self._root = data_root() / "commerce_data"
        self._root.mkdir(parents=True, exist_ok=True)
        self._ledger_path = self._root / "ledger.json"
        self._wallet_path = self._root / "wallet.json"
        self._ensure_stores()

    def _ensure_stores(self) -> None:
        if not self._ledger_path.exists():
            safe_write_json(
                self._ledger_path,
                {"currency": "usd", "sessions": [], "events": [], "customers": []},
            )
        if not self._wallet_path.exists():
            safe_write_json(
                self._wallet_path,
                {
                    "balance_cents": 0,
                    "currency": "usd",
                    "credits": [],
                    "debits": [],
                    "updated": _now(),
                },
            )

    def _ledger(self) -> dict[str, Any]:
        return load_json(self._ledger_path, {"sessions": [], "events": [], "customers": []})

    def _save_ledger(self, data: dict[str, Any]) -> None:
        safe_write_json(self._ledger_path, data)

    def _wallet(self) -> dict[str, Any]:
        return load_json(self._wallet_path, {"balance_cents": 0, "currency": "usd", "credits": [], "debits": []})

    def _save_wallet(self, data: dict[str, Any]) -> None:
        data["updated"] = _now()
        safe_write_json(self._wallet_path, data)

    def _stripe(self):
        if not self.secret_key:
            raise RuntimeError("STRIPE_SECRET_KEY not set")
        try:
            import stripe  # type: ignore
        except ImportError as e:
            raise RuntimeError("stripe package not installed: pip install stripe") from e
        stripe.api_key = self.secret_key
        return stripe

    def status(self) -> dict[str, Any]:
        sdk = False
        try:
            import stripe  # noqa: F401
            sdk = True
        except ImportError:
            pass
        return {
            "enabled": self.enabled,
            "provider": "stripe" if self.enabled else None,
            "configured": bool(self.secret_key) if self.enabled else False,
            "sdk_installed": sdk,
            "publishable_key": self.publishable_key if self.enabled else None,
            "publishable_key_present": bool(self.publishable_key),
            "webhook_configured": bool(self.webhook_secret),
            "webhook_path": "/api/v1/commerce/webhook/stripe",
            "free_core": True,
            "policy": (
                "Commerce is optional. Set CUBIT_COMMERCE=1 and Stripe keys to enable. "
                "Cubit free features never require payments."
            ),
        }

    def wallet_summary(self) -> dict[str, Any]:
        wallet = self._wallet()
        ledger = self._ledger()
        sessions = ledger.get("sessions") or []
        paid = [s for s in sessions if s.get("status") in ("paid", "complete", "completed")]
        open_s = [s for s in sessions if s.get("status") in ("open", "created")]
        return {
            "provider": "stripe",
            "enabled": self.enabled,
            "balance_cents": int(wallet.get("balance_cents") or 0),
            "currency": wallet.get("currency") or "usd",
            "updated": wallet.get("updated"),
            "session_count": len(sessions),
            "paid_count": len(paid),
            "open_count": len(open_s),
            "paid_total_cents": sum(int(s.get("amount_cents") or 0) for s in paid),
            "publishable_key": self.publishable_key or None,
            "recent_sessions": list(reversed(sessions[-15:])),
            "recent_credits": list(reversed((wallet.get("credits") or [])[-10:])),
            "recent_events": list(reversed((ledger.get("events") or [])[-15:])),
        }

    def create_checkout(
        self,
        amount_cents: int,
        currency: str = "usd",
        description: str = "Cubit OS",
        success_url: str = "http://127.0.0.1:8080/commerce?paid=1",
        cancel_url: str = "http://127.0.0.1:8080/commerce?cancelled=1",
        metadata: dict[str, Any] | None = None,
        customer_email: str | None = None,
    ) -> dict[str, Any]:
        if not self.enabled:
            raise RuntimeError("Commerce disabled — set CUBIT_COMMERCE=1")
        if amount_cents < 50:
            raise ValueError("amount_cents must be >= 50")

        metadata = dict(metadata or {})
        metadata.setdefault("source", "cubit_os")

        try:
            stripe = self._stripe()
            params: dict[str, Any] = {
                "mode": "payment",
                "line_items": [
                    {
                        "price_data": {
                            "currency": currency,
                            "product_data": {"name": description},
                            "unit_amount": amount_cents,
                        },
                        "quantity": 1,
                    }
                ],
                "success_url": success_url,
                "cancel_url": cancel_url,
                "metadata": metadata,
            }
            if customer_email:
                params["customer_email"] = customer_email
            session = stripe.checkout.Session.create(**params)
            session_record = {
                "id": session.id,
                "url": session.url,
                "amount_cents": amount_cents,
                "currency": currency,
                "description": description,
                "status": getattr(session, "status", None) or "open",
                "payment_status": getattr(session, "payment_status", None),
                "customer_email": customer_email,
                "created": _now(),
                "metadata": metadata,
                "dry_run": False,
            }
        except RuntimeError as e:
            if "stripe package" not in str(e).lower() and "STRIPE_SECRET" not in str(e):
                raise
            # Dry-run for local wiring without SDK/keys
            sid = f"cs_test_local_{int(time.time())}"
            session_record = {
                "id": sid,
                "url": f"https://checkout.stripe.com/c/pay/{sid}#cubit-dry-run",
                "amount_cents": amount_cents,
                "currency": currency,
                "description": description,
                "status": "open",
                "payment_status": "unpaid",
                "customer_email": customer_email,
                "created": _now(),
                "metadata": metadata,
                "dry_run": True,
                "note": str(e) if self.secret_key else "No STRIPE_SECRET_KEY — dry-run session",
            }

        data = self._ledger()
        data.setdefault("sessions", []).append(session_record)
        self._save_ledger(data)
        self._chronicle(f"Checkout created: {session_record['id']}", f"{amount_cents} {currency} — {description}")
        return session_record

    def credit_wallet(self, amount_cents: int, reason: str, ref: str | None = None) -> dict[str, Any]:
        wallet = self._wallet()
        wallet["balance_cents"] = int(wallet.get("balance_cents") or 0) + int(amount_cents)
        entry = {"amount_cents": amount_cents, "reason": reason, "ref": ref, "at": _now()}
        wallet.setdefault("credits", []).append(entry)
        self._save_wallet(wallet)
        return wallet

    def mark_session_paid(self, session_id: str, amount_cents: int | None = None) -> dict[str, Any] | None:
        data = self._ledger()
        found = None
        for s in data.get("sessions", []):
            if s.get("id") == session_id:
                s["status"] = "paid"
                s["payment_status"] = "paid"
                s["paid_at"] = _now()
                found = s
                if amount_cents is None:
                    amount_cents = int(s.get("amount_cents") or 0)
                break
        if found:
            self._save_ledger(data)
            self.credit_wallet(int(amount_cents or 0), reason="stripe_checkout", ref=session_id)
            self._chronicle(f"Payment recorded: {session_id}", f"{amount_cents} credited to wallet")
            self._journal_decision(
                f"Stripe payment completed for session {session_id}",
                reason="checkout.session.completed webhook or manual confirm",
                outcome="paid",
            )
        return found

    def construct_and_handle_webhook(self, payload: bytes, sig_header: str | None) -> dict[str, Any]:
        """Verify Stripe signature when secret set; process event."""
        if not self.enabled:
            raise RuntimeError("Commerce disabled")

        event: dict[str, Any]
        if self.webhook_secret and sig_header:
            stripe = self._stripe()
            try:
                event_obj = stripe.Webhook.construct_event(payload, sig_header, self.webhook_secret)
                event = event_obj if isinstance(event_obj, dict) else event_obj.to_dict()  # type: ignore
            except Exception as e:
                raise RuntimeError(f"Webhook signature verification failed: {e}") from e
        else:
            import json
            event = json.loads(payload.decode("utf-8") if isinstance(payload, (bytes, bytearray)) else payload)

        return self.handle_webhook_event(event)

    def handle_webhook_event(self, event: dict[str, Any]) -> dict[str, Any]:
        event_type = event.get("type") or "unknown"
        data_object = (event.get("data") or {}).get("object") or {}
        session_id = data_object.get("id")
        amount = data_object.get("amount_total") or data_object.get("amount")

        ledger = self._ledger()
        ledger.setdefault("events", []).append(
            {
                "id": event.get("id"),
                "type": event_type,
                "session_id": session_id,
                "received": _now(),
            }
        )
        self._save_ledger(ledger)

        if event_type in ("checkout.session.completed", "checkout.session.async_payment_succeeded"):
            if session_id:
                self.mark_session_paid(session_id, int(amount) if amount is not None else None)
        elif event_type == "payment_intent.succeeded" and session_id:
            # May not map 1:1 to checkout session id; record event only
            pass

        return {"received": True, "type": event_type, "session_id": session_id}

    def handle_webhook(self, payload: dict[str, Any], signature: str | None = None) -> dict[str, Any]:
        """JSON-body path (API router / tests)."""
        if not self.enabled:
            raise RuntimeError("Commerce disabled")
        return self.handle_webhook_event(payload)

    def _chronicle(self, event: str, significance: str = "") -> None:
        try:
            from cubit.chronicle.historian import Historian
            Historian().record(event=event, significance=significance)
        except Exception:
            pass

    def _journal_decision(self, decision: str, reason: str = "", outcome: str = "") -> None:
        try:
            from cubit.journal.store import Journal
            Journal().record_decision(decision=decision, reason=reason, outcome=outcome, tags=["commerce", "stripe"])
        except Exception:
            pass
