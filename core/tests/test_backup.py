"""Tests for Failsafe + Backup.

The safety net must be honest: an export captures the critical tables, a restore
re-creates only what is missing (never a duplicate), and tampering is caught by
the checksum. Everything is deterministic and offline.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from invisable_os.main import app
from invisable_os.services.backup import (
    POSTING_FALLBACK_CHAIN,
    VOICE_FALLBACK_CHAIN,
    export_snapshot,
    failsafe_status,
    restore_snapshot,
    verify_snapshot,
)
from invisable_os.store import get_repository

client = TestClient(app)


def _seed(repo) -> None:
    repo.enqueue({"id": "q1", "candidate": {"hook": "On site at 6am"}, "status": "approved"})
    repo.add_war_chest_item(
        {"id": "w1", "title": "Evergreen pacing tip", "category": "evergreen",
         "reserve_status": "ready"}
    )
    repo.add_source({"id": "s1", "name": "ONS", "source_type": "gov"})
    repo.add_source_claim({"id": "c1", "source_id": "s1", "title": "Theft up 20%"})
    repo.add_scanner_source({"id": "sc1", "name": "Trade RSS", "type": "rss"})


# --- export -----------------------------------------------------------------


def test_export_captures_every_section_with_a_checksum():
    repo = get_repository()
    _seed(repo)
    snap = export_snapshot(repo)
    assert snap["kind"] == "invisable-os-backup"
    assert snap["counts"] == {
        "queue": 1,
        "war_chest": 1,
        "sources": 1,
        "source_claims": 1,
        "scanner_sources": 1,
    }
    assert snap["total"] == 5
    assert snap["checksum"]


def test_empty_platform_exports_an_empty_but_valid_snapshot():
    snap = export_snapshot(get_repository())
    assert snap["total"] == 0
    assert verify_snapshot(snap)["ok"] is True


# --- verify -----------------------------------------------------------------


def test_verify_accepts_a_freshly_exported_snapshot():
    repo = get_repository()
    _seed(repo)
    v = verify_snapshot(export_snapshot(repo))
    assert v["ok"] is True
    assert v["checksum_ok"] is True


def test_verify_catches_a_tampered_snapshot():
    repo = get_repository()
    _seed(repo)
    snap = export_snapshot(repo)
    snap["sections"]["sources"][0]["name"] = "Tampered"
    v = verify_snapshot(snap)
    assert v["ok"] is False
    assert v["checksum_ok"] is False


# --- restore ----------------------------------------------------------------


def test_restore_is_idempotent_against_its_own_data():
    repo = get_repository()
    _seed(repo)
    snap = export_snapshot(repo)
    result = restore_snapshot(snap, repository=repo)
    # Everything is already present, so nothing is re-added.
    assert result["total_restored"] == 0
    assert result["skipped"]["sources"] == 1
    # And the platform still holds exactly one of each.
    assert len(repo.list_sources()) == 1


def test_restore_recreates_missing_rows():
    repo = get_repository()
    _seed(repo)  # ids q1/w1/s1/c1/sc1 exist
    snap = export_snapshot(repo)
    # A snapshot describing rows the platform does NOT yet hold.
    snap["sections"]["sources"].append({"id": "s2", "name": "NHS", "source_type": "gov"})
    snap["sections"]["queue"].append({"id": "q2", "candidate": {"hook": "new"}})
    result = restore_snapshot(snap, repository=repo)
    assert result["restored"]["sources"] == 1
    assert result["restored"]["queue"] == 1
    assert {s["id"] for s in repo.list_sources()} == {"s1", "s2"}


def test_restore_can_target_specific_sections():
    repo = get_repository()
    _seed(repo)
    snap = export_snapshot(repo)
    snap["sections"]["sources"].append({"id": "s2", "name": "NHS"})
    snap["sections"]["queue"].append({"id": "q2", "candidate": {}})
    result = restore_snapshot(snap, repository=repo, sections=["sources"])
    assert result["restored"]["sources"] == 1
    assert "queue" not in result["restored"]
    assert {s["id"] for s in repo.list_sources()} == {"s1", "s2"}


# --- failsafe status --------------------------------------------------------


def test_failsafe_status_reports_recoverable_and_fallback_chains():
    repo = get_repository()
    _seed(repo)
    status = failsafe_status(repo)
    assert status["ok"] is True
    assert status["backup_ready"] is True
    assert status["total_recoverable"] == 5
    assert status["ready_reserve"] == 1
    assert status["fallback_chains"]["voice"] == VOICE_FALLBACK_CHAIN
    assert status["fallback_chains"]["posting"] == POSTING_FALLBACK_CHAIN


def test_failsafe_status_warns_when_nothing_to_fall_back_on():
    status = failsafe_status(get_repository())
    assert status["ok"] is False
    assert status["backup_ready"] is False
    assert any("ready War Chest" in w for w in status["warnings"])


# --- HTTP surface -----------------------------------------------------------


def test_backup_round_trips_over_http():
    repo = get_repository()
    _seed(repo)
    snap = client.get("/v1/backup/export").json()
    assert snap["total"] == 5

    # Add an unseen row and restore it through the API.
    snap["sections"]["sources"].append({"id": "s9", "name": "Acas"})
    result = client.post("/v1/backup/restore", json={"snapshot": snap}).json()
    assert result["restored"]["sources"] == 1
    assert {s["id"] for s in repo.list_sources()} == {"s1", "s9"}

    status = client.get("/v1/failsafe/status").json()
    assert status["backup_ready"] is True
