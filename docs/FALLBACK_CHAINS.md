# Fallback chains (voice + posting)

> The platform never hard-fails on a missing provider.

Voice generation and posting each walk a chain of providers, ending in a terminal
link that is **always available** — so a draft can always be voiced (as plain
text if nothing else) and always be handed off (as a CSV export if nothing else),
even fully offline.

- Module: [`services/fallback.py`](../core/invisable_os/services/fallback.py)
- API: `GET /v1/fallback/status`
- The canonical chains live with the [Failsafe + Backup](FAILSAFE_BACKUP.md) module
  so backup/status and selection always agree.

## The chains

| Chain | Order (preferred → terminal) |
| ----- | ---------------------------- |
| **voice** | ElevenLabs → OpenVoice → F5-TTS → Piper → **text** |
| **posting** | Metricool → Postiz → TryPost → **CSV** |

## How selection works

A provider counts as available when its API key / URL is present in the
environment:

| Provider | Env var(s) |
| -------- | ---------- |
| ElevenLabs | `ELEVENLABS_API_KEY` |
| OpenVoice | `OPENVOICE_URL` |
| F5-TTS | `F5_TTS_URL` |
| Piper | `PIPER_BIN` / `PIPER_PATH` |
| Metricool | `METRICOOL_API_KEY` |
| Postiz | `POSTIZ_API_KEY` / `POSTIZ_API_URL` |
| TryPost | `TRYPOST_API_KEY` |

Selection walks the chain and picks the **first available** link. The terminal
link (text / CSV) is always available, so selection can never fail.

```
GET /v1/fallback/status
  →
  { voice:   { chain, available, selected, degraded, terminal_fallback },
    posting: { chain, available, selected, degraded, terminal_fallback },
    all_degraded, ok }
```

- `degraded` — the preferred provider wasn't available, so a lower link was chosen.
- `terminal_fallback` — degraded all the way to text / CSV.
- `all_degraded` — both chains are on their terminal link (fully offline operation).

`select_voice(available)` / `select_posting(available)` accept an explicit
availability set (used in tests); with no argument they detect from the
environment. Deterministic and offline.
