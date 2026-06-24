"""``invisable`` — the operational command line.

    invisable migrate           # create database tables
    invisable serve             # run the API
    invisable demo              # run the whole platform once, offline
    invisable plan [--persist]  # run the day's 20 posts (optionally into the queue)
    invisable queue [--status]  # list the approval queue
    invisable approve <id>      # approve a queued item
    invisable publish           # take approved items live (dry-run unless Postiz set)
    invisable seed-tags         # add a couple of example tag-network members
"""

from __future__ import annotations

import argparse
import json
import sys


def _migrate(_args) -> int:
    from invisable_os.store import init_db

    init_db()
    print("✓ database tables ready")
    return 0


def _serve(args) -> int:
    import uvicorn

    from invisable_os.config import get_settings
    from invisable_os.store import init_db

    init_db()
    settings = get_settings()
    uvicorn.run(
        "invisable_os.main:app",
        host=settings.api_host,
        port=args.port or settings.api_port,
        reload=args.reload,
    )
    return 0


def _demo(_args) -> int:
    from invisable_os.demo import main as demo_main

    demo_main()
    return 0


def _plan(args) -> int:
    from invisable_os.engines.daily import DailyContentDirector

    if args.persist:
        from invisable_os.services import run_and_queue_daily
        from invisable_os.store import init_db

        init_db()
        summary = run_and_queue_daily(candidates_per_slot=args.per_slot)
        print(f"✓ queued {len(summary['queued_ids'])} posts "
              f"({summary['total_assets']} assets); needs_improvement="
              f"{summary['needs_improvement']}")
    else:
        summary = DailyContentDirector().plan_day(candidates_per_slot=args.per_slot).summary()
        print(json.dumps(summary, indent=2))
    return 0


def _queue(args) -> int:
    from invisable_os.store import get_repository, init_db

    init_db()
    items = get_repository().list_queue(status=args.status)
    print(f"{len(items)} item(s)" + (f" with status={args.status}" if args.status else ""))
    for it in items:
        cand = it["candidate"]
        print(f"  [{it['status']:16}] {it['pillar']:10} q={it['quality_avg']:.1f} "
              f"m={it['mission_total']:.2f} {cand.get('hook', '')[:50]}  ({it['id'][:8]})")
    return 0


def _approve(args) -> int:
    from invisable_os.models.content import QueueStatus
    from invisable_os.store import get_repository, init_db

    init_db()
    res = get_repository().transition(args.id, QueueStatus.APPROVED)
    print("✓ approved" if res else "not found", args.id)
    return 0 if res else 1


def _publish(_args) -> int:
    from invisable_os.services import publish_due
    from invisable_os.store import init_db

    init_db()
    report = publish_due()
    print(f"✓ published {report['count']} via {report['backend']}; failed={len(report['failed'])}")
    return 0


def _seed_tags(_args) -> int:
    from invisable_os.models.departments import TagNetworkMember
    from invisable_os.store import get_repository, init_db

    init_db()
    repo = get_repository()
    for m in (
        TagNetworkMember(display_name="Bald Builders", instagram_handle="@baldbuilders",
                         tiktok_handle="@baldbuilders", category="partner"),
        TagNetworkMember(display_name="CT1", instagram_handle="@ct1sealantandadhesive",
                         category="sponsor"),
    ):
        repo.add_tag_member(m)
    print("✓ seeded example tag-network members")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="invisable", description="INVISABLE OS operations")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("migrate", help="create database tables").set_defaults(func=_migrate)

    p_serve = sub.add_parser("serve", help="run the API")
    p_serve.add_argument("--port", type=int, default=None)
    p_serve.add_argument("--reload", action="store_true")
    p_serve.set_defaults(func=_serve)

    sub.add_parser("demo", help="run the whole platform once, offline").set_defaults(func=_demo)

    p_plan = sub.add_parser("plan", help="run the day's 20 posts")
    p_plan.add_argument("--persist", action="store_true", help="persist into the approval queue")
    p_plan.add_argument("--per-slot", type=int, default=12, dest="per_slot")
    p_plan.set_defaults(func=_plan)

    p_queue = sub.add_parser("queue", help="list the approval queue")
    p_queue.add_argument("--status", default=None)
    p_queue.set_defaults(func=_queue)

    p_approve = sub.add_parser("approve", help="approve a queued item")
    p_approve.add_argument("id")
    p_approve.set_defaults(func=_approve)

    sub.add_parser("publish", help="take approved items live").set_defaults(func=_publish)
    p_seed = sub.add_parser("seed-tags", help="add example tag-network members")
    p_seed.set_defaults(func=_seed_tags)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
