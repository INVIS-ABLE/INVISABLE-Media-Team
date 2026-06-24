"""Harvest connectors: pure abstraction + live Firecrawl/Crawl4AI via MockTransport.

These verify the **ethics boundary** (connectors emit abstracted topic-level signals,
never verbatim content) and graceful degradation when unconfigured.
"""

import httpx

from invisable_os.engines.connectors import (
    Crawl4AIConnector,
    FirecrawlConnector,
    abstract_crawl_result,
    abstract_web_results,
    default_connectors,
)
from invisable_os.engines.harvester import IntelligenceHarvester

# --- Pure abstraction -------------------------------------------------------


def test_abstract_web_results_counts_not_content():
    results = [{"markdown": "secret"}, {"markdown": "x"}]
    sig = abstract_web_results("fatigue", results, source_type="web")
    assert sig["topic"] == "fatigue"
    assert sig["kind"] == "discussion"
    assert "2 fresh public results" in sig["summary"]
    # Ethics: the verbatim content must never leak into the signal.
    assert "secret" not in str(sig)


def test_abstract_web_results_empty_is_none():
    assert abstract_web_results("x", [], source_type="web") is None


def test_abstract_crawl_result_abstracts_and_guards_failure():
    ok = abstract_crawl_result("https://s", {"success": True, "results": [1, 2]}, ["trades"])
    assert ok["source_type"] == "crawl" and "2 relevant" in ok["summary"]
    assert abstract_crawl_result("https://s", {"success": False, "results": []}, ["t"]) is None


# --- Firecrawl (live path via MockTransport) --------------------------------


def test_firecrawl_unconfigured_yields_nothing(monkeypatch):
    monkeypatch.delenv("FIRECRAWL_API_KEY", raising=False)
    assert FirecrawlConnector().fetch(["fatigue"]) == []


def test_firecrawl_searches_and_abstracts(monkeypatch):
    monkeypatch.setenv("FIRECRAWL_API_KEY", "k")
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["path"] = request.url.path
        seen["auth"] = request.headers.get("authorization")
        return httpx.Response(200, json={"data": [{"url": "a"}, {"url": "b"}, {"url": "c"}]})

    conn = FirecrawlConnector(transport=httpx.MockTransport(handler))
    signals = conn.fetch(["chronic pain"])
    assert seen["path"] == "/v1/search"
    assert seen["auth"] == "Bearer k"
    assert len(signals) == 1 and signals[0]["topic"] == "chronic pain"


def test_firecrawl_degrades_on_http_error(monkeypatch):
    monkeypatch.setenv("FIRECRAWL_API_KEY", "k")

    def handler(request):
        return httpx.Response(500, json={"error": "boom"})

    conn = FirecrawlConnector(transport=httpx.MockTransport(handler))
    assert conn.fetch(["x"]) == []  # never raises


# --- Crawl4AI ---------------------------------------------------------------


def test_crawl4ai_unconfigured_yields_nothing(monkeypatch):
    monkeypatch.delenv("CRAWL4AI_BASE_URL", raising=False)
    monkeypatch.delenv("CRAWL4AI_SOURCES", raising=False)
    assert Crawl4AIConnector().fetch(["x"]) == []


def test_crawl4ai_crawls_configured_sources(monkeypatch):
    monkeypatch.setenv("CRAWL4AI_BASE_URL", "http://crawl4ai.local")
    monkeypatch.setenv("CRAWL4AI_SOURCES", "https://a.test, https://b.test")
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.path)
        return httpx.Response(200, json={"success": True, "results": [{"x": 1}]})

    conn = Crawl4AIConnector(transport=httpx.MockTransport(handler))
    signals = conn.fetch(["trades safety"])
    assert calls == ["/crawl", "/crawl"]  # one per configured source
    assert len(signals) == 2
    assert all(s["source_type"] == "crawl" for s in signals)


# --- Wiring -----------------------------------------------------------------


def test_default_connectors_include_firecrawl_and_crawl4ai():
    names = {c.name for c in default_connectors()}
    assert {"feedly", "google_trends", "firecrawl", "crawl4ai"} <= names


def test_harvester_runs_with_injected_connector():
    class _Stub:
        name = "stub"

        def fetch(self, topics):
            return [{"topic": topics[0], "kind": "trend", "summary": "s", "source_type": "web"}]

    signals = IntelligenceHarvester(connectors=[_Stub()]).harvest(["fatigue"])
    assert any(s.topic == "fatigue" for s in signals)
