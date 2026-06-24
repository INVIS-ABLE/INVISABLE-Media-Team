# Architecture

INVISABLE OS is **one platform**. The defining design choice is that every engine
shares a single memory (`INVISABLE_BRAIN`) and a single set of values
(`guardrails`). That is what makes it an operating system rather than a folder of
disconnected tools.

```
                          ┌─────────────────────────────────────────┐
                          │              INVISABLE OS                 │
                          │                                           │
   public sources ──▶ Intelligence ──▶┐                              │
   (Firecrawl, RSS,    Harvester       │                              │
    Trends — abstracted)               ▼                              │
                                  ┌──────────┐    ┌────────────────┐  │
   British culture ──▶ Cultural ─▶│          │    │   Founder      │  │
                       Intelligence│ Content  │◀──▶│   Engine       │  │
                                  │ Tournament│    │  (~80% presence)│ │
   Claude / Ollama ──▶ Generator ▶│  Engine   │    └────────────────┘  │
                                  │          │                         │
                                  │ generate │    ┌────────────────┐   │
                                  │   ▼      │    │  GUARDRAILS    │   │
                                  │  GATE ───┼───▶│ (Prime Directive)│ │
                                  │   ▼      │    └────────────────┘   │
                                  │  score   │                         │
                                  │   ▼      │                         │
                                  │ improve  │                         │
                                  │   ▼      │                         │
                                  │  rank    │                         │
                                  │   ▼      │                         │
                                  │ select   │                         │
                                  └────┬─────┘                         │
                                       │ winners                       │
                                       ▼                               │
   publish (Postiz) ◀────────── selected content                      │
        │                                                              │
        ▼                                                              │
   Algorithm Watchtower ──── learnings ──▶  INVISABLE_BRAIN  ◀─────────┘
   (performance signals)                   (Chroma + Postgres)
        │                                        ▲
        └─────── Founder Recognition Index ──────┘
```

## Components

| Layer | Module | Notes |
| ----- | ------ | ----- |
| Values | `guardrails/` | Deterministic hard gate. Runs **first** and is absolute. |
| Memory | `brain/` | Semantic memory over ChromaDB with an in-process fallback. |
| Reasoning | `llm/` | Claude → Ollama → deterministic stub, degrading gracefully. |
| Models | `models/` | `ContentCandidate`, `ScoreCard`, `PerformanceSignal`, … |
| Engines | `engines/` | Tournament, Scorer, Generator, Cultural, Founder, Watchtower, Harvester, Engagement. |
| Surface | `api/`, `main.py` | FastAPI orchestration that n8n and Open WebUI call. |

## Key invariants

1. **Guardrails run before scoring and are absolute.** A blocked candidate's
   composite score is forced to `0.0` (`ScoredCandidate.total`), so it can never be
   selected — the model cannot "score its way past" the values.
2. **Reach never outranks trust.** The `SCORE_WEIGHTS` are tilted toward trust and
   community value; there is no "virality" or "controversy" dimension to optimise.
3. **Everything degrades gracefully.** No API key or service can take the platform
   down; missing dependencies fall back to deterministic behaviour. This is why the
   whole system is testable offline.
4. **The platform compounds.** Winners, learnings, trends, and cultural notes all
   flow back into `INVISABLE_BRAIN`, which the Scorer reads on the next cycle.

## The daily cycle

1. **Harvest** abstracted public signals (`/v1/harvest`).
2. **Run tournaments** per brief/platform (`/v1/tournament/run`) — generate
   hundreds, gate, score, improve, rank, select.
3. **Rebalance** the publishing queue toward ~80% founder presence (Founder Engine).
4. **Publish** the winners (Postiz).
5. **Observe** performance and feed it back (`/v1/watchtower/ingest`), updating the
   Founder Recognition Index.

n8n schedules and wires these steps; see [`n8n/workflows/`](../n8n/workflows/).
