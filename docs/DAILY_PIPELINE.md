# The Daily 20-Post Pipeline

Implemented in [`core/invisable_os/engines/daily.py`](../core/invisable_os/engines/daily.py)
(`DailyContentDirector`). Run it from the API (`POST /v1/daily/plan`) or the CLI
(`python -m invisable_os.demo`).

## The fixed editorial brief (sums to 20)

| Count | Slot | Pillar | Platform / format |
| ----- | ---- | ------ | ----------------- |
| 3 | invisible-illness education | education | Instagram carousel |
| 3 | trades/community relatable | community | Instagram post |
| 3 | humour | humour | TikTok short video |
| 3 | TikTok/Reel scripts | trends | TikTok short video |
| 2 | carousels (myth-bust) | education | Instagram carousel |
| 2 | partner-safe | partner | Instagram post |
| 2 | trend reactions | trends | TikTok short video |
| 1 | founder / mission | founder | Instagram reel |
| 1 | comment / community response | community | Instagram post |

This maps onto the **content personality mix** (`GET /v1/personality/mix`):
30% humour · 25% education · 20% community · 10% founder · 5% partner · 5% trends ·
5% campaigns.

## What happens to every slot

```
for each of the 20 slots:
  1. Tournament:  generate N candidates → GUARDRAIL hard gate → score (8 values)
                  → improve top contenders → rank → dedup → select 1
                  → Founder Engine keeps the running mix ~80% founder presence
  2. Mission Advisor:  score awareness/community/fundraising/partner/long-term
                       → verdict advance | hold | reject
  3. Quality Control:  11 dimensions /10 → if any < 8, flag "needs improvement"
  4. Flywheel:    spin the winner into 7+ assets (TikTok, Reel, caption, quote
                  card, carousel, story poll, comment angle) + a future idea
  5. Tag Network: attach approved-only tags for the platform (never outside list)
  6. Review flags: advisory badge if medical/legal/benefits/sponsor/copyright
```

## Output shape (`DailyPlan.summary()`)

```json
{
  "total": 20,
  "by_pillar": { "humour": 5, "education": 5, "community": 5, "trends": 5, ... },
  "needs_improvement": 7,
  "needs_human_review": 2,
  "total_assets": 140,
  "posts": [
    { "slot": "humour", "pillar": "humour", "hook": "My immune system called in sick…",
      "mission": 0.41, "mission_verdict": "hold", "quality_avg": 7.8,
      "assets": 7, "founder": false }
  ]
}
```

One day's run produces **20 approved-track posts and ~140 derived assets** — the
content factory becomes a media organisation because every post is mission-scored,
quality-gated, and leveraged.

## Try it

```bash
curl -s -X POST localhost:8080/v1/daily/plan \
  -H 'content-type: application/json' -d '{"candidates_per_slot": 16}' | jq '.total, .total_assets, .needs_improvement'
```
