"""The end-to-end smoke walk completes against the in-process app (dry-run).

This keeps `invisable_os.smoke` honest: the full day — harvest → plan → approve →
produce → assemble → publish → DAM → metrics → recognition — must run green with no
credentials, every external adapter degrading to dry-run.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from invisable_os.main import app
from invisable_os.smoke import run_smoke


def test_smoke_walk_passes_in_dry_run():
    report = run_smoke(TestClient(app), candidates_per_slot=6)

    failed = [s for s in report["steps"] if not s["ok"]]
    assert not failed, f"smoke steps failed: {failed}"
    assert report["ok"]

    names = {s["name"] for s in report["steps"]}
    assert {
        "harvest", "daily plan (persist)", "approve", "produce media",
        "publish (run)", "founder recognition",
    } <= names

    # With no credentials every external adapter must be dry-run / off.
    integ = report["integrations"]
    for adapter in ("postiz", "metricool", "resourcespace", "comfyui", "elevenlabs"):
        assert not integ.get(adapter), f"{adapter} should be off without credentials"
