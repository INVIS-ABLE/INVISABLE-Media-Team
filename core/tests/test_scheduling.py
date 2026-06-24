from datetime import UTC, datetime

from invisable_os.models.content import Platform, QueueStatus
from invisable_os.models.scheduling import Channel, ScheduleSlot
from invisable_os.scheduling import calendar_by_day, default_week, next_open_slot
from invisable_os.services import schedule_next
from invisable_os.store import get_repository


def test_next_open_slot_finds_earliest_future_slot():
    # A Wednesday 12:00 UTC starting point.
    after = datetime(2026, 6, 24, 12, 0, tzinfo=UTC)
    slots = [
        ScheduleSlot(channel_id="c", weekday=2, hour=9, minute=0),   # Wed 09:00 (past today)
        ScheduleSlot(channel_id="c", weekday=2, hour=17, minute=0),  # Wed 17:00 (next)
    ]
    when = next_open_slot(slots, after=after, tz="UTC")
    assert when.hour == 17 and when.day == 24


def test_next_open_slot_skips_taken():
    after = datetime(2026, 6, 24, 12, 0, tzinfo=UTC)
    wed17 = datetime(2026, 6, 24, 17, 0, tzinfo=UTC)
    slots = [ScheduleSlot(channel_id="c", weekday=2, hour=17, minute=0)]
    when = next_open_slot(slots, after=after, taken={wed17}, tz="UTC")
    # 17:00 taken → next Wednesday.
    assert when.day == 1 and when.month == 7


def test_default_week_has_fifteen_slots():
    assert len(default_week("c")) == 15  # 5 weekdays × 3 times


def test_schedule_next_assigns_slot_to_approved_item():
    repo = get_repository()
    ch = Channel(name="IG", platform=Platform.INSTAGRAM)
    repo.add_channel(ch)
    for slot in default_week(ch.id):
        repo.add_slot(slot)

    item_id = repo.enqueue(
        {
            "candidate_id": "c1",
            "candidate": {"hook": "h", "platform": "instagram"},
            "status": QueueStatus.APPROVED.value,
            "platform": "instagram",
        }
    )
    res = schedule_next(item_id)
    assert "scheduled_at" in res
    assert repo.get_queue_item(item_id)["status"] == "scheduled"


def test_schedule_next_without_channel_reports_error():
    repo = get_repository()
    item_id = repo.enqueue(
        {"candidate_id": "c", "candidate": {"platform": "youtube"}, "platform": "youtube",
         "status": QueueStatus.APPROVED.value}
    )
    assert "error" in schedule_next(item_id)


def test_calendar_groups_by_day():
    items = [
        {"scheduled_at": "2026-06-24T17:00:00+00:00", "id": "a"},
        {"scheduled_at": "2026-06-24T09:00:00+00:00", "id": "b"},
        {"scheduled_at": "2026-06-25T09:00:00+00:00", "id": "c"},
        {"scheduled_at": None, "id": "d"},
    ]
    cal = calendar_by_day(items)
    assert set(cal) == {"2026-06-24", "2026-06-25"}
    assert len(cal["2026-06-24"]) == 2
