# Content War Chest

> **Always generate more than you publish.**

The War Chest is the durable **reserve of approved, ready-to-post assets**. It is what
lets the platform sustain a high posting cadence without ever forcing low-quality
content out the door: the system stockpiles approved work, and the Scheduler draws the
best, non-repetitive item from the reserve for each slot.

- Service: [`core/invisable_os/services/war_chest.py`](../core/invisable_os/services/war_chest.py)
- Table: [`db/schema.sql`](../db/schema.sql) (`war_chest_item`)
- API: `/v1/warchest*` in [`core/invisable_os/api/routes.py`](../core/invisable_os/api/routes.py)
- PWA: the **War Chest** dashboard tab ([`core/invisable_os/web`](../core/invisable_os/web))

## Reserve health

Health is measured by the count of `ready` items, against the V3 thresholds:

| Tier | Ready items | Recommended cadence |
| ---- | ----------- | ------------------- |
| `below_minimum` | < 500 | 24 posts/day — protect the reserve, quality over quantity |
| `minimum` | 500–999 | 48 posts/day (one every 30 min) |
| `healthy` | 1,000–1,999 | 72 posts/day |
| `elite` | 2,000+ | 96 posts/day (one every 15 min) |

A strong reserve means the platform can post more; a thin one means it posts fewer and
keeps generating. The recommended cadence is advisory output of `reserve_health()` —
the scheduler can honour or override it, but it never forces volume from an empty chest.

## Stocking

`stock_approved()` moves every **approved** queue item into the reserve, **idempotently**
(an item already stocked is never duplicated). Each reserve record captures:

- **category** — derived from the content pillar (`humour`, `education`, `community`,
  `founder`, `trends`, `partner`, …); evergreen pillars are flagged `evergreen`.
- **scores** — quality, mission, humour, risk (copied from the queue item).
- **freshness + expiry** — evergreen content gets a long horizon (180 days), topical
  content a short one (30 days). Freshness decays from age vs. that horizon.

## Selection (anti-repetition)

`select_next()` draws the best ready item for the next slot. It scores each candidate on

```
0.45·quality + 0.30·mission + 0.15·freshness + 0.10·humour − 0.5·risk − 0.10·reuse_count
```

and applies a **category-rotation penalty** so it steers away from the category of the
most-recently-used item — *no two consecutive posts feel identical*. The chosen item is
marked `used` (stamping `last_used_at` and bumping `reuse_count`).

## API

| Method & path | Purpose |
| ------------- | ------- |
| `GET /v1/warchest` | reserve level, tier, recommended cadence, category spread |
| `GET /v1/warchest/items` | list reserve items (filter by `category` / `reserve_status`) |
| `POST /v1/warchest/stock` | stock all approved queue items (idempotent) |
| `POST /v1/warchest/select` | draw the best non-repetitive item and mark it used |

## CLI / workflow

The War Chest sits between the **approval queue** and the **scheduler**: approve content
→ `stock` it into the reserve → the scheduler `select`s from the reserve each slot. This
is the "Scheduler & War Chest bot" role from the agent-swarm spec, made concrete and
testable.
