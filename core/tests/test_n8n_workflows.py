"""Validate the n8n workflow JSONs against the live API.

These are the orchestration spine: every workflow calls the core API. This test is
the guardrail that keeps the JSON honest — it fails if a workflow is malformed, if a
node bypasses ``$env.INVISABLE_CORE_URL``, if a connection points at a missing node,
or (most importantly) if a workflow calls a ``/v1`` endpoint + method the API does
not actually expose. So API drift can't silently break the automation.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from invisable_os.main import create_app

WORKFLOW_DIR = Path(__file__).resolve().parents[2] / "n8n" / "workflows"
EXPECTED = {
    "daily_content_cycle.json",
    "scanner_sweep.json",
    "comment_to_content.json",
    "nightly_learning.json",
    "campaign_factory.json",
    "media_production.json",
    "relationship_followups.json",
}


_HTTP_METHODS = {"get", "put", "post", "delete", "patch", "options", "head", "trace"}


def _api_routes() -> list[tuple[set[str], re.Pattern]]:
    """(methods, compiled-regex) for every /v1 route the app exposes.

    Read from the OpenAPI schema — the canonical, version-proof list of exposed
    paths + methods — rather than walking FastAPI's internal route objects (which
    nest included routers behind private classes).
    """
    routes: list[tuple[set[str], re.Pattern]] = []
    schema = create_app().openapi()
    for path, ops in schema.get("paths", {}).items():
        if not path.startswith("/v1"):
            continue
        methods = {m.upper() for m in ops if m.lower() in _HTTP_METHODS}
        pattern = re.sub(r"\{[^/}]+\}", r"[^/]+", path)
        routes.append((methods, re.compile(f"^{pattern}$")))
    return routes


API_ROUTES = _api_routes()
WORKFLOW_FILES = sorted(WORKFLOW_DIR.glob("*.json"))


def _http_nodes(wf: dict) -> list[dict]:
    return [n for n in wf["nodes"] if n["type"] == "n8n-nodes-base.httpRequest"]


def _path_of(url: str) -> tuple[str, str]:
    """Return (raw_url_without_leading_=, path-with-expressions-substituted)."""
    raw = url[1:] if url.startswith("=") else url
    after = raw.split("/v1", 1)[1]
    path = "/v1" + after.split("?", 1)[0]  # drop query string
    path = re.sub(r"\{\{.*?\}\}", "X", path)  # n8n expressions → a path token
    return raw, path.rstrip("/") or path


def test_all_expected_workflows_present():
    names = {p.name for p in WORKFLOW_FILES}
    assert EXPECTED <= names, f"missing workflows: {EXPECTED - names}"


@pytest.mark.parametrize("path", WORKFLOW_FILES, ids=lambda p: p.name)
def test_workflow_is_well_formed(path):
    wf = json.loads(path.read_text())
    assert wf.get("name"), "workflow needs a name"
    assert wf.get("nodes"), "workflow needs nodes"
    node_names = {n["name"] for n in wf["nodes"]}
    # Every connection source and target must be a real node.
    for src, conn in wf.get("connections", {}).items():
        assert src in node_names, f"connection from unknown node {src!r}"
        for group in conn.get("main", []):
            for link in group:
                assert link["node"] in node_names, f"connection to unknown node {link['node']!r}"


@pytest.mark.parametrize("path", WORKFLOW_FILES, ids=lambda p: p.name)
def test_http_nodes_use_core_env_and_real_endpoints(path):
    wf = json.loads(path.read_text())
    for node in _http_nodes(wf):
        url = node["parameters"]["url"]
        assert "$env.INVISABLE_CORE_URL" in url, f"{node['name']} bypasses the core URL env"

        raw, wf_path = _path_of(url)
        method = node["parameters"].get("method", "GET").upper()
        matched = any(
            method in methods and rx.match(wf_path) for methods, rx in API_ROUTES
        )
        assert matched, f"{node['name']}: {method} {wf_path} is not an exposed /v1 endpoint"
