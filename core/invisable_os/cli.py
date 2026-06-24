"""``invisable`` — the operational command line.

    invisable migrate           # create database tables
    invisable serve             # run the API
    invisable demo              # run the whole platform once, offline
    invisable plan [--persist]  # run the day's 20 posts (optionally into the queue)
    invisable queue [--status]  # list the approval queue
    invisable approve <id>      # approve a queued item
    invisable publish           # take approved items live (dry-run unless Postiz set)
    invisable seed-tags         # add a couple of example tag-network members
    invisable seed-channels     # add channels + a default posting schedule
    invisable schedule          # assign approved items to the next open slots
    invisable calendar          # show scheduled posts by day
    invisable produce <id>      # render a queued item's media assets
    invisable scan <mode>       # run a Remix scanner (e.g. scan_tool_theft)
    invisable remix <mode>      # run a Remix create mode (e.g. create_parody --topic ...)
    invisable seed-popculture   # seed the pop-culture & meme index
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


def _scan(args) -> int:
    from invisable_os.engines.remix import RemixTrendEngine
    from invisable_os.models.remix import ContentMode

    try:
        mode = ContentMode(args.mode)
    except ValueError:
        print(f"unknown scan mode '{args.mode}'. "
              f"Try one of: {', '.join(m.value for m in RemixTrendEngine.SCAN_MODES)}")
        return 1
    result = RemixTrendEngine().run(mode)
    print(f"✓ {result['count']} signal(s) from {mode.value}")
    for it in result["items"]:
        print(f"  [{it['category']:22}] q={it['score']:.2f} {it['title'][:60]}")
    return 0


def _remix(args) -> int:
    from invisable_os.engines.remix import RemixTrendEngine
    from invisable_os.models.remix import ContentMode

    try:
        mode = ContentMode(args.mode)
    except ValueError:
        print(f"unknown create mode '{args.mode}'. "
              f"Try one of: {', '.join(m.value for m in RemixTrendEngine.CREATE_MODES)}")
        return 1
    result = RemixTrendEngine().run(mode, topic=args.topic or "")
    print(json.dumps(result, indent=2))
    return 0


def _seed_popculture(_args) -> int:
    from invisable_os.engines.remix import PopCultureIndex
    from invisable_os.store import get_repository, init_db

    init_db()
    repo = get_repository()
    index = PopCultureIndex()
    n = 0
    for ref in index.references:
        repo.add_pop_culture(ref.model_dump())
        n += 1
    for fmt in index.formats:
        repo.add_meme_format(fmt.model_dump())
        n += 1
    print(f"✓ seeded {n} pop-culture references / meme formats")
    return 0


def _seed_channels(_args) -> int:
    from invisable_os.models.content import Platform
    from invisable_os.models.scheduling import Channel
    from invisable_os.scheduling import default_week
    from invisable_os.store import get_repository, init_db

    init_db()
    repo = get_repository()
    for name, platform, handle in (
        ("INVISABLE Instagram", Platform.INSTAGRAM, "@invisable"),
        ("INVISABLE TikTok", Platform.TIKTOK, "@invisable"),
    ):
        ch = Channel(name=name, platform=platform, handle=handle)
        repo.add_channel(ch)
        for slot in default_week(ch.id):
            repo.add_slot(slot)
    print("✓ seeded 2 channels with a Mon–Fri × 3-slot posting schedule")
    return 0


def _calendar(_args) -> int:
    from invisable_os.services import calendar
    from invisable_os.store import init_db

    init_db()
    cal = calendar()
    if not cal:
        print("(no scheduled posts — approve items then `invisable schedule`)")
    for day, items in cal.items():
        print(f"{day}: {len(items)} post(s)")
        for it in items:
            print(f"    {it['scheduled_at'][11:16]}  {it['pillar']:10} "
                  f"{it['candidate'].get('hook', '')[:42]}")
    return 0


def _schedule(_args) -> int:
    from invisable_os.models.content import QueueStatus
    from invisable_os.services import schedule_next
    from invisable_os.store import get_repository, init_db

    init_db()
    repo = get_repository()
    approved = repo.list_queue(QueueStatus.APPROVED.value)
    if not approved:
        print("(no approved items to schedule)")
        return 0
    for item in approved:
        res = schedule_next(item["id"])
        if "error" in res:
            print(f"  skip {item['id'][:8]}: {res['error']}")
        else:
            print(f"  ✓ {item['id'][:8]} → {res['scheduled_at']} on {res['channel']}")
    return 0


def _produce(args) -> int:
    from invisable_os.services import produce_media
    from invisable_os.store import init_db

    init_db()
    res = produce_media(args.id)
    if "error" in res:
        print(res["error"], args.id)
        return 1
    print(f"✓ produced {res['produced']} assets for {args.id[:8]}")
    for a in res["assets"]:
        print(f"    [{a['backend']:10}] {a['kind']:14} {a['path']}")
    return 0


def _assemble(args) -> int:
    from invisable_os.services import assemble_post
    from invisable_os.store import init_db

    init_db()
    res = assemble_post(args.id)
    if "error" in res:
        print(res["error"], args.id)
        return 1
    print(f"✓ assembled [{res['backend']}] final video for {args.id[:8]}: {res['final_video']}")
    print(f"    inputs: {res['inputs']}")
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

    sub.add_parser("publish", help="take due items live").set_defaults(func=_publish)
    p_seed = sub.add_parser("seed-tags", help="add example tag-network members")
    p_seed.set_defaults(func=_seed_tags)

    p_seedc = sub.add_parser("seed-channels", help="add channels + a default posting schedule")
    p_seedc.set_defaults(func=_seed_channels)
    sub.add_parser("schedule", help="assign approved items to the next open slots").set_defaults(
        func=_schedule
    )
    sub.add_parser("calendar", help="show scheduled posts by day").set_defaults(func=_calendar)

    p_produce = sub.add_parser("produce", help="render a queued item's media assets")
    p_produce.add_argument("id")
    p_produce.set_defaults(func=_produce)

    p_assemble = sub.add_parser("assemble", help="stitch a post's assets into a final video")
    p_assemble.add_argument("id")
    p_assemble.set_defaults(func=_assemble)

    p_scan = sub.add_parser("scan", help="run a Remix scanner mode (e.g. scan_tool_theft)")
    p_scan.add_argument("mode", help="a scan_* ContentMode")
    p_scan.set_defaults(func=_scan)

    p_remix = sub.add_parser("remix", help="run a Remix create mode (e.g. create_parody)")
    p_remix.add_argument("mode", help="a create_* ContentMode")
    p_remix.add_argument("--topic", default="", help="topic / trend to remix")
    p_remix.set_defaults(func=_remix)

    sub.add_parser(
        "seed-popculture", help="seed the pop-culture & meme index"
    ).set_defaults(func=_seed_popculture)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
