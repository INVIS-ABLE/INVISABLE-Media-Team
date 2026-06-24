# The Big Campaign Button

> One button. The whole platform behind one theme.

For a launch, an awareness day, or a moment in the news, the founder shouldn't
have to drive twenty bots by hand. The Big Campaign Button **concentrates** the
platform: it generates a coordinated burst of on-theme content across every
content pillar, gates it through the same hard checks the rest of the platform
uses, and surfaces the matching War Chest reserve as ready reinforcements.

- Module: [`services/campaign.py`](../core/invisable_os/services/campaign.py)
- API: `POST /v1/campaign/launch`

## What one press does

1. **Care first.** The brief runs through [Crisis Mode](CRISIS_MODE.md) before a
   word is written — a sensitive campaign is flagged for approval and signposting,
   never hyped.
2. **Generate a coordinated burst.** Content is generated round-robin across the
   pillars — founder, education, community, humour, partner, trends — so the
   campaign speaks in many voices at once, not one note repeated.
3. **Gate it.** Brand guardrails hard-reject; quality, mission, and the
   [Credible Source Rule](SOURCES.md) annotate each survivor (`needs_review` for
   high-stakes or unsourced-fact drafts).
4. **Marshal reinforcements.** Matching **ready** [War Chest](WAR_CHEST.md)
   reserve items (by theme word) are surfaced as suggestions — the reserve is
   *offered*, never silently consumed.
5. **Optionally stage.** With `persist: true`, the usable drafts are enqueued into
   the approval queue, each tagged `campaign:<id>` so the whole push is one set.

## Surface

```
POST /v1/campaign/launch
  { "brief": "national tradesperson day", "theme": "", "posts": 12,
    "platform": "tiktok", "persist": false }
  →
  { campaign_id, theme, platform, requested,
    crisis: { sensitive, requirements, signposting },
    funnel: { raw, brand_passed, brand_rejected, usable, needs_review },
    generated: [ { candidate, quality_avg, mission_verdict, pillar, needs_review } ],
    reinforcements: [ <ready war-chest items matching the theme> ],
    ready_to_queue, persisted, queued_ids }
```

`posts` is clamped to 1–60. `theme` defaults to the brief; it's what the reserve
match is keyed on. A dry run (`persist: false`, the default) never touches the
queue — it returns the plan so the founder can review before committing.

Everything is deterministic and offline: the generator degrades to templates, and
the gates are the real hard-gate code.
