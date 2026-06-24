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

## Next (clearly scoped extensions)

- ⏳ **Live generation at volume** — wire Claude/Ollama prompts for hundreds of
  daily candidates; add structured output parsing and an LLM-judge scoring pass on
  top of the deterministic floor.
- ⏳ **Persistence wiring** — connect the engines to the Postgres schema (currently
  the API is stateless per-request; the schema and Brain are ready).
- ⏳ **Harvester connectors** — Firecrawl / Crawl4AI / Feedly / Google Trends /
  AnswerThePublic adapters behind `harvest()`.
- ⏳ **Media pipeline** — ComfyUI/Flux image gen, ElevenLabs voice, Whisper
  captions, OpenCut assembly, ResourceSpace asset library.
- ⏳ **Publishing** — Postiz scheduling from the winners queue + per-platform
  formatting.
- ⏳ **Platform metrics ingestion** — real connectors feeding the Watchtower.
- ⏳ **Founder Recognition dashboard** — surface the index and presence view over time.

## Guiding principle for every extension

If a new feature increases reach but damages trust, it does not ship. Add a
guardrail test before adding the capability.
