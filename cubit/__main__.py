"""CLI entry: python -m cubit ..."""
from __future__ import annotations

import argparse
import json
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cubit", description="Cubit OS — AI Operations Manager")
    sub = parser.add_subparsers(dest="cmd")

    sub.add_parser("briefing", help="Founder briefing")
    sub.add_parser("steward", help="Alignment review")
    sub.add_parser("context", help="Full JSON snapshot")
    sub.add_parser("chronicle", help="Chronicle events")
    sub.add_parser("history", help="Alias for chronicle")
    sub.add_parser("registry", help="Department list")

    p_projects = sub.add_parser("projects", help="List or archive projects")
    p_projects.add_argument("action", nargs="?", choices=["archive"], help="archive <name>")
    p_projects.add_argument("name", nargs="?", help="Project name for archive")
    p_projects.add_argument("--all", action="store_true", help="Include archived")

    p_tasks = sub.add_parser("tasks", help="Task operations")
    p_tasks.add_argument("action", nargs="?", choices=["add", "complete", "status"], help="Action")
    p_tasks.add_argument("value", nargs="?", help="Title, task-id, or status")
    p_tasks.add_argument("--project", help="Project name")
    p_tasks.add_argument("--status", help="Filter or set status")

    p_journal = sub.add_parser("journal", help="Record decision or lesson")
    p_journal.add_argument("kind", nargs="?", choices=["decision", "lesson"])
    p_journal.add_argument("text", nargs="?", default="")
    p_journal.add_argument("--reason", default="")
    p_journal.add_argument("--context", default="")

    p_reason = sub.add_parser("reason", help="Optional LLM over state")
    p_reason.add_argument("question", nargs="+", help="Question text")

    p_builder = sub.add_parser("builder", help="Create departments")
    p_builder.add_argument("action", nargs="?", choices=["create"])
    p_builder.add_argument("name", nargs="?")
    p_builder.add_argument("--description", default="")

    p_chat = sub.add_parser("chat", help="NL interface / REPL")
    p_chat.add_argument("text", nargs="*", help="Optional single message")

    p_web = sub.add_parser("web", help="Local dashboard")
    p_web.add_argument("--port", type=int, default=8080)


    p_api = sub.add_parser("api", help="API framework helpers")
    p_api.add_argument("action", nargs="?", choices=["routes", "key", "keys", "open-mode-hint"])
    p_api.add_argument("--name", default="default")

    p_commerce = sub.add_parser("commerce", help="Optional Stripe commerce status (off by default)")
    p_commerce.add_argument("action", nargs="?", choices=["status", "wallet", "checkout"], default="status")
    p_commerce.add_argument("--amount", type=float, default=10.0)
    p_commerce.add_argument("--currency", default="usd")
    p_commerce.add_argument("--description", default="Cubit OS")


    p_adv = sub.add_parser("advocate", help="Personal Advocate offline task agent")
    p_adv.add_argument("action", nargs="?", choices=["status", "list", "add", "process", "cancel"], default="status")
    p_adv.add_argument("--type", default="email", help="phonecall|email|appointment|sales|pr|research|followup")
    p_adv.add_argument("--title", default="")
    p_adv.add_argument("--details", default="")
    p_adv.add_argument("--contact", default="")
    p_adv.add_argument("--id", default="")
    p_adv.add_argument("--steps", type=int, default=5)

    args = parser.parse_args(argv)

    if args.cmd is None:
        parser.print_help()
        return 0

    if args.cmd == "briefing":
        from cubit.ai.briefing_builder import BriefingBuilder
        print(BriefingBuilder().render())
        return 0

    if args.cmd == "steward":
        from cubit.council.steward import Steward
        r = Steward().review()
        print(json.dumps(r, indent=2))
        return 0

    if args.cmd == "context":
        from cubit.ai.context_builder import ContextBuilder
        print(json.dumps(ContextBuilder().build(), indent=2, default=str))
        return 0

    if args.cmd in ("chronicle", "history"):
        from cubit.chronicle.historian import Historian
        for e in Historian().recent_history(20):
            print(f"[{e.get('date', '')[:19]}] {e.get('event', '')} — {e.get('significance', '')}")
        return 0

    if args.cmd == "registry":
        from cubit.registry.store import Registry
        for d in Registry().list():
            print(f"[{d.get('status')}] {d.get('name')}: {d.get('description', '')}")
        return 0

    if args.cmd == "projects":
        from cubit.projects.agent import ProjectAgent
        pa = ProjectAgent()
        if args.action == "archive" and args.name:
            # Direct CLI archive journals as Founder action; prefer chat for gated flow
            from cubit.journal.store import Journal
            result = pa.archive_project(args.name)
            if result:
                Journal().record_decision(
                    decision=f"CLI archive project: {args.name}",
                    reason="Direct CLI action by Founder",
                    outcome="success",
                    tags=["cli", "archive"],
                )
                print(f"Archived: {args.name}")
            else:
                print(f"Project not found: {args.name}")
            return 0
        for p in pa.get_projects(include_archived=args.all):
            print(f"[{p.get('status')}] {p['name']} — next: {p.get('next_action', '—')}")
        return 0

    if args.cmd == "tasks":
        from cubit.agents.task_agent import TaskAgent
        from cubit.journal.store import Journal
        ta = TaskAgent()
        if args.action == "add" and args.value:
            t = ta.add_task(title=args.value, project=args.project)
            Journal().record_decision(
                decision=f"CLI add task: {args.value}",
                reason="Direct CLI action by Founder",
                outcome="success",
                tags=["cli", "task"],
            )
            print(f"Added {t['id']}: {t['title']} (prefer chat for gated workflow)")
            return 0
        if args.action == "complete" and args.value:
            t = ta.complete_task(args.value)
            if t:
                Journal().record_decision(
                    decision=f"CLI complete task: {args.value}",
                    reason="Direct CLI action by Founder",
                    outcome="success",
                    tags=["cli", "task"],
                )
                print(f"Completed: {t['id']}")
            else:
                print(f"Task not found: {args.value}")
            return 0
        if args.action == "status" and args.value and args.status:
            t = ta.update_status(args.value, args.status)
            print(t or f"Not found: {args.value}")
            return 0
        # list grouped
        groups = ta.grouped_by_project()
        for proj, tasks in groups.items():
            print(f"\n## {proj}")
            for t in tasks:
                if args.status and t.get("status") != args.status:
                    continue
                if args.project and t.get("project") != args.project:
                    continue
                print(f"  [{t['status']}] {t['id']}: {t['title']}")
        return 0

    if args.cmd == "journal":
        from cubit.journal.store import Journal
        j = Journal()
        if args.kind == "decision" and args.text:
            e = j.record_decision(decision=args.text, reason=args.reason)
            print(json.dumps(e, indent=2))
        elif args.kind == "lesson" and args.text:
            e = j.record_lesson(lesson=args.text, context=args.context)
            print(json.dumps(e, indent=2))
        else:
            for e in j.recent(15):
                print(json.dumps(e, default=str))
        return 0

    if args.cmd == "reason":
        from cubit.ai.reasoner import Reasoner
        q = " ".join(args.question)
        result = Reasoner().reason(q)
        print(f"[{result['mode']}]\n{result['answer']}")
        return 0

    if args.cmd == "builder":
        from cubit.builder.department import Builder
        if args.action == "create" and args.name:
            # Prefer gated path; CLI still works for scaffolding
            from cubit.ai.conversation import ConversationalLayer
            cl = ConversationalLayer()
            prop = cl.create_proposal(
                action="create_department",
                description=f"Create department {args.name}",
                params={"name": args.name, "description": args.description, "status": "active", "scaffold": True},
            )
            print(f"Proposal {prop['id']} created. Approve via: cubit chat \"approve {prop['id']}\"")
        else:
            from cubit.registry.store import Registry
            for d in Registry().list():
                print(f"[{d.get('status')}] {d.get('name')}")
        return 0

    if args.cmd == "chat":
        from cubit.ai.conversation import ConversationalLayer
        cl = ConversationalLayer()
        if args.text:
            result = cl.handle(" ".join(args.text))
            print(result["message"])
            return 0
        print("Cubit chat (type 'quit' to exit). Significant actions require approve prop-XXX.")
        while True:
            try:
                line = input("you> ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                break
            if not line or line.lower() in ("quit", "exit", "q"):
                break
            result = cl.handle(line)
            print(result["message"])
            print()
        return 0

    if args.cmd == "web":
        try:
            import uvicorn
            from cubit.web.app import app
            print(f"Starting Cubit dashboard at http://127.0.0.1:{args.port}")
            uvicorn.run(app, host="127.0.0.1", port=args.port, log_level="info")
        except ImportError:
            print("Web dependencies missing. pip install fastapi uvicorn jinja2 python-multipart")
            return 1
        return 0


    if args.cmd == "api":
        from cubit.api.router import ApiRouter
        from cubit.api.framework import ApiFramework
        if args.action == "routes":
            for r in ApiRouter().list_routes():
                print(f"{r['method']:6} {r['path']:40} scope={r['scope']}")
        elif args.action == "key":
            created = ApiFramework().keys.create_key(name=args.name)
            print("API key created (store now, shown once):")
            print(created.get("key"))
            print(f"id={created.get('id')} prefix={created.get('prefix')}")
        elif args.action == "keys":
            for k in ApiFramework().keys.list_keys():
                print(k)
        else:
            print("Actions: routes | key | keys")
            print("Auth: Authorization: Bearer <key>")
            print("Local open mode: export CUBIT_API_OPEN=1")
        return 0

    if args.cmd == "commerce":
        from cubit.commerce.stripe_wallet import CommerceGateway
        import json
        gw = CommerceGateway()
        if args.action == "checkout":
            if not gw.enabled:
                print(json.dumps(gw.status(), indent=2))
                print("Enable with CUBIT_COMMERCE=1 and STRIPE_SECRET_KEY")
                return 1
            session = gw.create_checkout(
                amount_cents=int(args.amount * 100),
                currency=args.currency,
                description=args.description,
            )
            print(json.dumps(session, indent=2))
            return 0
        if args.action == "wallet" and gw.enabled:
            print(json.dumps(gw.wallet_summary(), indent=2))
        else:
            print(json.dumps(gw.status(), indent=2))
        return 0


    if args.cmd == "advocate":
        from cubit.advocate.agent import AdvocateAgent
        import json
        adv = AdvocateAgent()
        if args.action == "list":
            print(json.dumps(adv.list_tasks(), indent=2, default=str))
        elif args.action == "add":
            task = adv.enqueue(args.type, args.title or "Untitled", args.details, args.contact)
            print(json.dumps(task, indent=2, default=str))
        elif args.action == "process":
            print(json.dumps(adv.process_offline(args.steps), indent=2, default=str))
        elif args.action == "cancel":
            print(json.dumps(adv.cancel(args.id) or {"error": "not found"}, indent=2, default=str))
        else:
            print(json.dumps(adv.status(), indent=2, default=str))
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
