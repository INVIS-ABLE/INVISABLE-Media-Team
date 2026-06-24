# Roadmap — what's wired vs. what's next

This repository is the **foundation** of the operating system: a coherent, runnable,
tested core with the architecture, shared memory, engines, and values in place. The
honest state of each piece:

## Wired and tested (works today, offline)

- ✅ **Guardrails** — deterministic hard gate enforcing the Prime Directive, the
  never-optimise-for / never-do lists, emoji & engagement-bait policy. Fully tested.
- ✅ **Content Tournament Engine** — generate → gate → score → improve → rank →
  dedup → select → founder-rebalance → remember. Fully tested.
- ✅ **Scorer** — eight value dimensions with trust/community-weighted composite,
  learning nudges from the Brain. Tested.
- ✅ **Founder Engine** — proportional ~80% presence balancing. Tested.
- ✅ **Cultural Intelligence Engine** — British resonance scoring, Americanism
  flagging. Tested.
- ✅ **Algorithm Watchtower** — signal ingestion, theme learning, Founder
  Recognition Index. Tested.
- ✅ **Intelligence Harvester** — abstracted-signal model + Brain persistence. Tested.
- ✅ **Community Engagement** — compliant comment drafting. Tested.
- ✅ **INVISABLE_BRAIN** — Chroma-backed semantic memory with in-process fallback.
- ✅ **LLM layer** — Claude → Ollama → stub, degrading gracefully.
- ✅ **FastAPI surface**, **Postgres schema**, **Docker Compose** stack, **n8n**
  daily-cycle workflow, **CI**.

### Departments build (added)

- ✅ **Humour & Personality Engine** — content personality mix + style rotation;
  refined brand-safety that allows self-deprecating/British/situational humour and
  natural swearing, but blocks slurs, harassment, and punching down. Tested.
- ✅ **Mission Advisor** (`mission.py`) — five mission impacts + advance/hold/reject
  verdict, long-term weighted highest. Tested.
- ✅ **Quality Control** (`quality.py`) — 11-dimension /10 rubric with the
  below-8-must-improve gate. Tested.
- ✅ **Content Flywheel** (`flywheel.py`) — one idea → 7+ assets. Tested.
- ✅ **Daily Output System** (`daily.py`) — the 20-post day (~140 assets), each
  gated/scored/spun. Tested.
- ✅ **Fixed Tag Network** (`tagging.py`) — approved-only, paused/do-not-tag,
  per-platform, max-tags. Tested.
- ✅ **Risk Scanner** — advisory flags (medical/legal/benefits/sponsor/copyright)
  for human review. Tested.
- ✅ **Agent Library** (`agents/`) — 77 specialist agents across seven
  production-pipeline teams + router; guardrails baked into every prompt. Tested.
- ✅ **Visual Layout Agent + Video Quality Gate** (`media/safe_area.py`,
  `media/video_qc.py`) — deterministic safe-area geometry (captions off faces/UI) and
  the full pre-approval video checklist. Tested. See `docs/PRODUCTION_STUDIO.md`.
- ✅ Department **DB schema** (tag network, people/consent, partners, CRM,
  competitors, opportunities, media contacts, community stories, knowledge, hooks,
  mission/risk).
- ✅ Docs: departments, god-tier architecture, n8n workflow map, PWA layout, daily
  pipeline, agent library, install order.

### Operational build (added)

- ✅ **Persistence layer** (`store/`) — SQLAlchemy ORM + repository; SQLite by
  default (zero services), Postgres via `DATABASE_URL`. App self-migrates on boot. Tested.
- ✅ **Content lifecycle / approval queue** — durable queue items with status
  (`pending_review` → `approved` → `scheduled` → `published`, plus
  `needs_improvement` / `rejected`). API + CLI. Tested.
- ✅ **Pipeline service** — `run_and_queue_daily` persists the day's 20 posts (with
  scores, tags, flywheel assets) into the queue. Tested.
- ✅ **Publishing layer** (`publish/`) — `Publisher` protocol, safe **dry-run**
  default, Postiz adapter; scheduler publishes approved items + seeds a perf signal. Tested.
- ✅ **Harvester connectors** (`connectors.py`) — Feedly / Google Trends / Firecrawl
  adapters with graceful fallback; opportunity scanning persisted. Tested.
- ✅ **Management CLI** (`invisable`) — migrate / serve / demo / plan / queue /
  approve / publish / seed-tags.
- ✅ **Operational API** — `/v1/daily/plan?persist`, `/v1/queue`, queue actions,
  `/v1/publish/run`, `/v1/tags`, `/v1/partners`, `/v1/opportunities`.
- ✅ **Docker** — core self-bootstraps the DB and serves via the CLI; Postgres driver
  included. Runbook in [`OPERATIONS.md`](OPERATIONS.md).

### Scheduling & media build (added)

- ✅ **Posting-slot queue** (`scheduling/`) — weekly slots per channel, "fill the
  next free slot" with timezone-aware slot computation and no double-booking. Tested.
- ✅ **Channels & default schedule** — connected accounts + Mon–Fri × 3-slot default
  at off-the-hour times. CLI `seed-channels` / `schedule`. Tested.
- ✅ **Calendar** — scheduled posts grouped by day (`GET /v1/calendar`, CLI). Tested.
- ✅ **Media pipeline** (`media/`) — ComfyUI/Flux, ElevenLabs, Whisper, passthrough
  renderers with dry-run fallback; `MediaProducer` renders the flywheel into the
  media library. Tested.
- ✅ **Per-slot angle generation** — each daily slot generates in its editorial
  angle, so the day spans distinct content (not 20 clones).
- ✅ **Reference audit** — licences verified; patterns borrowed clean-room. See
  [`REFERENCES.md`](REFERENCES.md), [`SCHEDULING.md`](SCHEDULING.md).

### Generation build (added)

- ✅ **Structured generation** — `LLMClient.complete_json` (Claude JSON / Ollama
  `format:json`) + tolerant `extract_json`; the generator requests `{hook, body,
  call_to_action}` and falls back to safe templates offline. Tested.
- ✅ **LLM-judge** (`engines/judge.py`) — re-scores only the top contenders and
  blends 50/50 with the deterministic floor; **self-disables offline** so tests stay
  fast and behaviour is unchanged without a model. Wired into the tournament. Tested.
- ✅ Docs: [`GENERATION.md`](GENERATION.md).

## Next (clearly scoped extensions)
- ✅ **Real media rendering** — ComfyUI (submit → poll → download), ElevenLabs TTS,
  and a real SRT caption writer behind the renderers, with per-asset dry-run
  fallback. Live when a backend is configured. Tested with mocked transports. See
  [`MEDIA.md`](MEDIA.md).
- ✅ **Video assembly** — FFmpeg executor (`media/assembly.py`) stitches a post's
  rendered visual + voiceover + burned-in captions into a finished `.mp4`; pure
  command-builder + injectable runner, per-asset dry-run fallback. `invisable
  assemble`, `POST /v1/media/assemble/{id}`. Tested. See [`MEDIA.md`](MEDIA.md).
- ⏳ **ResourceSpace asset-library sync** + Metricool metrics into the Watchtower.
- ⏳ **Platform metrics ingestion** — real connectors (Metricool) feeding the Watchtower.
- ✅ **PWA front-end** — installable dashboard (`core/invisable_os/web/`) served at
  `/app`: Today / Queue / Calendar / Media / Agents / Values, wired to the API.
  Tested. (Richer screens in [`PWA_DASHBOARD.md`](PWA_DASHBOARD.md) are next.)
- ⏳ **Founder Recognition dashboard** — surface the index and presence view over time.

## Guiding principle for every extension

If a new feature increases reach but damages trust, it does not ship. Add a
guardrail test before adding the capability.
