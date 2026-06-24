# INVISABLE® AI Media Agency OS

> The central operating system of the INVISABLE® movement — a unified, founder-led
> media platform that grows awareness of invisible illness, builds the INVISABLE®
> brand, supports the community, and increases the recognition of founder
> **Stephen Garnham** as a consequence of genuine impact.

INVISABLE OS is **one platform**, not a collection of disconnected tools. Every
engine reads from and writes back to a shared memory — **`INVISABLE_BRAIN`** — so
the system compounds what it learns over time.

---

## ⬇️ Download the desktop app

[![Download for Windows](https://img.shields.io/github/v/release/INVIS-ABLE/INVISABLE-Media-Team?label=Download%20for%20Windows&logo=windows&style=for-the-badge)](https://github.com/INVIS-ABLE/INVISABLE-Media-Team/releases/latest)

**[⬇️ Get the latest INVISABLE® Media Team installer →](https://github.com/INVIS-ABLE/INVISABLE-Media-Team/releases/latest)**

The full desktop application — packaged, signed installer. Download it, **double-click
to install**, and it opens on your desktop:

- **`INVISABLE Media Team_x.x.x_x64-setup.exe`** — Windows installer (recommended). Run
  it and pick your role on first launch:
  - **🛰️ Command Centre** on the server — the agency control room.
  - **🎬 Studio Worker** on the 5090 — the render/production worker.

> The installer is published as a **GitHub Release** (shown in the **Releases** panel on
> the right of this page). It's built automatically by the
> [desktop build workflow](.github/workflows/desktop-build.yml): push a `desktop-vX.Y.Z`
> tag (or run the workflow manually) and the Windows `.exe`/`.msi` is built and attached
> to the release. Build it yourself any time with `cd desktop && npm run tauri build`.

See [`desktop/README.md`](desktop/README.md) for full setup, the role selector, server
URL settings, and Cloudflare Access.

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
| **Remix, Parody & Trend Intelligence Engine** | Scan culture & trends, index pop-culture safely, and create *original* parody/reaction/voiceover/meme content — a rights-safe remix studio, never a "steal and repost" machine. |
| **5090 Studio Engine** | Generate, review and export strong content **fully offline** on the Studio Worker (the 5090) — no server, PWA or social connection. Each post arrives complete (hook, caption, hashtags, script, visual idea, founder-presence suggestion) with four review scores (risk, mission, humour, authenticity), then approve/reject/edit/export to local folders. |
| **Human-led Co-Pilot** | The app runs **alongside Stephen**, never instead of him. Four posting/interaction **intensity modes** (Introduction → Modest Growth → Active Influencer → Career) scale the rhythm without ever scaling autonomy: at every level the AI only drafts and suggests, and human approval is required before anything publishes or sends. Emergency controls (Pause All, Manual Mode, Stop Posting, Stop Interactions, Clear Today's Queue, Founder Override) keep Stephen in control. The **Interaction Centre** is where the AI drafts polite, on-mission replies to comments/mentions/questions/collabs — and Stephen sends them. |
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
| 🎭 **Remix, Parody & Trend Intelligence** | Scanner + remix brain + rights database + parody engine. Analyses/parodies/transforms trends into original content; a rights filter (8 statuses) blocks reuploading others' videos as-is. See [`docs/REMIX_ENGINE.md`](docs/REMIX_ENGINE.md). |
| 🕵️ **Intelligence / 📚 Knowledge / 🎤 PR** | Competitor & opportunity scanning, NHS/benefits & construction knowledge, journalist/press tooling. |

84 specialist **agents** ([`docs/AGENT_LIBRARY.md`](docs/AGENT_LIBRARY.md)) carry the
guardrails into every call, organised as a **multi-agent production studio** of seven
pipeline teams — research → strategy → writing → production → quality → publishing →
learning ([`docs/PRODUCTION_STUDIO.md`](docs/PRODUCTION_STUDIO.md)). The headline of
that studio is the **Visual Layout Agent** and the **Video Quality Gate**: deterministic
safe-area geometry that keeps captions off faces and platform UI, plus a full
pre-approval video checklist. See also [`docs/DEPARTMENTS.md`](docs/DEPARTMENTS.md),
[`docs/TOOL_INTEGRATION_REVIEW.md`](docs/TOOL_INTEGRATION_REVIEW.md),
[`docs/REMIX_ENGINE.md`](docs/REMIX_ENGINE.md),
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
| Reasoning / LLMs | [Claude](https://claude.ai), [Ollama](https://ollama.com) (Qwen, DeepSeek) — structured JSON generation + an [LLM-judge](docs/GENERATION.md) on the deterministic floor |
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
invisable doctor            # run the whole pipeline once & confirm everything works
invisable plan --persist    # run the day's 20 posts into the approval queue
invisable queue             # review what's waiting
invisable approve <id>      # approve an item
invisable publish           # take it live (dry-run until Postiz is configured)
invisable serve             # dashboard at http://localhost:8080/app · API docs at /docs

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
│       ├── engines/          # Tournament, Watchtower, Cultural, Harvester, Founder, Remix
│       ├── brain/            # INVISABLE_BRAIN shared memory
│       ├── guardrails/       # The Prime Directive + the rights filter, encoded
│       ├── llm/              # Claude + Ollama clients (degrade gracefully)
│       ├── models/           # Domain models (content, scores, metrics)
│       └── api/              # HTTP surface
├── db/schema.sql             # PostgreSQL schema
├── n8n/workflows/            # Automation workflows (daily content cycle, harvesting)
├── docs/                     # Architecture, values, engines, deployment
├── desktop/                  # Tauri desktop apps (Command Centre + Studio Worker)
├── docker-compose.yml        # Full self-hostable stack
└── .env.example
```

---

## Desktop apps

Native desktop control surfaces live in [`desktop/`](desktop/) — one Tauri app with
two roles selected at first launch:

- **🛰️ Command Centre** runs on the server: opens the protected PWA and gives Stephen
  the full agency dashboard with manual override (approve/reject/schedule/post-now,
  pause automation, request content) — so the system is never a black box.
- **🎬 Studio Worker** runs on the 5090: claims render jobs from the server, runs
  FFmpeg/Whisper/ComfyUI locally, and uploads finished media back.

They talk to the server over the stable `/api/*` surface
([`core/invisable_os/api/desktop_routes.py`](core/invisable_os/api/desktop_routes.py)),
prefer the LAN at home and Cloudflare Access remotely, and keep all secrets
server-side. See [`desktop/README.md`](desktop/README.md) and
[`desktop/cloudflare/`](desktop/cloudflare/) for build, role, connection, and lockdown
details.

---

## Status

This is the **foundation** of the operating system: the architecture, the shared
memory, the engines with real (tested) selection and guardrail logic, and the
stack orchestration are in place and runnable. LLM- and platform-API-dependent
steps degrade gracefully to deterministic behaviour so the system is testable and
demonstrable without external credentials.

See [`docs/ROADMAP.md`](docs/ROADMAP.md) for what is wired vs. what is next.
