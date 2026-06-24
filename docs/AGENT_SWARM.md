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

1. **Scan** — each scanner bot surfaces its topic domain. This is **source-led**
   ([`services/source_scan.py`](../core/invisable_os/services/source_scan.py)): when
   credible sources with RSS feeds are configured, the scanner pulls **live
   headlines** and routes each to the right bot by topic area; any bot with nothing
   fresh falls back to a deterministic seed pool, so the swarm never starves. Fetching
   degrades gracefully (no network / no feeds → seed pool, never an error), and a
   headline is only ever used as a *topic to brief original content* — never reposted.
   - `GET /v1/swarm/topics` previews what each bot would feed; `POST /v1/swarm/sources/seed`
     seeds a starter set of credible UK-first feeds (GOV.UK, NHS, …).
2. **Generate** — each generate bot drafts against every scanned topic via the
   content generator. Each bot carries a **specialist persona** that sharpens the
   LLM's voice for its craft (Humour Bot → warm British dry humour; Founder Voice →
   raw, mission-led first person; Partner/Sponsor → sponsor-safe, no false claims;
   Hook Bot → scroll-stopping openers; …). The persona *augments* — never relaxes —
   the generator's safety system prompt, and is ignored by the deterministic
   template fallback, so generation stays safe and testable offline.
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
