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
