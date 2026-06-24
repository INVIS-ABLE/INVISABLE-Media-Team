# Install Order & Build Roadmap

Build in dependency order so each layer is verifiable before the next. Use official
docs only; keep secrets in env vars; gate all publishing behind approval.

## Phase 0 — Foundations (done in this repo)
1. `core` API + guardrails + engines + departments + agents + tests (`pytest`).
2. PostgreSQL schema (`db/schema.sql`).
3. Docker Compose stack skeleton (`docker-compose.yml`).

```bash
cp .env.example .env
docker compose up -d core postgres chroma
curl -s localhost:8080/health | jq
```

## Phase 1 — Memory & reasoning
4. PostgreSQL (structured) + ChromaDB (semantic) — the two halves of the Brain.
5. Ollama + pull `qwen2.5` / a DeepSeek model: `docker compose --profile llm up -d`.
6. Open WebUI for ad-hoc chat against local models.
7. Add `ANTHROPIC_API_KEY` for Claude on the highest-stakes selection/judging.

## Phase 2 — Orchestration
8. n8n (`docker compose up -d n8n`); import [`n8n/workflows`](../n8n/workflows/).
9. Wire the **Daily Content Cycle** and **Scanner Sweep** to the core API.
10. Stand up the **approval queue** (PWA) — nothing publishes without it.

## Phase 3 — Intelligence & knowledge
11. Harvester connectors: Firecrawl / Crawl4AI / Feedly / Google Trends / AnswerThePublic.
12. Competitor + Opportunity + Sponsor scanners → `competitor` / `opportunity` tables.
13. Knowledge bases (NHS/benefits, construction) → `knowledge_item` (review-gated).

## Phase 4 — Production (5090 machine)
14. ComfyUI + ComfyUI Manager; Flux (image); Wan / Hunyuan / LTX (video).
15. ElevenLabs (voice) + Whisper (captions) + OpenCut (assembly) + ResourceSpace (assets).
16. Connect the Flywheel asset specs → render jobs → back to the approval queue.

## Phase 5 — Distribution & relationships
17. Postiz / Metricool / Typefully scheduling from the approved queue.
18. People & consent DB, Fixed Tag Network, Partner CRM, Community Story Portal.

## Phase 6 — Ops & exposure
19. Uptime Kuma (monitoring) + Watchtower (auto-updates).
20. Cloudflare Tunnel + Access for secure remote PWA access.

## Verify at every phase
```bash
cd core && . .venv/bin/activate && pytest        # logic stays green
python -m invisable_os.demo                       # full cycle, offline
curl -s -X POST localhost:8080/v1/daily/plan -d '{"candidates_per_slot":8}' -H 'content-type: application/json' | jq '.total'
```

## Security rules (non-negotiable)
- Official docs / trusted images only; review any third-party script before use.
- Never expose API keys; use env vars and Docker secrets.
- Keep Postgres + Chroma internal to the Docker network.
- Approval gates before any post goes live; log all actions.
- Cloudflare Tunnel for ingress — do not open raw ports.
