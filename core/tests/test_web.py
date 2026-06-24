"""The PWA dashboard is served and wired to the API."""

import json

from fastapi.testclient import TestClient

from invisable_os.main import app

client = TestClient(app)


def test_dashboard_index_served():
    r = client.get("/app/")
    assert r.status_code == 200
    assert "INVISABLE" in r.text
    assert "app.js" in r.text


def test_static_assets_served():
    for path, needle in (
        ("/app/app.js", "INVISABLE OS dashboard"),
        ("/app/styles.css", "--accent"),
        ("/app/sw.js", "caches"),
        ("/app/icon.svg", "<svg"),
    ):
        r = client.get(path)
        assert r.status_code == 200, path
        assert needle in r.text, path


def test_manifest_is_valid_json_and_installable():
    r = client.get("/app/manifest.webmanifest")
    assert r.status_code == 200
    data = json.loads(r.text)
    assert data["name"].startswith("INVISABLE")
    assert data["display"] == "standalone"
    assert data["icons"], "a PWA needs at least one icon"


def test_root_advertises_dashboard():
    assert client.get("/").json()["dashboard"] == "/app/"


def test_dashboard_only_uses_existing_api_endpoints():
    """Guardrail: every /v1 path the dashboard calls must exist on the API."""
    import re

    js = client.get("/app/app.js").text
    called = set(re.findall(r"`?(/v1/[a-z/]+)", js))
    known_prefixes = {
        "/v1/daily/plan", "/v1/queue", "/v1/calendar", "/v1/media", "/v1/agents",
        "/v1/values", "/v1/personality/mix", "/v1/channels", "/v1/brain/stats",
        # Remix department screens (Scanner / Inbox / Remix Studio / Rights Manager /
        # Pop Culture Index / Voiceover Queue / Asset Library)
        "/v1/remix", "/v1/scanner", "/v1/rights",
        "/v1/popculture", "/v1/meme", "/v1/voiceover",
        # Content War Chest screen
        "/v1/warchest",
        # Source Control Centre (credible sources + fact-check)
        "/v1/sources", "/v1/factcheck",
        # Agent Swarm dashboard
        "/v1/swarm",
        # Integrations panel (ResourceSpace DAM + Metricool metrics)
        "/v1/integrations", "/v1/metrics", "/v1/dam",
        # Analytics screen (Founder Recognition Index over time)
        "/v1/founder",
    }
    for path in called:
        assert any(path.startswith(p) for p in known_prefixes), f"dashboard calls unknown {path}"
    # The read-only endpoints the dashboard depends on must actually respond.
    for path in (
        "/v1/calendar", "/v1/agents", "/v1/values", "/v1/brain/stats",
        "/v1/remix/modes", "/v1/scanner/items", "/v1/rights", "/v1/rights-assets",
        "/v1/popculture", "/v1/meme-formats",
        "/v1/warchest", "/v1/warchest/items",
        "/v1/sources", "/v1/sources/hierarchy",
        "/v1/swarm/bots", "/v1/swarm/stats",
        "/v1/integrations",
        "/v1/founder/recognition",
    ):
        assert client.get(path).status_code == 200, path
