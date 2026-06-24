"""Failsafe + Backup — a portable safety net for the platform's critical state.

If a database is lost, a deploy goes wrong, or the founder simply wants an
off-box copy, this exports the hard-to-recreate domain data into one
JSON-serialisable snapshot and restores it idempotently. It is deliberately
narrow: it round-trips exactly the dict-shaped tables the platform already
writes (queue, War Chest reserve, credible sources + claims, scanner sources),
each of which preserves its own ``id`` — so a restore never duplicates a row it
already holds.

It also reports a ``failsafe_status``: what is recoverable right now, and which
fallback chains are standing by when a preferred provider is unavailable. The
whole thing is deterministic and offline; no provider is ever called here.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime

from invisable_os.store import get_repository

SNAPSHOT_VERSION = 1
SNAPSHOT_KIND = "invisable-os-backup"

# Generous ceiling so a snapshot captures the whole table, not just a page.
_EXPORT_LIMIT = 100_000

# The fallback chains the platform degrades through when a preferred provider is
# down. Surfaced by ``failsafe_status`` so an operator can see the safety net at
# a glance; the actual selection lives in the voice/posting services.
VOICE_FALLBACK_CHAIN = ["ElevenLabs", "OpenVoice", "F5-TTS", "Piper", "text"]
POSTING_FALLBACK_CHAIN = ["Metricool", "Postiz", "TryPost", "CSV"]

# Each section maps to the repository's list/add pair. Every one of these
# add_* methods preserves an incoming ``id`` and round-trips with its list_*
# via ``as_dict()`` — that symmetry is what makes restore idempotent.
_SECTIONS: tuple[str, ...] = (
    "queue",
    "war_chest",
    "sources",
    "source_claims",
    "scanner_sources",
)


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _read_section(repo, name: str) -> list[dict]:
    if name == "queue":
        return repo.list_queue(limit=_EXPORT_LIMIT)
    if name == "war_chest":
        return repo.list_war_chest(limit=_EXPORT_LIMIT)
    if name == "sources":
        return repo.list_sources()
    if name == "source_claims":
        return repo.list_source_claims(limit=_EXPORT_LIMIT)
    if name == "scanner_sources":
        return repo.list_scanner_sources()
    return []


def _existing_ids(repo, name: str) -> set[str]:
    return {row.get("id") for row in _read_section(repo, name) if row.get("id")}


def _write_row(repo, name: str, row: dict) -> None:
    if name == "queue":
        repo.enqueue(row)
    elif name == "war_chest":
        repo.add_war_chest_item(row)
    elif name == "sources":
        repo.add_source(row)
    elif name == "source_claims":
        repo.add_source_claim(row)
    elif name == "scanner_sources":
        repo.add_scanner_source(row)


def _checksum(sections: dict[str, list[dict]]) -> str:
    """A stable digest over the section payloads, order-independent per row.

    ``default=str`` keeps datetimes/uuids serialisable; ``sort_keys`` makes the
    digest independent of dict ordering so the same data always hashes the same.
    """
    canonical = json.dumps(sections, sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def export_snapshot(repository=None) -> dict:
    """Capture the critical, dict-shaped tables into one portable snapshot."""
    repo = repository or get_repository()
    sections = {name: _read_section(repo, name) for name in _SECTIONS}
    counts = {name: len(rows) for name, rows in sections.items()}
    return {
        "kind": SNAPSHOT_KIND,
        "version": SNAPSHOT_VERSION,
        "created_at": _now_iso(),
        "counts": counts,
        "total": sum(counts.values()),
        "checksum": _checksum(sections),
        "sections": sections,
    }


def verify_snapshot(snapshot: dict) -> dict:
    """Check a snapshot is well-formed and its checksum matches its sections."""
    problems: list[str] = []
    if snapshot.get("kind") != SNAPSHOT_KIND:
        problems.append(f"unexpected kind: {snapshot.get('kind')!r}")
    if snapshot.get("version") != SNAPSHOT_VERSION:
        problems.append(f"unsupported version: {snapshot.get('version')!r}")
    sections = snapshot.get("sections")
    checksum_ok = False
    if isinstance(sections, dict):
        checksum_ok = _checksum(sections) == snapshot.get("checksum")
        if not checksum_ok:
            problems.append("checksum mismatch — snapshot may be corrupted")
    else:
        problems.append("missing or malformed sections")
    return {"ok": not problems, "checksum_ok": checksum_ok, "problems": problems}


def restore_snapshot(snapshot: dict, repository=None, sections=None) -> dict:
    """Idempotently restore a snapshot — only rows whose id is absent are added.

    Returns a per-section tally of ``restored`` vs ``skipped`` (already present),
    plus the verification verdict. A row missing an ``id`` is treated as new.
    """
    repo = repository or get_repository()
    verdict = verify_snapshot(snapshot)
    snap_sections = snapshot.get("sections") or {}
    wanted = set(sections) if sections else set(_SECTIONS)

    restored: dict[str, int] = {}
    skipped: dict[str, int] = {}
    for name in _SECTIONS:
        if name not in wanted:
            continue
        rows = snap_sections.get(name) or []
        present = _existing_ids(repo, name)
        added = skip = 0
        for row in rows:
            row_id = row.get("id")
            if row_id and row_id in present:
                skip += 1
                continue
            _write_row(repo, name, row)
            if row_id:
                present.add(row_id)
            added += 1
        restored[name] = added
        skipped[name] = skip

    return {
        "ok": verdict["ok"],
        "checksum_ok": verdict["checksum_ok"],
        "problems": verdict["problems"],
        "restored": restored,
        "skipped": skipped,
        "total_restored": sum(restored.values()),
    }


def failsafe_status(repository=None) -> dict:
    """What is recoverable right now, and which fallback chains stand ready."""
    repo = repository or get_repository()
    counts = {name: len(_read_section(repo, name)) for name in _SECTIONS}
    total = sum(counts.values())

    # Ready reserve is the platform's true cushion if generation stalls.
    ready_reserve = len(repo.list_war_chest(reserve_status="ready", limit=_EXPORT_LIMIT))

    warnings: list[str] = []
    if total == 0:
        warnings.append("nothing to back up yet — no durable content state")
    if ready_reserve == 0:
        warnings.append("no ready War Chest reserve — nothing to fall back on if generation stalls")

    return {
        "ok": not warnings,
        "backup_ready": total > 0,
        "recoverable": counts,
        "total_recoverable": total,
        "ready_reserve": ready_reserve,
        "fallback_chains": {
            "voice": VOICE_FALLBACK_CHAIN,
            "posting": POSTING_FALLBACK_CHAIN,
        },
        "warnings": warnings,
    }
