# Content Decay Detector

> Old content expires; sameness gets flagged before the audience notices.

A read-only, deterministic scan over the **approval queue** and the **War Chest
reserve** that surfaces the ways a feed rots. It flags — it never deletes.

- Service: [`services/decay.py`](../core/invisable_os/services/decay.py)
- API: `GET /v1/decay/scan`

## What it flags

| Flag | Signal |
| ---- | ------ |
| `overused_hook` | the same hook reused ≥ 3× across recent posts |
| `near_duplicate` | two recent posts with ≥ 0.6 token overlap (too similar in wording) |
| `stale_hashtag` | a hashtag appearing on > 50% of recent posts |
| `expired_reserve` | War Chest items past their `expiry_date` — refresh or retire |
| `category_dominance` | one category > 50% of the ready reserve (feed feels samey) |

Each flag carries a `kind`, a `severity` (low/medium/high), a human `detail`, and the
`refs` (queue / war-chest item ids) so the founder can jump straight to them.

```
GET /v1/decay/scan
→ { ok, scanned: {queue, reserve}, flag_count, by_kind: {...}, flags: [...] }
```

`ok: true` means a clean, varied feed — no decay detected.

## How it composes

The detector reads the same `queue_item` and `war_chest_item` data the rest of the
platform writes, so it needs no new tables. The Scheduler & War Chest bot can run it
each cycle to keep the reserve fresh; the dashboard can show the flags so stale hooks,
duplicates and aged stock get refreshed before they go out. It pairs naturally with
the War Chest's freshness/expiry model and the swarm's anti-repetition draw.
