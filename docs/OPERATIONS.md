# Operations Runbook

How to actually run INVISABLE OS day to day. It is operational out of the box: with
no configuration it persists to a local SQLite database and publishes in **dry-run**
(nothing is posted, everything is logged). Point it at Postgres + Postiz to go live.

## The content lifecycle

```
generate → (guardrail gate · mission · quality) → QUEUE
                                                    │
          pending_review ──approve──► approved ──publish──► published
                │                                              ▲
          needs_improvement (below 8/10 quality)               │
                │                                          scheduler
              reject ──► graveyard (the platform learns)
```

Every piece of content is a durable **queue item** with its scores, tags, flywheel
asset list, and any advisory risk flags. Humans approve from the PWA (or the CLI/API).

## Run it locally (zero services)

```bash
cd core && python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

invisable migrate                  # create tables (SQLite at ./data/invisable.db)
invisable seed-tags                # add example approved tag-network members
invisable plan --persist           # run the day's 20 posts into the approval queue
invisable queue                    # see what's waiting
invisable approve <id>             # approve an item
invisable publish                  # take approved items live (dry-run by default)
invisable serve                    # run the API at :8080  (docs at /docs)
```

Or run the whole thing once, end to end, offline:

```bash
invisable demo
```

## Run it as a service

```bash
docker compose up -d core postgres chroma      # core self-migrates on boot
curl -s localhost:8080/health | jq
```

The `core` container talks to Postgres via `DATABASE_URL`; the app creates its tables
on startup, so there is no manual migration step.

## The operational API

| Action | Endpoint |
| ------ | -------- |
| Plan the day **into the queue** | `POST /v1/daily/plan {"persist": true}` |
| List the queue | `GET /v1/queue?status=pending_review` |
| Approve / reject / schedule / publish | `POST /v1/queue/{id}/{action}` |
| Take approved items live | `POST /v1/publish/run` |
| Tag network | `GET/POST /v1/tags` |
| Partners | `GET/POST /v1/partners` |
| Opportunities (scan + list) | `POST /v1/opportunities/scan`, `GET /v1/opportunities` |

## Automate the cadence (n8n)

The shipped [`daily_content_cycle`](../n8n/workflows/daily_content_cycle.json) calls
`POST /v1/daily/plan` each morning. Add a workflow that calls `POST /v1/publish/run`
on your posting schedule, and a nightly one that calls `POST /v1/watchtower/ingest`
with the day's metrics. See [`N8N_WORKFLOW_MAP.md`](N8N_WORKFLOW_MAP.md).

## Going live

| Capability | Set | Effect |
| ---------- | --- | ------ |
| Real publishing | `POSTIZ_API_URL`, `POSTIZ_API_KEY` | `publish` posts via Postiz instead of dry-run |
| Production DB | `DATABASE_URL=postgresql://…` | persistence moves from SQLite to Postgres |
| Live generation | `ANTHROPIC_API_KEY` and/or `OLLAMA_BASE_URL` | candidates are model-generated at volume |
| Harvesting | `FEEDLY_ACCESS_TOKEN`, `FIRECRAWL_API_KEY`, pytrends | real signals feed the Intelligence dept |

Nothing about the lifecycle, guardrails, mission/quality gates, flywheel, or tagging
changes when you go live — only the backends behind them.

## Safety defaults

- **Dry-run publishing** until Postiz is explicitly configured.
- **Approval gate**: nothing is published without an approve transition.
- **Quality gate**: below-bar content lands as `needs_improvement`, not `pending_review`.
- **Risk flags**: medical/legal/benefits/sponsor/copyright content is flagged for
  human review (`needs_human_review`) and never auto-published.
- Secrets via env vars; keep Postgres/Chroma internal; expose only via Cloudflare Tunnel.
