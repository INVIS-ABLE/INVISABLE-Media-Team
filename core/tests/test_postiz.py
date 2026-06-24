"""Postiz publisher: pure payload builder + MockTransport network path + service."""

import json
from datetime import UTC, datetime

import httpx

from invisable_os.publish.base import PublishResult
from invisable_os.publish.postiz import PostizPublisher, build_postiz_payload, post_text
from invisable_os.services.scheduler import schedule_to_postiz

ITEM = {
    "id": "q1",
    "candidate_id": "c1",
    "platform": "instagram",
    "tags": ["#invisable"],
    "candidate": {"hook": "You don't look ill", "body": "but it's real", "call_to_action": "Share"},
}
INTEGRATIONS = {"instagram": "intg_1", "tiktok": "intg_2"}
WHEN = datetime(2026, 7, 1, 9, 30, tzinfo=UTC)


# --- Pure payload builder ---------------------------------------------------


def test_post_text_joins_parts():
    assert post_text(ITEM) == "You don't look ill\n\nbut it's real\n\nShare"


def test_build_payload_immediate():
    payload = build_postiz_payload(ITEM, INTEGRATIONS)
    assert payload["type"] == "now"
    assert "date" not in payload
    assert payload["posts"][0]["integration"]["id"] == "intg_1"
    assert payload["tags"] == ["#invisable"]


def test_build_payload_scheduled():
    payload = build_postiz_payload(ITEM, INTEGRATIONS, when=WHEN)
    assert payload["type"] == "schedule"
    assert payload["date"] == WHEN.isoformat()


def test_build_payload_unmapped_platform_has_no_integration():
    payload = build_postiz_payload({**ITEM, "platform": "threads"}, INTEGRATIONS)
    assert "integration" not in payload["posts"][0]


# --- Network path via MockTransport -----------------------------------------


def _mock_publisher(handler, **kw) -> PostizPublisher:
    return PostizPublisher(
        base_url="https://postiz.test", api_key="k",
        integrations=INTEGRATIONS, transport=httpx.MockTransport(handler), **kw,
    )


def test_publish_posts_now_and_returns_external_id():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["body"] = json.loads(request.read())
        captured["auth"] = request.headers.get("authorization")
        return httpx.Response(200, json={"id": "post_42"})

    result = _mock_publisher(handler).publish(ITEM)
    assert result.ok and result.external_id == "post_42"
    assert captured["url"].endswith("/public/v1/posts")
    assert captured["auth"] == "Bearer k"
    assert captured["body"]["type"] == "now"


def test_schedule_sends_schedule_type_and_date():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = json.loads(request.read())
        return httpx.Response(201, json={"id": "post_99"})

    result = _mock_publisher(handler).schedule(ITEM, WHEN)
    assert result.ok and result.external_id == "post_99"
    assert captured["body"]["type"] == "schedule"
    assert captured["body"]["date"] == WHEN.isoformat()


def test_unmapped_platform_is_a_clear_error_not_a_post():
    def handler(request):  # pragma: no cover - must never be called
        raise AssertionError("should not POST for an unmapped platform")

    result = _mock_publisher(handler).publish({**ITEM, "platform": "threads"})
    assert not result.ok
    assert "no Postiz integration" in result.detail


def test_http_error_degrades_gracefully():
    def handler(request):
        return httpx.Response(500, json={"error": "boom"})

    result = _mock_publisher(handler).publish(ITEM)
    assert not result.ok
    assert result.backend == "postiz"


def test_unconfigured_publisher_is_dry_run_safe(monkeypatch):
    monkeypatch.delenv("POSTIZ_API_URL", raising=False)
    monkeypatch.delenv("POSTIZ_API_KEY", raising=False)
    pub = PostizPublisher()
    assert pub.configured is False
    assert pub.publish(ITEM).ok is False


# --- Service ----------------------------------------------------------------


class _FakeRepo:
    def __init__(self, item):
        self._item = item
        self.transitions = []

    def get_queue_item(self, item_id):
        return self._item if self._item and self._item["id"] == item_id else None

    def transition(self, item_id, status, tags=None):
        self.transitions.append((item_id, status))
        return {"id": item_id, "status": status}


class _OkPublisher:
    def schedule(self, item, when):
        return PublishResult(ok=True, backend="postiz", external_id="ext1", detail="scheduled")


def test_schedule_to_postiz_marks_item_scheduled():
    repo = _FakeRepo(ITEM)
    out = schedule_to_postiz("q1", WHEN, repository=repo, publisher=_OkPublisher())
    assert out["ok"] is True
    assert out["external_id"] == "ext1"
    assert repo.transitions and repo.transitions[0][0] == "q1"


def test_schedule_to_postiz_unknown_item():
    out = schedule_to_postiz("nope", WHEN, repository=_FakeRepo(None), publisher=_OkPublisher())
    assert out["ok"] is False
    assert out["error"] == "not found"
