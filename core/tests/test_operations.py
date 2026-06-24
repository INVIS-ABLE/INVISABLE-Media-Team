"""End-to-end operational flow: plan → queue → approve → publish (dry-run)."""

from invisable_os.models.content import QueueStatus
from invisable_os.publish import get_publisher
from invisable_os.publish.base import DryRunPublisher
from invisable_os.services import publish_due, run_and_queue_daily
from invisable_os.store import get_repository


def test_run_and_queue_daily_persists_full_day():
    summary = run_and_queue_daily(candidates_per_slot=8)
    assert summary["total"] == 20
    assert len(summary["queued_ids"]) == 20
    # Everything landed in the queue with a reviewable status.
    items = get_repository().list_queue()
    assert len(items) == 20
    statuses = {i["status"] for i in items}
    assert statuses <= {"pending_review", "needs_improvement"}


def test_default_publisher_is_dry_run_when_postiz_unset(monkeypatch):
    monkeypatch.delenv("POSTIZ_API_URL", raising=False)
    monkeypatch.delenv("POSTIZ_API_KEY", raising=False)
    assert isinstance(get_publisher(), DryRunPublisher)


def test_approve_then_publish_flow():
    repo = get_repository()
    summary = run_and_queue_daily(candidates_per_slot=8)
    first = summary["queued_ids"][0]

    repo.transition(first, QueueStatus.APPROVED)
    report = publish_due()
    assert report["backend"] == "dry-run"
    assert report["count"] >= 1

    published = repo.get_queue_item(first)
    assert published["status"] == "published"
    assert published["published_at"] is not None


def test_publish_run_records_performance_signal():
    repo = get_repository()
    item_id = repo.enqueue(
        {
            "candidate_id": "c9",
            "candidate": {"hook": "h", "platform": "instagram"},
            "status": QueueStatus.APPROVED.value,
            "platform": "instagram",
        }
    )
    publish_due()
    assert repo.get_queue_item(item_id)["status"] == "published"
