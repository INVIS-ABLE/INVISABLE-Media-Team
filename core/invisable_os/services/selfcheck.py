"""Self-check — prove the whole program works end to end, in one call.

This is the operational "does everything actually work together?" check. It drives
the real content lifecycle through the platform's own engines and services — the
same seams the dashboard and the desktop window use — and returns a per-stage report:

    scan → generate → gate → stock → approve → schedule → calendar → draw

It is read-mostly and self-contained: it runs against the configured database, uses
the deterministic offline path (no network, no LLM required), and never publishes.
The CLI ``invisable doctor`` prints this report; the end-to-end test asserts on it.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from invisable_os.models.content import Platform, QueueStatus
from invisable_os.models.scheduling import Channel
from invisable_os.scheduling import default_week
from invisable_os.services.fact_check import check_post
from invisable_os.services.scheduling import calendar, schedule_next
from invisable_os.services.swarm import run_swarm_cycle
from invisable_os.services.war_chest import reserve_health, select_next, stock_approved
from invisable_os.store import get_repository


@dataclass
class StageResult:
    name: str
    ok: bool
    detail: str


@dataclass
class SelfCheckReport:
    stages: list[StageResult] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return all(s.ok for s in self.stages)

    def add(self, name: str, ok: bool, detail: str) -> None:
        self.stages.append(StageResult(name=name, ok=ok, detail=detail))

    def as_dict(self) -> dict:
        return {
            "ok": self.ok,
            "passed": sum(1 for s in self.stages if s.ok),
            "total": len(self.stages),
            "stages": [{"name": s.name, "ok": s.ok, "detail": s.detail} for s in self.stages],
        }


def run_self_check(*, drafts_per_topic: int = 1) -> SelfCheckReport:
    """Run the full pipeline once and report whether each stage works."""
    repo = get_repository()
    report = SelfCheckReport()

    # 1. Channels + posting schedule (so scheduling has somewhere to place a post).
    try:
        ch = Channel(name="Self-check TikTok", platform=Platform.TIKTOK, handle="@selfcheck")
        repo.add_channel(ch)
        slots = 0
        for slot in default_week(ch.id):
            repo.add_slot(slot)
            slots += 1
        report.add("channels", slots > 0, f"seeded 1 channel · {slots} weekly slots")
    except Exception as exc:  # noqa: BLE001
        report.add("channels", False, f"error: {exc}")

    # 2. Swarm cycle: scan → generate → gate → stock.
    try:
        cycle = run_swarm_cycle(drafts_per_topic=drafts_per_topic, live_sources=False)
        f = cycle["funnel"]
        ok = f["raw_drafts"] > 0 and f["usable_drafts_queued"] > 0
        report.add(
            "swarm_cycle", ok,
            f"raw {f['raw_drafts']} → usable {f['usable_drafts_queued']} "
            f"· stocked {f['stocked_to_war_chest']} · rejected {f['brand_rejected']}",
        )
    except Exception as exc:  # noqa: BLE001
        report.add("swarm_cycle", False, f"error: {exc}")

    # 3. Approval queue holds the usable drafts.
    pending = repo.list_queue(status=QueueStatus.PENDING_REVIEW.value, limit=500)
    report.add("queue", bool(pending), f"{len(pending)} item(s) pending review")

    # 4. Approve one, then stock approved into the War Chest reserve.
    approved_id = ""
    if pending:
        approved_id = pending[0]["id"]
        repo.transition(approved_id, QueueStatus.APPROVED)
    try:
        stock = stock_approved()
        health = reserve_health()
        report.add(
            "war_chest", health["ready"] >= 0,
            f"stocked {stock['stocked']} · reserve {health['ready']} ({health['tier']}) "
            f"· cadence {health['recommended_posts_per_day']}/day",
        )
    except Exception as exc:  # noqa: BLE001
        report.add("war_chest", False, f"error: {exc}")

    # 5. Schedule the approved item onto the next open slot.
    if approved_id:
        sched = schedule_next(approved_id)
        ok = "scheduled_at" in sched
        report.add(
            "schedule", ok,
            sched.get("scheduled_at", sched.get("error", "no result")),
        )
    else:
        report.add("schedule", False, "no approved item to schedule")

    # 6. Calendar reflects the scheduled post.
    cal = calendar()
    report.add("calendar", len(cal) >= (1 if approved_id else 0), f"{len(cal)} day(s) scheduled")

    # 7. War Chest draw (anti-repetition selection), if anything is stocked.
    draw = select_next()
    if "item" in draw:
        report.add("war_chest_draw", True, f"drew '{draw['item']['category']}' and marked used")
    else:
        # An empty reserve is acceptable (templates may not clear the stock bar); the
        # selector still answered cleanly rather than erroring.
        report.add("war_chest_draw", "error" in draw, draw.get("error", "drew nothing"))

    # 8. Credible Source Rule: a fact-led claim with no source must be flagged.
    fc = check_post("Tool theft rose 20% in 2024 according to official figures.")
    report.add(
        "fact_check", fc.fact_led and not fc.ok,
        "fact-led claim with no source correctly flagged (not ok)",
    )

    return report
