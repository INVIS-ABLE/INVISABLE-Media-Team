"""Optional API-key auth on the /v1 surface.

Open by default; gated when ``INVISABLE_API_KEY`` is set. Health, root and the PWA
shell stay open either way so probes and the dashboard keep working.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from invisable_os.main import app

client = TestClient(app)


def test_api_open_when_no_key(monkeypatch):
    monkeypatch.delenv("INVISABLE_API_KEY", raising=False)
    assert client.get("/v1/values").status_code == 200


def test_v1_requires_key_when_set(monkeypatch):
    monkeypatch.setenv("INVISABLE_API_KEY", "s3cret")
    assert client.get("/v1/values").status_code == 401  # no header
    assert client.get("/v1/values", headers={"X-API-Key": "wrong"}).status_code == 401
    assert client.get("/v1/values", headers={"X-API-Key": "s3cret"}).status_code == 200


def test_bearer_token_accepted(monkeypatch):
    monkeypatch.setenv("INVISABLE_API_KEY", "s3cret")
    assert client.get(
        "/v1/values", headers={"Authorization": "Bearer s3cret"}
    ).status_code == 200


def test_open_endpoints_stay_open_with_key(monkeypatch):
    monkeypatch.setenv("INVISABLE_API_KEY", "s3cret")
    # Liveness + the installable PWA shell must never require the key.
    assert client.get("/health").status_code == 200
    assert client.get("/").status_code == 200
    assert client.get("/app/").status_code == 200


def test_post_endpoint_also_gated(monkeypatch):
    monkeypatch.setenv("INVISABLE_API_KEY", "s3cret")
    body = {"text": "hello", "original": True}
    assert client.post("/v1/guardrails/check", json=body).status_code == 401
    assert client.post(
        "/v1/guardrails/check", json=body, headers={"X-API-Key": "s3cret"}
    ).status_code == 200
