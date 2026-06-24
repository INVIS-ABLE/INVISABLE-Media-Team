# n8n workflows

Automation that drives the platform's daily cadence. Import these into n8n
(Settings → Import from File) or mount `./n8n/workflows` (the compose file already
does at `/workflows`).

| Workflow | What it does |
| -------- | ------------ |
| `daily_content_cycle.json` | 07:00 daily: harvest abstracted public signals → run a Content Tournament (120 candidates, select 5) → branch when winners exist → publish (wire your Postiz node). |

All nodes call the core API via `{{$env.INVISABLE_CORE_URL}}` (set to
`http://core:8080` in `docker-compose.yml`). Winners returned by the tournament are
already guardrail-passed and founder-rebalanced, so the publishing step can trust
them.

## Suggested additional workflows

- **Hourly engagement** — pull notifications, draft compliant comments via
  `/v1/engagement/comment`, queue for human approval.
- **Nightly learning** — push the day's platform metrics to
  `/v1/watchtower/ingest` so the Brain learns and the Founder Recognition Index
  updates.
