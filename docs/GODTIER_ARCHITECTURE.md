# God-Tier Architecture

The full INVISABLE® AI media operating system: a self-hosted server running 24/7, a
GPU machine for heavy generation, and a PWA dashboard reachable from anywhere.

## Physical layout

```
┌─────────────────────────────────────────────────────────────────────┐
│  SERVER TOWER (24/7)                          5090 GPU MACHINE         │
│                                                                        │
│  core API (this repo)                         ComfyUI                  │
│  n8n            (orchestration)               Flux        (image)      │
│  PostgreSQL     (structured memory)           Wan Video   (video)      │
│  ChromaDB       (semantic memory)             HunyuanVideo(video)      │
│  Open WebUI     (chat UI)                      LTX Video   (video)      │
│  Ollama         (Qwen / DeepSeek)             heavy local generation   │
│  scanners · queues · databank · scheduling                             │
│  approval · analytics · CRM · tagging                                  │
│                                                                        │
│            ▲                         ▲                                  │
│            │  internal Docker net    │  render jobs over LAN/API        │
│            └─────────────┬───────────┘                                  │
│                          │                                              │
│                 Cloudflare Tunnel (secure ingress)                      │
└──────────────────────────┼─────────────────────────────────────────────┘
                           │
                  PWA Dashboard (phone · iPad · PC · browser)
```

## Logical layers

1. **Governance (centre of gravity)** — `guardrails` + `mission` + `quality`. Every
   asset passes the hard gate, the Mission Advisor, and Quality Control before it
   can be approved. The Brand Guardian holds veto.
2. **Memory** — PostgreSQL (relational: candidates, scores, partners, people,
   opportunities, CRM, knowledge) + ChromaDB (semantic: winning patterns, learnings,
   trends, cultural notes). Together they are `INVISABLE_BRAIN`.
3. **Reasoning** — Claude (final selection / high-stakes), Ollama/Qwen/DeepSeek
   (volume), Whisper (transcription). All behind the `llm` layer with graceful
   degradation.
4. **Departments** — the cooperating engines + agents in
   [`DEPARTMENTS.md`](DEPARTMENTS.md).
5. **Production** — ComfyUI/Flux/Wan/Hunyuan/LTX (visual), ElevenLabs (voice),
   Canva/OpenCut (assembly), ResourceSpace (asset library).
6. **Distribution** — Postiz / Metricool / Typefully scheduling; the fixed tag
   network; the approval queue.
7. **Surface** — the `core` API + the PWA dashboard + Open WebUI for ad-hoc chat.

## Data & control flow (the daily loop)

```
07:00  Harvest (Intelligence)  → abstracted signals into the Brain
07:05  Daily Content Director   → 20 slots, each a mini tournament
       per slot:  generate → guardrail gate → score → improve → select
                  → Mission Advisor → Quality Control → Flywheel (5–10 assets)
                  → Tag Network → approval queue
~      Human approves / regenerates from the PWA
       Scheduler → Postiz/Metricool → published
+24h   Watchtower ingests performance → learnings → Brain → next day is smarter
```

## Where the code lives

| Layer | Path |
| ----- | ---- |
| Governance | `core/invisable_os/guardrails/`, `engines/mission.py`, `engines/quality.py` |
| Departments | `core/invisable_os/engines/` |
| Agents | `core/invisable_os/agents/` |
| Memory | `core/invisable_os/brain/`, `db/schema.sql` |
| Reasoning | `core/invisable_os/llm/` |
| Surface | `core/invisable_os/api/`, `main.py` |
| Orchestration | `n8n/workflows/` |
| Stack | `docker-compose.yml` |

See [`DEPLOYMENT.md`](DEPLOYMENT.md) for bring-up and
[`INSTALL_ORDER.md`](INSTALL_ORDER.md) for the recommended build sequence.
