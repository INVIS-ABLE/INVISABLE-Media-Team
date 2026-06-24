"""End-to-end pipeline: harvest → generate → produce → probe → gate → schedule → publish.

This is the integration test that proves the studio's spine works in one pass, using
the *real* service seams with backends in their dry-run / injected form (no GPU, no
network). It's the guard that the engines still compose after future refactors.
"""

from datetime import UTC, datetime

from invisable_os.brain import get_brain
from invisable_os.engines.harvester import IntelligenceHarvester
from invisable_os.media.probes import probe_video
from invisable_os.media.safe_area import Surface
from invisable_os.media.video_qc import VideoQualityGate, VideoSpec
from invisable_os.models.content import Platform, QueueStatus
from invisable_os.models.scheduling import Channel
from invisable_os.publish.base import PublishResult
from invisable_os.scheduling import default_week
from invisable_os.services import (
    produce_media,
    publish_due,
    run_and_queue_daily,
    schedule_next,
    schedule_to_postiz,
)
from invisable_os.store import get_repository


class _StubConnector:
    """A harvest connector returning one abstracted signal — no network."""

    name = "stub"

    def fetch(self, topics):
        return [
            {"topic": topics[0], "kind": "trend", "summary": "abstracted signal",
             "source_type": "web", "score": 0.8}
        ]


class _RecordingPublisher:
    name = "recording"

    def __init__(self):
        self.published = []

    def publish(self, item):
        self.published.append(item["id"])
        return PublishResult(ok=True, backend=self.name, external_id="ext-" + item["id"][:6])


def test_full_pipeline_in_one_pass():
    repo = get_repository()

    # 1. HARVEST — the Research team turns public signals into Brain memories.
    signals = IntelligenceHarvester(connectors=[_StubConnector()]).harvest(["chronic fatigue"])
    assert signals, "harvest produced no signals"
    assert get_brain().count("trend_signal") >= 1, "signals not learned into the Brain"

    # 2. GENERATE + QUEUE — the daily director plans, gates, scores, and persists.
    summary = run_and_queue_daily(candidates_per_slot=4)
    ids = summary["queued_ids"]
    assert ids, "no posts queued"
    item_id = ids[0]
    assert repo.get_queue_item(item_id) is not None

    # 3. PRODUCE — the Content Flywheel's assets render (dry-run) into the library.
    produced = produce_media(item_id)
    assert produced["produced"] >= 5
    assert len(repo.list_media(item_id)) == produced["produced"]

    # 4. PROBE + GATE — measure a clean short and clear the Video Quality Gate.
    spec = probe_video(
        "/no/such/file.mp4",
        VideoSpec(
            platform=Platform.TIKTOK, surface=Surface.REEL,
            width=1080, height=1920, fps=30.0, duration_s=20.0,
            sharpness=0.9, generation_models=["flux-schnell"],  # commercial-clear model
        ),
    )
    assert spec.probe_backend == "dry-run"  # no ffmpeg here, spec passes through
    report = VideoQualityGate().check(spec)
    assert report.passed, report.failures

    # 5. APPROVE + SCHEDULE — assign the item the next open slot on its channel.
    platform = repo.get_queue_item(item_id)["platform"]
    channel = Channel(name="primary", platform=Platform(platform))
    repo.add_channel(channel)
    for slot in default_week(channel.id):
        repo.add_slot(slot)
    repo.transition(item_id, QueueStatus.APPROVED)
    scheduled = schedule_next(item_id)
    assert "scheduled_at" in scheduled, scheduled
    assert repo.get_queue_item(item_id)["status"] == QueueStatus.SCHEDULED.value

    # 6. PUBLISH — once the slot's time has arrived, the item goes live.
    far_future = datetime(2030, 1, 1, tzinfo=UTC)
    publisher = _RecordingPublisher()
    result = publish_due(now=far_future, publisher=publisher)
    assert item_id in publisher.published
    assert result["count"] >= 1
    assert repo.get_queue_item(item_id)["status"] == QueueStatus.PUBLISHED.value


def test_pipeline_native_postiz_scheduling_branch():
    """The Postiz Scheduler Agent's path: hand a queued item to Postiz to schedule."""
    repo = get_repository()
    item_id = repo.enqueue(
        {
            "candidate_id": "c1",
            "candidate": {"hook": "h", "body": "b", "platform": "instagram"},
            "platform": "instagram",
            "status": QueueStatus.APPROVED.value,
            "tags": [],
        }
    )

    class _PostizStub:
        def schedule(self, item, when):
            return PublishResult(ok=True, backend="postiz", external_id="pz1", detail="scheduled")

    out = schedule_to_postiz(
        item_id, datetime(2026, 7, 1, 9, 30, tzinfo=UTC), repository=repo, publisher=_PostizStub()
    )
    assert out["ok"] is True
    assert out["external_id"] == "pz1"
    assert repo.get_queue_item(item_id)["status"] == QueueStatus.SCHEDULED.value


def test_pipeline_gate_blocks_a_bad_asset():
    """The gate is a real barrier: a non-commercial model + wrong aspect fails."""
    spec = VideoSpec(
        platform=Platform.TIKTOK, surface=Surface.REEL,
        width=1080, height=1080,  # square, wrong for a reel
        sharpness=0.9, generation_models=["flux-dev"],  # non-commercial
    )
    report = VideoQualityGate().check(spec)
    assert not report.passed
    assert {"aspect_ratio", "model_licence"} <= set(report.summary()["failures"])
