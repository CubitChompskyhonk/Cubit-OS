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

## Quick start (desktop / CLI)

```bash
cd Cubit-OS
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

python -m cubit briefing
python -m cubit chat
python -m cubit chat "create project My Idea"
python -m cubit chat "approve prop-001"
python -m cubit web --port 8080
```

Optional OpenAI: set `OPENAI_API_KEY` or `CUBIT_OPENAI_API_KEY`.

## Android free APK

Kotlin WebView + Chaquopy Python 3.11 shell that starts the same dashboard on `127.0.0.1:8765`.

### CI (GitHub Actions)

Workflow: `.github/workflows/android-apk.yml`

- **Trigger:** push to `main`, tags `v*`, or manual `workflow_dispatch`
- **Output artifact:** `CubitOS-free.apk`
- **Tags:** also publishes to **GitHub Releases** (public download URL)

No billing libraries. Debug APK (no store signing secrets required).

### Build locally (optional)

```bash
# Requires JDK 17, Android SDK, Python 3.11
rsync -a --exclude '__pycache__' cubit/ android/app/src/main/python/cubit/
cd android
gradle :app:assembleDebug
# APK: app/build/outputs/apk/debug/
```

## Core principles

1. Preserve Founder intent  
2. Explain reasoning  
3. Identify risks  
4. Prefer simple, reliable solutions  
5. Maintain continuity (journal + chronicle)  
6. Ask when information is missing  
7. Ethical outcomes over short-term gains  

**Metaphor:** Foundation before expansion. Deliberate placement of the cube.

## Tests

```bash
PYTHONPATH=. python tests/test_smoke.py
```

## License / policy

Free. No payment code paths. Core features fully local.
