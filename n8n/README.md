# n8n workflows

Automation that drives the platform's daily cadence. Import these into n8n
(Settings → Import from File) or mount `./n8n/workflows` (the compose file already
does at `/workflows`).

| Workflow | Trigger | What it does |
| -------- | ------- | ------------ |
| `daily_content_cycle.json` | 07:00 daily | Harvest abstracted signals → `POST /v1/daily/plan` (persist) → branch when posts exist → read the approval queue. The day lands in `pending_review`; the founder approves in the PWA. |
| `scanner_sweep.json` | hourly :17 | `POST /v1/harvest` (invisible illness, trades, tool theft, benefits, trends) + `POST /v1/opportunities/scan` (podcasts/speaking/sponsors). Abstracted signals only, persisted in core. |
| `comment_to_content.json` | every 30 min | Pull comments/DMs (Composio integration point) → `GET /v1/agents/route` (Comment-to-Content agent) → `POST /v1/engagement/comment` to draft a compliant reply for approval. |
| `nightly_learning.json` | 23:40 daily | `POST /v1/metrics/sync` (Metricool → Watchtower) then `GET /v1/founder/recognition`. Closes the learning loop and updates the Founder Recognition Index. |
| `campaign_factory.json` | webhook `/campaign` | On-demand `{"topic": …}` → `POST /v1/tournament/run` per format (TikTok, Instagram, …) → winners to the approval queue. |
| `media_production.json` | every 15 min | `GET /v1/queue?status=approved` → per item `POST /v1/media/produce/{id}` → `POST /v1/media/assemble/{id}`. Renderers fall back to dry-run when a backend isn't configured. |
| `relationship_followups.json` | 09:03 daily | `GET /v1/partners` → filter active relationships → nudge the founder in the PWA. Read-only; never contacts anyone automatically. |

All nodes call the core API via `{{$env.INVISABLE_CORE_URL}}` (set to
`http://core:8080` in `docker-compose.yml`). Winners and plans returned by the core
are already guardrail-passed, mission/quality-scored and founder-rebalanced, so the
publishing step can trust them.

## Conventions

- Every workflow is **read-mostly against the core API**; the core owns the rules.
- **Nothing publishes without passing through the approval queue** (human gate). The
  daily cycle and campaign factory only ever *queue* content.
- Secrets live in n8n credentials / env vars, never in the workflow JSON. The
  Composio poll in `comment_to_content.json` is marked as an integration point —
  swap the sample `Set` node for a credentialed Composio node.
- `tests/test_n8n_workflows.py` validates every workflow: well-formed JSON, all
  connections resolve, all HTTP nodes use the core URL env, and every `/v1` path +
  method actually exists on the API — so API drift can't silently break automation.
