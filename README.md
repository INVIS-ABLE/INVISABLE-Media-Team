# INVISABLE® AI Media Agency OS

> The central operating system of the INVISABLE® movement — a unified, founder-led
> media platform that grows awareness of invisible illness, builds the INVISABLE®
> brand, supports the community, and increases the recognition of founder
> **Stephen Garnham** as a consequence of genuine impact.

INVISABLE OS is **one platform**, not a collection of disconnected tools. Every
engine reads from and writes back to a shared memory — **`INVISABLE_BRAIN`** — so
the system compounds what it learns over time.

---

## Why this exists

Invisible illnesses are real, widespread, and under-recognised. INVISABLE® is a
movement to change that. This operating system is the machine that runs the
movement's media presence at scale **without ever trading trust for reach**.

### The Prime Directive

> **If a decision increases reach but damages trust, reject it.**
>
> **If a decision increases awareness, trust, community value, and founder
> recognition simultaneously, prioritise it.**

This rule is not a slogan. It is encoded as a hard gate
([`guardrails`](core/invisable_os/guardrails/)) that every piece of content must
pass before it can be published.

---

## What the platform optimises for

| Always optimise for | Never optimise for |
| ------------------- | ------------------ |
| trust               | controversy        |
| awareness           | outrage            |
| authenticity        | misinformation     |
| consistency         | spam               |
| education           | fake engagement    |
| humour              | fake stories       |
| community value     | fabricated testimonials |
| long-term brand building | fabricated founder experiences |

---

## The Engines

The platform is composed of cooperating engines, each a real module in
[`core/invisable_os/engines`](core/invisable_os/engines/):

| Engine | Responsibility |
| ------ | -------------- |
| **Content Tournament Engine** | Generate hundreds of candidates daily, then score → improve → rank → select only the highest-quality outputs. |
| **Algorithm Watchtower** | Monitor platform performance and feed learning back into `INVISABLE_BRAIN`. |
| **Cultural Intelligence Engine** | Understand British culture, humour, trades culture, football culture, and live social trends. |
| **Intelligence Harvester** | Monitor *public* information sources, trend signals, creator content, and emerging opportunities. |
| **Founder Engine** | Keep founder presence at ~80% of published content and grow founder recognition. |
| **INVISABLE_BRAIN** | Shared long-term memory (vector + structured) that every engine learns from. |

See [`docs/ENGINES.md`](docs/ENGINES.md) for the detailed design of each.

### From tools to a media organisation — the Departments

The platform is organised as departments, not disconnected tools. On top of the
engines above sit:

| Department | What it adds |
| ---------- | ------------ |
| 🏛️ **Governance** | **Mission Advisor** (scores every idea on awareness/community/fundraising/partner/long-term impact) · **Quality Control** (11 dimensions /10, must clear the bar) · Brand Guardian veto. |
| 🎨 **Creative** | Humour & Personality engine — warm, British, self-deprecating humour that laughs *with* the community, never punches down. The content personality mix (30% humour · 25% education · 20% community · 10% founder · 5% partner · 5% trends · 5% campaigns). |
| 🎬 **Production** | **Content Flywheel** — one idea → TikTok, Reel, caption, quote card, carousel, story poll, comment angle + a future idea. |
| ⚙️ **Automation** | **Daily Output System** — produces the day's 20 posts (~140 assets), each gated, mission-scored, quality-checked, and spun. |
| 🤝 **Relationship** | Fixed Tag Network (approved-only tagging), Partner CRM, People & consent. |
| 🕵️ **Intelligence / 📚 Knowledge / 🎤 PR** | Competitor & opportunity scanning, NHS/benefits & construction knowledge, journalist/press tooling. |

38 specialist **agents** ([`docs/AGENT_LIBRARY.md`](docs/AGENT_LIBRARY.md)) carry the
guardrails into every call. See [`docs/DEPARTMENTS.md`](docs/DEPARTMENTS.md),
[`docs/GODTIER_ARCHITECTURE.md`](docs/GODTIER_ARCHITECTURE.md),
[`docs/DAILY_PIPELINE.md`](docs/DAILY_PIPELINE.md),
[`docs/N8N_WORKFLOW_MAP.md`](docs/N8N_WORKFLOW_MAP.md),
[`docs/PWA_DASHBOARD.md`](docs/PWA_DASHBOARD.md), and
[`docs/INSTALL_ORDER.md`](docs/INSTALL_ORDER.md).

---

## Originality & ethics (non-negotiable)

The platform **may** learn patterns, structures, formats, audience reactions, and
content mechanics. The platform **must never**:

- copy copyrighted works,
- duplicate creator content,
- impersonate people without authorisation,
- fabricate stories, testimonials, or founder experiences.

These rules are enforced in code, not just policy. See
[`docs/VALUES.md`](docs/VALUES.md).

---

## The Stack

INVISABLE OS orchestrates a self-hostable, mostly open stack. See
[`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) and [`docker-compose.yml`](docker-compose.yml).

| Layer | Tooling |
| ----- | ------- |
| Reasoning / LLMs | [Claude](https://claude.ai), [Ollama](https://ollama.com) (Qwen, DeepSeek) |
| Orchestration | [n8n](https://n8n.io), this `core` API |
| Memory | [PostgreSQL](https://www.postgresql.org), [ChromaDB](https://www.trychroma.com) |
| Chat UI | [Open WebUI](https://openwebui.com) |
| Tooling bridge | [Composio](https://composio.dev) |
| Harvesting | [Firecrawl](https://firecrawl.dev), [Crawl4AI](https://github.com/unclecode/crawl4ai), [Feedly](https://feedly.com), [Google Trends](https://trends.google.com) |
| Media | [ComfyUI](https://github.com/comfyanonymous/ComfyUI) + [Flux](https://blackforestlabs.ai), [ElevenLabs](https://elevenlabs.io), [Whisper](https://github.com/openai/whisper), [OpenCut](https://github.com/OpenCut-app/OpenCut) |
| Publishing | [Postiz](https://postiz.com) |
| Assets | [ResourceSpace](https://www.resourcespace.com) |
| Ops | [Docker](https://www.docker.com), [Watchtower](https://containrrr.dev/watchtower), [Uptime Kuma](https://uptime.kuma.pet), [Cloudflare Tunnel](https://www.cloudflare.com/products/tunnel) |

---

## Quick start

```bash
# 1. Configure (optional — the platform runs fully without any keys)
cp .env.example .env

# 2. Install + run the operational platform locally (no services needed)
cd core
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest                      # 56 deterministic tests

invisable migrate           # create tables (local SQLite by default)
invisable plan --persist    # run the day's 20 posts into the approval queue
invisable queue             # review what's waiting
invisable approve <id>      # approve an item
invisable publish           # take it live (dry-run until Postiz is configured)
invisable serve             # API at http://localhost:8080/docs

# 3. Or bring up the whole stack (core self-migrates on boot)
docker compose up -d core postgres chroma   # minimal
docker compose up -d                         # full agency OS
```

Run the entire platform once, end to end, offline:

```bash
invisable demo
```

Or drive it over HTTP — plan a whole day straight into the approval queue:

```bash
curl -s -X POST localhost:8080/v1/daily/plan \
  -H 'content-type: application/json' -d '{"persist": true}' | jq '.total, .total_assets'
```

Schedule the approved queue into recurring posting slots and render media:

```bash
invisable seed-channels    # channels + a Mon–Fri × 3-slot weekly schedule
invisable schedule         # fill the next open slots (timezone-aware)
invisable calendar         # see the week laid out by day
invisable produce <id>     # render a post's flywheel assets into the media library
```

See [`docs/OPERATIONS.md`](docs/OPERATIONS.md) for the full runbook,
[`docs/SCHEDULING.md`](docs/SCHEDULING.md) for the posting-slot queue + media
pipeline, and [`docs/REFERENCES.md`](docs/REFERENCES.md) for the open-source
schedulers we studied (and their licences).

---

## Repository layout

```
.
├── core/                     # The INVISABLE OS application (Python / FastAPI)
│   └── invisable_os/
│       ├── engines/          # Tournament, Watchtower, Cultural, Harvester, Founder
│       ├── brain/            # INVISABLE_BRAIN shared memory
│       ├── guardrails/       # The Prime Directive, encoded
│       ├── llm/              # Claude + Ollama clients (degrade gracefully)
│       ├── models/           # Domain models (content, scores, metrics)
│       └── api/              # HTTP surface
├── db/schema.sql             # PostgreSQL schema
├── n8n/workflows/            # Automation workflows (daily content cycle, harvesting)
├── docs/                     # Architecture, values, engines, deployment
├── docker-compose.yml        # Full self-hostable stack
└── .env.example
```

---

## Status

This is the **foundation** of the operating system: the architecture, the shared
memory, the engines with real (tested) selection and guardrail logic, and the
stack orchestration are in place and runnable. LLM- and platform-API-dependent
steps degrade gracefully to deterministic behaviour so the system is testable and
demonstrable without external credentials.

See [`docs/ROADMAP.md`](docs/ROADMAP.md) for what is wired vs. what is next.
