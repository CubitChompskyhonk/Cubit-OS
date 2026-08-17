"""Reasoner: optional OpenAI over local context only. Never mutates state."""
from __future__ import annotations

import os
from typing import Any

from cubit.ai.briefing_builder import BriefingBuilder
from cubit.ai.context_builder import ContextBuilder


SYSTEM_PROMPT = """You are Cubit, AI Operations Manager and strategic partner for the Founder.
You reason ONLY over the provided Cubit organizational context. Do not invent projects, tasks, facts, or history.
Preserve Founder intent. Propose; do not execute. Explain reasoning, risks, and tradeoffs.
Prefer simple reliable solutions. Foundation before expansion.
If information is missing, ask for clarification.
Tone: clear, structured, practical."""


class Reasoner:
    def __init__(self):
        self.briefing = BriefingBuilder()
        self.context = ContextBuilder()

    def _has_api_key(self) -> bool:
        return bool(os.environ.get("OPENAI_API_KEY") or os.environ.get("CUBIT_OPENAI_API_KEY"))

    def reason(self, question: str) -> dict[str, Any]:
        briefing_text = self.briefing.render()
        if not self._has_api_key():
            return {
                "mode": "local",
                "answer": (
                    "No OpenAI API key set (OPENAI_API_KEY or CUBIT_OPENAI_API_KEY). "
                    "Local fallback — current briefing:\n\n" + briefing_text
                ),
                "context_used": "briefing",
            }

        try:
            from openai import OpenAI

            key = os.environ.get("OPENAI_API_KEY") or os.environ.get("CUBIT_OPENAI_API_KEY")
            client = OpenAI(api_key=key)
            ctx = self.context.build()
            # Compact context for the model
            compact = {
                "identity": ctx.get("identity"),
                "purpose": ctx.get("purpose"),
                "projects": ctx.get("projects"),
                "task_stats": ctx.get("task_stats"),
                "steward": ctx.get("steward"),
                "recommendations": ctx.get("recommendations"),
                "recent_journal": ctx.get("journal_recent"),
                "chronicle": ctx.get("chronicle")[-5:] if ctx.get("chronicle") else [],
            }
            import json

            user_content = (
                f"Founder question: {question}\n\n"
                f"Cubit organizational context (source of truth — do not invent beyond this):\n"
                f"{json.dumps(compact, indent=2, default=str)}"
            )
            resp = client.chat.completions.create(
                model=os.environ.get("CUBIT_OPENAI_MODEL", "gpt-4o-mini"),
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_content},
                ],
                temperature=0.3,
            )
            answer = resp.choices[0].message.content or ""
            return {"mode": "openai", "answer": answer, "context_used": "full_snapshot"}
        except Exception as e:
            return {
                "mode": "local_fallback",
                "answer": f"LLM call failed ({e}). Local briefing:\n\n{briefing_text}",
                "context_used": "briefing",
            }
