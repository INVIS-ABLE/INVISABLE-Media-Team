# Format Split Testing

> One idea, several formats, head-to-head — then keep the winner.

The same brief rarely lands the same as a punchy short video, a swipe-through
carousel, a single image, or a plain text post. This builds a **split**: one
gated variant of an idea per format, tagged as one experiment, so they can go out
side-by-side. Once performance signals come back, the **leaderboard** says which
format actually wins.

- Module: [`services/split_test.py`](../core/invisable_os/services/split_test.py)
- API: `POST /v1/split/build` · `GET /v1/split/leaderboard`

## Build a split

```
POST /v1/split/build
  { "brief": "pacing on a busy week", "formats": ["short_video","carousel","image","text_post"],
    "platform": "tiktok", "persist": false }
  →
  { experiment_id, brief, platform, formats,
    variants: [ { format, candidate, brand_passed, quality_avg, mission_verdict, needs_review } ],
    funnel: { raw, brand_passed, brand_rejected, needs_review },
    persisted, queued_ids }
```

- One variant is generated per format (defaults to short video / carousel / image
  / text post; requested formats are de-duped, order preserved).
- Each variant runs through the same hard gates as everything else — brand
  guardrails reject; quality, mission, and the Credible Source Rule annotate.
- `persist: true` enqueues the brand-safe variants, each tagged
  `split:<experiment_id>` **and** `format:<format>`, so the experiment is one set
  and every post knows which arm it belongs to. A dry run (default) returns the
  variants without touching the queue.

## Read the leaderboard

```
GET /v1/split/leaderboard?metric=views&min_samples=3
  →
  { metric, min_samples,
    by_format: [ { format, samples, total_value, avg_value } ],  // ranked by avg
    recommended, confident }
```

The leaderboard joins the Watchtower's performance signals to the **format** of
the post they belong to (via the approval queue), averages per format, and
recommends the best format that has at least `min_samples` signals behind it.
Below that threshold it withholds a recommendation (`recommended: null`,
`confident: false`) rather than over-trust a tiny sample.

Pass `metric` to rank on one metric (e.g. `views`, `saves`); omit it to pool all
signals. Everything is deterministic and offline.
