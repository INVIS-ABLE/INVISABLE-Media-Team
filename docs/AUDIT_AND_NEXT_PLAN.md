# INVISABLE® OS — System Audit & Next Implementation Plan

> Audit date: 2026-06-24. Scope: the whole repository, audited against the full
> INVISABLE AI Media Agency OS specification in [`docs/`](.) and
> [`README.md`](../README.md). This document is the single source of truth for
> **what exists, what is placeholder-only, what is missing, and what we build next.**

---

## 1. Executive summary

The repository is a **genuinely strong, fully-tested deterministic foundation**
(3,700 LOC of `core`, 47 passing tests) — but it is a **single stateless Python
service**, not yet the running media organisation the docs describe. The two are
often conflated; this audit separates them honestly.

**What is real and excellent:**
- The values layer (guardrails) is hard-coded, deterministic, and genuinely
  un-talk-around-able. This is the best part of the system.
- The cognitive *shape* of every engine exists and is tested: tournament,
  scoring, mission, quality, flywheel, founder balancing, daily 20-post plan.
- The FastAPI surface exposes all 15 specified endpoints and runs offline.

**What is placeholder / not yet wired (the honest gaps):**
- **Persistence is not connected at all.** `db/schema.sql` defines 20 tables, but
  **no application code imports asyncpg/SQLAlchemy or touches Postgres.** The API
  is stateless per-request; the Brain runs on its in-memory fallback. The schema
  is, today, dead code relative to the running system.
- **"Generation" is deterministic templates, not AI.** The Generator, Scorer,
  Mission, Quality, Cultural and Personality engines work by keyword/marker
  density and string templates. This is great for tests and offline runs, but no
  LLM is actually driving content at volume — the LLM path exists but is thin and
  unparsed in practice.
- **Scanners are illustrative stubs.** The Harvester returns hand-written sample
  signals; no Firecrawl/Feedly/Trends/Crawl4AI connector exists.
- **The PWA dashboard does not exist as code** — it is a spec doc only.
- **n8n has 1 of the 7 specified workflows**, and even that one only has a sticky
  note where publishing should be.
- **No publishing, no media pipeline, no approval queue, no metrics ingestion.**

### Status at a glance

| Area | Spec'd | Built (real) | Placeholder | Missing |
| ---- | :----: | :----------: | :---------: | :-----: |
| Guardrails / Prime Directive | ✅ | ✅ **Complete** | — | — |
| Core API surface (15 endpoints) | ✅ | ✅ Endpoints exist & run | Responses are in-memory only | Auth, persistence-backed reads |
| Database schema (`schema.sql`) | ✅ | ✅ Well-designed SQL | — | **Not connected to any code** |
| Persistence / repository layer | ✅ | — | — | **Entirely missing** |
| Content Tournament | ✅ | ✅ Pipeline shape + tests | Generation is template-based | LLM-at-volume, LLM-judge |
| Scoring (8 dims) | ✅ | ✅ Deterministic + tested | Keyword-density only | LLM rationale pass |
| Mission Advisor (5) / Quality (11) | ✅ | ✅ Deterministic + tested | Keyword-density only | — |
| Daily 20-post / ~140 assets | ✅ | ✅ Produces 20 + 140 specs | Assets are *briefs*, not media | Real assets, persistence |
| Content Flywheel | ✅ | ✅ 7 asset specs + tests | Specs only | Media rendering |
| Founder Engine (~80%) | ✅ | ✅ + tested | — | Cross-day state (needs DB) |
| Scanners / Intelligence Harvester | ✅ | Model + Brain write | ✅ **Illustrative stub** | Real connectors |
| Watchtower / FRI | ✅ | ✅ + tested | — | Real metrics ingestion |
| Agent library (38) | ✅ | ✅ 37 agents + router | — | 1 missing vs docs; no exec |
| LLM layer | ✅ | ✅ Claude→Ollama→stub | Output parsing best-effort | Structured output |
| n8n workflows (7 spec'd) | ✅ | 1 of 7 | Publishing = sticky note | 6 workflows + publish wiring |
| PWA dashboard | ✅ | — | — | **Entire frontend** |
| Publishing (Postiz) | ✅ | — | — | Entire integration |
| Media pipeline (ComfyUI/11Labs/…) | ✅ | — | — | Entire pipeline |
| Docker / CI / docs | ✅ | ✅ Complete | — | Image build/deploy in CI |

**One-line verdict:** the *brain stem and value system* are built and trustworthy;
the *body* (memory, senses, hands, face) is specified but not yet attached.

---

## 2. Detailed audit

### 2.1 Built and trustworthy (ship-quality today)

- **Guardrails** (`guardrails/policy.py`, `engine.py`) — hard gate runs first;
  blocked candidates forced to score `0.0`. Covers fabrication, medical overclaim,
  engagement bait, banned emoji, comment hygiene, slurs/harassment/punching-down,
  plus advisory risk flags (medical/legal/benefits/sponsor/copyright). 18 tests.
  **No changes needed; extend by test-first only.**
- **Tournament** (`tournament.py`) — generate → gate → score → improve-top-6 →
  rank → dedup → select → founder-rebalance → remember-to-Brain. Tested.
- **Scoring** (`scoring.py`) — 8 weighted dimensions, weights sum to 1.0, Brain
  learning nudges bounded so values can't be swamped. Tested.
- **Mission** (5 impacts, advance/hold/reject) and **Quality** (11 dims, ≥8 bar) —
  both deterministic, both tested.
- **Daily director** (`daily.py`) — fixed 20-slot brief, each slot fully processed,
  emits 20 posts and ~140 asset specs. Tested (`DAILY_BRIEF == 20`).
- **Founder, Cultural, Watchtower, Engagement, Tagging, Personality, Flywheel** —
  all real deterministic logic with tests.
- **Infra** — `docker-compose.yml` (4 core + 6 profiled services), `Dockerfile`,
  `Makefile`, `setup.sh`, CI (ruff + mypy-advisory + pytest). Solid.

### 2.2 Placeholder-only (looks done, isn't load-bearing yet)

- **AI generation.** `generator.py` calls the LLM but falls back to 8 fixed
  templates, and the parse step is best-effort. In every test/offline run, content
  is templates. **No LLM is generating hundreds of real candidates.**
- **Scanners.** `harvester.py` literally returns "illustrative, abstracted
  signals." No external source is contacted.
- **The daily ~140 assets** are *briefs* (`Asset(kind, platform, brief, hook)`),
  not rendered media.
- **n8n `daily_content_cycle.json`** ends at a sticky note: "Wire your Postiz node
  here." It harvests and runs a tournament but nothing publishes.

### 2.3 Missing entirely

1. **Persistence layer.** No code connects to Postgres. `schema.sql` is unused.
   Every API call is amnesiac; founder-presence and learning can't compound across
   days because nothing is stored. **This is the highest-leverage gap.**
2. **PWA dashboard.** No `frontend/`, no `package.json`, no manifest/service
   worker. Spec only (`docs/PWA_DASHBOARD.md`).
3. **Approval queue.** `publish_decision` table exists; no endpoint or flow writes
   to it. The human gate the whole architecture depends on is not implemented.
4. **Publishing** (Postiz), **media generation** (ComfyUI/Flux/ElevenLabs/Whisper/
   OpenCut), **real metrics ingestion** for the Watchtower.
5. **6 of 7 n8n workflows** (scanner sweep, comment-to-content, nightly learning,
   campaign factory, media production, relationship follow-ups).
6. **Auth** (Cloudflare Access / API keys) — no protection on any endpoint.

### 2.4 Discrepancies to fix

- Docs say **38 agents**; registry has **37**. Reconcile (add the missing one or
  correct the docs).
- Docs/README imply a stateful, learning, publishing organism; `ROADMAP.md` is
  honest that it isn't yet. Align README "Status" wording with this audit.

---

## 3. Next implementation plan (phased)

Ordering follows the request: **core API → database → n8n → PWA → scanners →
guardrails → daily pipeline**, sequenced so each phase unblocks the next. Every
phase keeps the prime rule: *graceful degradation stays intact, and a guardrail
test precedes any new capability.*

### Phase 1 — Persistence & the real Core API (foundation)
**Goal: the system remembers.** Without this, nothing compounds.
- Add a repository layer (`core/invisable_os/db/`) using SQLAlchemy 2.0 async +
  asyncpg, with an **in-memory fallback** mirroring the Brain pattern so offline
  tests still pass with zero DB.
- Wire `content_candidate`, `candidate_score`, `publish_decision`,
  `performance_signal`, `trend_signal`, `founder_recognition`, `mission_score`,
  `risk_flag` to the engines that already produce those objects.
- Make the Brain prefer real ChromaDB; persist `winning_pattern` etc.
- New/changed endpoints: persist tournament + daily results; add
  `GET /v1/queue` (approval queue), `POST /v1/queue/{id}/approve|reject|schedule`,
  `GET /v1/daily/today` (read back today's plan), `GET /v1/founder/recognition`.
- Add Alembic migrations generated from `schema.sql`; add a `pytest` Postgres
  service to CI.
- **Acceptance:** founder presence and Brain learning visibly compound across two
  consecutive `/v1/daily/plan` runs; tests cover persisted + fallback paths.

### Phase 2 — n8n workflows + publishing path
- Implement the remaining 6 workflows from `docs/N8N_WORKFLOW_MAP.md`.
- Replace the sticky note with a real **approval-queue → Postiz** publish path
  (degrades to a no-op "dry-run publisher" when `POSTIZ_API_KEY` is absent).
- Add `POST /v1/publish` + per-platform formatting.
- **Acceptance:** an approved post moves `publish_decision` → `scheduled` →
  `published` end to end in dry-run mode, no external keys required.

### Phase 3 — PWA dashboard
- Scaffold `frontend/` (Vite + React + TS, installable PWA: manifest + service
  worker, offline read views, push for approvals).
- Build the 8 left-rail sections against the existing API contract, starting with
  **Today** (20-post plan, mission/quality badges, approve/regenerate/schedule)
  and **Queues**.
- Cloudflare Access in front; API-key auth on the core.
- **Acceptance:** founder can load today's plan on a phone, approve a post, and see
  it enter the schedule queue.

### Phase 4 — Real scanners (Intelligence Harvester)
- Implement connectors behind `harvest()`: Firecrawl, Feedly, Google Trends,
  Crawl4AI, AnswerThePublic — each abstracting (never copying) into `trend_signal`.
- Keep the illustrative generator as the offline fallback.
- Wire the hourly **Scanner Sweep** workflow; raise `opportunity` rows.
- **Acceptance:** with a Firecrawl key, real abstracted signals land in Postgres &
  Brain; with no key, offline signals still flow. Originality guardrail tested
  against scraped text.

### Phase 5 — Live AI generation at volume + guardrail hardening
- Wire Claude/Ollama for real candidate generation with **structured output**
  (JSON schema) so parsing is reliable; add an **LLM-judge scoring pass** layered
  *on top of* the deterministic floor (never replacing the hard gate).
- Harden guardrails for LLM-authored text (prompt-injection, fabricated stats,
  impersonation) — **test-first**, per the guiding principle.
- **Acceptance:** a tournament generates 100+ genuinely varied LLM candidates; the
  deterministic guardrail still vetoes anything the LLM judge would have passed.

### Phase 6 — Media pipeline + metrics ingestion
- ComfyUI/Flux (image), Wan/Hunyuan/LTX (video), ElevenLabs (voice), Whisper
  (captions), OpenCut (assembly), ResourceSpace (asset library) — triggered by
  approved video briefs (the Media Production workflow).
- Real platform-metrics connectors feeding `POST /v1/watchtower/ingest`; surface
  the Founder Recognition Index over time.

### Cross-cutting (every phase)
- Reconcile the 37-vs-38 agent count and align README "Status" with reality.
- Add API auth before the PWA ships.
- CI: build the Docker image; run tests against a real Postgres.
- Keep the invariant: **no capability without a guardrail test; degrade gracefully.**

---

## 4. Recommended immediate next step

**Phase 1 (persistence + approval queue).** It is the keystone: the daily pipeline,
founder balancing, Watchtower learning, and the PWA all assume durable state that
does not exist yet. Everything else is more valuable once the system can remember.
