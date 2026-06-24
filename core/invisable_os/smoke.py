"""End-to-end smoke test — walk a real day through the live API.

Drives the full pipeline in order:

    health → integrations → harvest → daily plan (persist) → seed channels →
    approve → produce media → assemble video → publish → DAM sync →
    metrics sync → watchtower ingest → founder recognition

Every external adapter (Postiz, Metricool, ResourceSpace, ComfyUI, ElevenLabs,
FFmpeg) degrades to dry-run when its credentials/binaries are absent, so this is
safe to run anywhere: with no keys it exercises the whole flow in dry-run; with
keys set it exercises the **live** adapters and the report shows which ran live.

Run it:

    python -m invisable_os.smoke                 # in-process app, temp SQLite
    SMOKE_BASE_URL=http://localhost:8080 python -m invisable_os.smoke   # live server

See ``docs/SMOKE_TEST.md`` for the credentialed runbook.
"""

from __future__ import annotations

import os
import sys


def _make_client():
    """A client speaking to a live server (SMOKE_BASE_URL) or the in-process app."""
    base = os.getenv("SMOKE_BASE_URL")
    if base:
        import httpx

        return httpx.Client(base_url=base, timeout=120.0), f"live server {base}"
    os.environ.setdefault(
        "INVISABLE_SQLITE_PATH",
        os.path.join(os.getenv("TMPDIR", "/tmp"), "invisable-smoke.db"),
    )
    from fastapi.testclient import TestClient

    from invisable_os.main import app

    return TestClient(app), "in-process app"


def run_smoke(client, *, candidates_per_slot: int = 6) -> dict:
    """Walk the full day; return a structured report. Never raises — captures errors."""
    report: dict = {"steps": [], "ok": True, "integrations": {}}
    state: dict = {}

    def get(path: str):
        r = client.get(path)
        r.raise_for_status()
        return r.json()

    def post(path: str, body: dict | None = None):
        r = client.post(path, json=body or {})
        r.raise_for_status()
        return r.json()

    def step(name: str, fn) -> None:
        try:
            report["steps"].append({"name": name, "ok": True, "detail": fn()})
        except Exception as exc:  # noqa: BLE001 — a smoke test reports failures, never crashes
            report["steps"].append({"name": name, "ok": False, "detail": repr(exc)})
            report["ok"] = False

    def _integrations() -> str:
        report["integrations"] = get("/v1/integrations")
        live = [k for k, v in report["integrations"].items() if v]
        return "live: " + (", ".join(sorted(live)) if live else "none (all dry-run)")

    def _plan() -> str:
        d = post("/v1/daily/plan", {"persist": True, "candidates_per_slot": candidates_per_slot})
        state["queued"] = d.get("queued_ids", [])
        return f"{d['total']} posts · {d['total_assets']} assets · {len(state['queued'])} queued"

    def _seed() -> str:
        a = post("/v1/channels", {"name": "INVISABLE Instagram", "platform": "instagram"})
        b = post("/v1/channels", {"name": "INVISABLE TikTok", "platform": "tiktok"})
        return f"{a.get('slots_created', 0) + b.get('slots_created', 0)} posting slots"

    def _approve() -> str:
        ids = [i["id"] for i in get("/v1/queue")["items"][:3]]
        for i in ids:
            post(f"/v1/queue/{i}/approve")
        state["approved"] = ids
        return f"approved {len(ids)}"

    def _produce() -> str:
        if not state.get("approved"):
            return "no approved items"
        d = post(f"/v1/media/produce/{state['approved'][0]}")
        state["produced_item"] = state["approved"][0]
        backs: dict[str, int] = {}
        for a in d.get("assets", []) if isinstance(d, dict) else []:
            backs[a.get("backend", "?")] = backs.get(a.get("backend", "?"), 0) + 1
        return f"produced {d.get('produced', '?')} · backends={backs or 'n/a'}"

    def _assemble() -> str:
        if not state.get("produced_item"):
            return "skip"
        d = post(f"/v1/media/assemble/{state['produced_item']}")
        return f"backend={d.get('backend', '?')} · {d.get('status', d.get('error', 'ok'))}"

    def _publish() -> str:
        d = post("/v1/publish/run")
        state["published"] = [p["id"] for p in d.get("published", [])]
        count = d.get("count", len(state["published"]))
        return f"backend={d.get('backend', '?')} · published={count}"

    def _dam() -> str:
        pid = (state.get("published") or state.get("approved") or [None])[0]
        if not pid:
            return "skip"
        d = post(f"/v1/dam/sync/{pid}")
        return f"backend={d.get('backend', '?')} · synced={len(d.get('synced', []))}"

    def _ingest() -> str:
        signals = [
            {"candidate_id": "c1", "platform": "instagram", "metric": "media_mentions", "value": 4},
            {"candidate_id": "c2", "platform": "tiktok", "metric": "saves", "value": 80,
             "themes": ["invisible illness"]},
        ]
        out = post("/v1/watchtower/ingest", {"signals": signals})
        return f"FRI={out['founder_recognition_index']}"

    def _recognition() -> str:
        d = get("/v1/founder/recognition")
        return f"latest={d['latest']} · points={d['points']}"

    step("health", lambda: f"claude={get('/health')['claude_configured']}")
    step("integrations", _integrations)
    def _harvest() -> str:
        return f"{post('/v1/harvest', {'topics': ['invisible illness']})['count']} signals"

    step("harvest", _harvest)
    step("daily plan (persist)", _plan)
    step("seed channels", _seed)
    step("approve", _approve)
    step("produce media", _produce)
    step("assemble video", _assemble)
    step("publish (run)", _publish)
    step("dam sync", _dam)
    step("metrics sync", lambda: f"source={post('/v1/metrics/sync')['source']}")
    step("watchtower ingest", _ingest)
    step("founder recognition", _recognition)
    return report


def _print(report: dict, target: str) -> None:
    print(f"\nINVISABLE OS — end-to-end smoke ({target})\n" + "=" * 52)
    for s in report["steps"]:
        mark = "✓" if s["ok"] else "✗"
        print(f" {mark} {s['name']:<22} {s['detail']}")
    integ = report.get("integrations", {})
    live = [k for k, v in integ.items() if v]
    print("-" * 52)
    print(f" adapters live: {', '.join(sorted(live)) if live else 'none (all dry-run)'}")
    print(f" RESULT: {'PASS' if report['ok'] else 'FAIL'}\n")


def main() -> int:
    client, target = _make_client()
    report = run_smoke(client)
    _print(report, target)
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
