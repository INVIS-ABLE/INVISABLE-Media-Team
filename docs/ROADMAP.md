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
- ✅ **Agent Library** (`agents/`) — 38 specialist agents + router; guardrails
  baked into every prompt. Tested.
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

## Next (clearly scoped extensions)

- ⏳ **Live generation at volume** — richer Claude/Ollama prompts + structured JSON
  output parsing + an LLM-judge scoring pass on top of the deterministic floor.
- ⏳ **Media pipeline** — ComfyUI/Flux image gen, ElevenLabs voice, Whisper
  captions, OpenCut assembly, ResourceSpace asset library, wired to the flywheel.
- ⏳ **Platform metrics ingestion** — real connectors (Metricool) feeding the Watchtower.
- ⏳ **PWA front-end** — build the dashboard in [`PWA_DASHBOARD.md`](PWA_DASHBOARD.md)
  against the now-operational API.
- ⏳ **Founder Recognition dashboard** — surface the index and presence view over time.

## Guiding principle for every extension

If a new feature increases reach but damages trust, it does not ship. Add a
guardrail test before adding the capability.
