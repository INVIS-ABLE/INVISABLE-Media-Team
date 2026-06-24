# n8n workflows

Automation that drives the platform's daily cadence. Import these into n8n
(Settings → Import from File) or mount `./n8n/workflows` (the compose file already
does at `/workflows`).

| Workflow | What it does |
| -------- | ------------ |
| `daily_content_cycle.json` | 07:00 daily: harvest abstracted public signals → run a Content Tournament (120 candidates, select 5) → branch when winners exist → publish (wire your Postiz node). |
| `nightly_learning.json` | 23:40 daily: `POST /v1/metrics/sync` — pull Metricool metrics into the Watchtower, updating learnings + the Founder Recognition Index that feed tomorrow's scoring. Safe no-op until Metricool keys are set. |
| `nightly_dam_sync.json` | 00:10 daily: list published posts → for each `POST /v1/dam/sync/{id}` — push finished media into ResourceSpace. Safe dry-run until ResourceSpace keys are set. |

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
