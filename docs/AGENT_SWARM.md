# Agent Swarm — 20-bot content production

> Always generate more than you publish, and reject more than you keep.

The Agent Swarm is the orchestration layer that ties the platform's engines into the
V3 spec's pipeline: **scan → generate → gate → stock**. Each cycle, 20 specialist
bots surface topics, draft original content, run it through every safety check the
platform owns, and stock the survivors into the [Content War Chest](WAR_CHEST.md).

- Service: [`core/invisable_os/services/swarm.py`](../core/invisable_os/services/swarm.py)
- Table: [`db/schema.sql`](../db/schema.sql) (`bot_output`)
- API: `/v1/swarm/*` in [`api/routes.py`](../core/invisable_os/api/routes.py)
- PWA: the **Swarm** dashboard tab (Agent Swarm Dashboard)

## The 20 bots

| Stage | Bots |
| ----- | ---- |
| **scan** (5) | UK Source Scanner · Construction Scanner · Autoimmune & Invisible Illness · Trades Relatability · Pop Culture Index |
| **generate** (8) | Hook · Script · Caption · Hashtag & Tag · Humour · Founder Voice · Partner/Sponsor · Remix/Parody |
| **gate** (6) | Rights & Source · Fact Checker · Quote & Attribution · Audio Quality · Visual Quality · Brand Guardian |
| **schedule** (1) | Scheduler & War Chest |

## The pipeline (one cycle)

1. **Scan** — each scanner bot surfaces its topic domain (offline: a deterministic
   topic pool; with connectors: abstracted scan results).
2. **Generate** — each generate bot drafts against every scanned topic via the
   content generator (degrades to safe, original templates offline).
3. **Gate** — the only **hard rejection** is the brand guardrails (the Prime
   Directive). Below-bar quality and fact-led-without-source are **flagged for
   review**, not dropped:
   - **Brand Guardian / Rights & Source** → hard gate (fabrication, overclaim,
     punching-down, banned content).
   - **Fact Checker / Quote & Attribution** → a fact-led claim with no credible
     source is flagged `needs_human_review` (never auto-stocked or auto-published —
     see [the Credible Source Rule](SOURCES.md)).
   - **Audio / Visual Quality** → mapped to the quality score.
4. **Stock** — every brand-passing draft is **enqueued** for review. Only the
   genuinely clean ones (fact-clean, on-mission, strong quality average) are
   **auto-stocked** into the War Chest reserve. Anything flagged stays queued for a
   human.

## The funnel

A cycle returns a funnel so the dashboard can show the spec's
`500 raw → 250 usable → 100 approved → publish` shape:

```
raw_drafts → passed_brand_gate → quality_passed / fact_check_clean
           → usable_drafts_queued → needs_human_review
           → stocked_to_war_chest   (+ brand_rejected)
```

`reject_rate` is reported per cycle — the swarm is meant to reject heavily.

## How hard it runs

Reserve health (from the War Chest) is reported alongside each cycle: a thin reserve
(`below_minimum`) signals the swarm should keep producing; a strong one (`elite`)
means it can ease off. The cadence target (48 → 72 → 96 posts/day) follows the same
tiers.

## API

| Method & path | Purpose |
| ------------- | ------- |
| `GET /v1/swarm/bots` | the 20 bots + lifetime produced/passed/pass-rate |
| `GET /v1/swarm/stats` | production funnel, best/weakest bot, reserve health |
| `POST /v1/swarm/run` | run one cycle (`drafts_per_topic`) |
| `GET /v1/swarm/outputs` | per-bot output records (filter by `cycle_id` / `bot_name`) |

## bot_output

Each bot writes one `bot_output` row per cycle: `bot_name`, `stage`, `produced`,
`passed`, `rejected`, a representative `score`, and `status` — the raw material for
the dashboard's drafts-today, pass-rate, and best/weakest-bot views.
