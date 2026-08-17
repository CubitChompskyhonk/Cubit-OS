# Cubit OS

**AI Operations Manager and strategic partner for the Founder.**

Free, local-first. No wallet, payments, or subscriptions.

## Mission

Transform the Founder's ideas into organized, actionable projects while preserving intent and purpose.

## Architectural law

```
Founder → Cubit analyzes → Cubit proposes → Founder decides → System acts → Historian records
```

Significant mutations require **explicit Founder approval** via the Approval Gate.

## Quick start

```bash
cd cubit_os
python -m venv .venv
source .venv/bin/activate  # or Windows equivalent
pip install -r requirements.txt  # optional deps for web/LLM

# CLI
python -m cubit briefing
python -m cubit steward
python -m cubit chat
python -m cubit chat "create project My Idea"
python -m cubit chat "approve prop-001"

# Web dashboard
python -m cubit web --port 8080
# open http://127.0.0.1:8080
```

Optional OpenAI: set `OPENAI_API_KEY` or `CUBIT_OPENAI_API_KEY`. Without a key, `reason` falls back to local briefing text.

## Core principles

1. Preserve Founder intent  
2. Explain reasoning  
3. Identify risks  
4. Prefer simple, reliable solutions  
5. Maintain continuity (journal + chronicle)  
6. Ask when information is missing  
7. Ethical outcomes over short-term gains  

**Metaphor:** Foundation before expansion. Deliberate placement of the cube.

## Package layout

See the recreation spec. Departments: Steward, Advisor, Historian, Builder.

## Tests

```bash
python tests/test_smoke.py
```

## Android (optional)

Chaquopy + WebView shell pointing at local uvicorn on `127.0.0.1:8765`. Free APK via GitHub Actions → Releases. No billing libraries.

## License / policy

Free. No payment code paths. Core features fully local.
