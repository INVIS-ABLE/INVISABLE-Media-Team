"""ResourceSpace DAM sync + Metricool metrics → Watchtower."""

import httpx
from fastapi.testclient import TestClient

from invisable_os.integrations import MetricoolClient, metricool_to_signals
from invisable_os.integrations.resourcespace import ResourceSpaceClient
from invisable_os.main import app
from invisable_os.models.content import QueueStatus
from invisable_os.models.metrics import PerformanceSignal, SuccessMetric
from invisable_os.services import sync_metrics, sync_post_to_dam
from invisable_os.store import get_repository

# --- ResourceSpace ----------------------------------------------------------


def _rs_handler(request: httpx.Request) -> httpx.Response:
    fn = request.url.params.get("function")
    assert "sign" in request.url.params  # every call is signed
    if fn == "create_resource":
        return httpx.Response(200, json=123)
    if fn == "upload_multipart":
        return httpx.Response(200, json="OK")
    return httpx.Response(404)


def _rs_client(mock=True):
    client = httpx.Client(transport=httpx.MockTransport(_rs_handler)) if mock else None
    return ResourceSpaceClient("http://rs", "admin", "secret", client=client)


def test_resourcespace_configured_flag():
    assert _rs_client().configured is True
    assert ResourceSpaceClient("", "", "").configured is False


def test_resourcespace_sync_file_creates_and_uploads(tmp_path):
    f = tmp_path / "final.mp4"
    f.write_bytes(b"video-bytes")
    res = _rs_client().sync_file(str(f), title="INVISABLE clip")
    assert res["ref"] == "123"
    assert res["url"].endswith("/?r=123")


def test_dam_sync_dry_run_without_real_assets():
    repo = get_repository()
    item_id = repo.enqueue({
        "candidate_id": "c1", "candidate": {"hook": "h"}, "platform": "tiktok",
        "status": QueueStatus.PENDING_REVIEW.value,
    })
    repo.add_media_asset(item_id, "tiktok", "x", "data/x/tiktok.mp4", "dry-run")
    res = sync_post_to_dam(item_id)  # ResourceSpace unconfigured + no real file
    assert res["backend"] == "dry-run"
    assert res["synced"] == []


def test_dam_sync_pushes_real_assets(tmp_path):
    repo = get_repository()
    item_id = repo.enqueue({
        "candidate_id": "c2", "candidate": {"hook": "h"}, "platform": "tiktok",
        "status": QueueStatus.APPROVED.value,
    })
    real = tmp_path / "final.mp4"
    real.write_bytes(b"v")
    repo.add_media_asset(item_id, "final_video", "fv", str(real), "ffmpeg")

    res = sync_post_to_dam(item_id, client=_rs_client())
    assert res["backend"] == "resourcespace"
    assert res["count"] == 1 and res["synced"][0]["ref"] == "123"
    # A dam_ref asset is recorded in the library.
    refs = [a for a in repo.list_media(item_id) if a["kind"] == "dam_ref"]
    assert refs and refs[0]["backend"] == "resourcespace"


# --- Metricool --------------------------------------------------------------


def test_metricool_to_signals_maps_known_metrics():
    records = [{"id": "p1", "provider": "instagram",
                "metrics": {"shares": 10, "saved": 5, "unknownKey": 99}}]
    signals = metricool_to_signals(records)
    metrics = {s.metric for s in signals}
    assert SuccessMetric.SHARES in metrics and SuccessMetric.SAVES in metrics
    assert len(signals) == 2  # unknownKey ignored


def test_metricool_fetch_via_mock_transport():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["X-Mc-Auth"] == "tok"
        return httpx.Response(200, json=[{"id": "p1", "metrics": {"shares": 3}}])
    client = httpx.Client(transport=httpx.MockTransport(handler))
    mc = MetricoolClient("tok", "blog1", client=client)
    assert mc.configured
    recs = mc.fetch(start="2026-06-01", end="2026-06-24")
    assert recs and recs[0]["metrics"]["shares"] == 3


def test_sync_metrics_with_provided_signals_updates_index():
    res = sync_metrics(signals=[
        PerformanceSignal(candidate_id="c1", platform="instagram",
                          metric=SuccessMetric.MEDIA_MENTIONS, value=6),
        PerformanceSignal(candidate_id="c1", platform="instagram",
                          metric=SuccessMetric.SAVES, value=200, themes=["explainer"]),
    ])
    assert res["source"] == "provided"
    assert res["ingested"] == 2
    assert res["founder_recognition_index"] > 0


def test_sync_metrics_offline_is_noop():
    res = sync_metrics()  # no Metricool configured
    assert res["source"] == "none"
    assert res["ingested"] == 0


# --- API --------------------------------------------------------------------


def test_integrations_status_endpoint():
    body = TestClient(app).get("/v1/integrations").json()
    assert body["resourcespace"] is False and body["metricool"] is False
    assert set(body) >= {"resourcespace", "metricool", "postiz", "comfyui", "ffmpeg"}


def test_metrics_sync_endpoint_with_signals():
    body = TestClient(app).post("/v1/metrics/sync", json={"signals": [
        {"candidate_id": "c1", "platform": "instagram", "metric": "saves", "value": 120,
         "themes": ["explainer"]}
    ]}).json()
    assert body["ingested"] == 1
