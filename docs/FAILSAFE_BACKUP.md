# Failsafe + Backup

> A safety net the founder can hold in one hand.

If the database is lost, a deploy goes wrong, or you simply want an off-box copy,
this exports the platform's hard-to-recreate state into **one portable JSON
snapshot** and restores it **idempotently** — it never duplicates a row it
already holds.

- Module: [`services/backup.py`](../core/invisable_os/services/backup.py)
- API: `GET /v1/backup/export` · `POST /v1/backup/restore` · `GET /v1/failsafe/status`
- CLI: `invisable backup <file>` · `invisable restore <file>`

## What's in a snapshot

Exactly the dict-shaped tables the platform already writes, each of which keeps
its own `id` so a restore round-trips cleanly:

| Section | Source |
| ------- | ------ |
| `queue` | the approval lifecycle (`queue_item`) |
| `war_chest` | the Content War Chest reserve |
| `sources` | credible sources |
| `source_claims` | the claims behind the Credible Source Rule |
| `scanner_sources` | source-led scan feeds |

A snapshot carries a `version`, a `created_at`, per-section `counts`, and a
`checksum` (SHA-256 over the canonical section payloads) for integrity.

```
GET /v1/backup/export → { kind, version, created_at, counts, total, checksum, sections }
```

## Restore is idempotent

Restore only adds rows whose `id` is **absent**; anything already present is
skipped. So it is safe to run twice, or to merge a snapshot into a live system.

```
POST /v1/backup/restore  { "snapshot": {...}, "sections": ["sources"] }  (sections optional)
  → { ok, checksum_ok, restored:{...}, skipped:{...}, total_restored }
```

A checksum mismatch is reported (`checksum_ok: false`) but does **not** block the
restore — recovery from a slightly-edited snapshot is still better than no
recovery. The verdict tells you exactly what looked off.

## Failsafe status

`GET /v1/failsafe/status` answers two questions at a glance — *what can I recover
right now?* and *what stands ready when a provider is down?*

```json
{
  "ok": true,
  "backup_ready": true,
  "recoverable": { "queue": 42, "war_chest": 18, ... },
  "ready_reserve": 18,
  "fallback_chains": {
    "voice":   ["ElevenLabs", "OpenVoice", "F5-TTS", "Piper", "text"],
    "posting": ["Metricool", "Postiz", "TryPost", "CSV"]
  },
  "warnings": []
}
```

It warns when there is nothing to back up yet, or when the **ready War Chest
reserve is empty** — the cushion that keeps posting alive if generation stalls.

Everything here is deterministic and offline: no provider is ever called to take
a backup or report status.
