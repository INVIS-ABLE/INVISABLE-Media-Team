# Newsroom Mode

> Fast, but never a rumour.

When something lands in the news the trades or the invisible-illness community
care about, speed matters — but not at the cost of the
[Credible Source Rule](SOURCES.md). Newsroom Mode takes a headline and its source
and, in one call, drafts a spread of angles, grounds each in the supplied source,
and runs the lot through the platform's hard gates.

- Module: [`services/newsroom.py`](../core/invisable_os/services/newsroom.py)
- API: `POST /v1/newsroom/brief`

## The spread

Four rapid-response angles by default — a founder **reaction**, an **explainer**,
a show of **solidarity**, and a **myth-vs-reality** buster — each generated, then
gated (brand reject; quality, mission, and the Credible Source Rule annotate).

## Honest about readiness

- The supplied source is assessed against the credibility hierarchy: `tier` and
  `credible_for_facts` (tier ≤ 7).
- A fact-led angle with **no credible source** behind it is flagged
  `source_required` and held for review — never shipped as a rumour.
- A sensitive headline is routed through [Crisis Mode](CRISIS_MODE.md) first;
  `publish_ready` stays `false` until a human signs off with signposting.
- `guidance` spells out exactly what to do before publishing.

## Surface

```
POST /v1/newsroom/brief
  { "headline": "ONS reports tool theft up 20%", "summary": "",
    "source_name": "ONS", "source_url": "", "source_type": "gov",
    "platform": "tiktok", "count": 4, "persist": false }
  →
  { newsroom_id, headline, platform,
    source: { name, url, source_type, tier, credible_for_facts },
    crisis: { sensitive, requirements, signposting },
    angles: [ { angle, pillar, candidate, brand_passed, quality_avg,
                mission_verdict, fact_ok, fact_led, needs_review, attribution } ],
    funnel: { raw, brand_passed, brand_rejected, needs_review },
    source_required, publish_ready, guidance, persisted, queued_ids }
```

`persist: true` enqueues the brand-safe angles, each tagged `newsroom:<id>` and
carrying a clean attribution line; a dry run (default) returns the package without
touching the queue. `count` is clamped to 1–12. Everything runs offline.
