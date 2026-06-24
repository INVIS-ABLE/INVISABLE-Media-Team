# Credible Sources & the Fact-Check Rule

> The system must never present a social-media rumour as a fact.

Any **fact-led** post must carry a **credible source**. This is the fact-attribution
equivalent of the brand guardrails: a deterministic, un-talk-around-able check that
sits in front of the approval queue.

- Service: [`core/invisable_os/services/fact_check.py`](../core/invisable_os/services/fact_check.py)
- Tables: [`db/schema.sql`](../db/schema.sql) (`source`, `source_claim`)
- API: `/v1/sources*` and `/v1/factcheck` in [`api/routes.py`](../core/invisable_os/api/routes.py)
- PWA: the **Sources** dashboard tab (Source Control Centre)

## What counts as "fact-led"

A post is fact-led if it contains any of: a **percentage or statistic**, a
**fact-claim phrase** ("according to", "research shows", "government figures",
"reported that", …), a **hard-claim topic** (tool theft, waiting lists, employment
rate, PIP/benefits, …), or a **specific year alongside another signal**. Pure
solidarity/opinion/humour is *not* fact-led and needs no source.

## The rule

`check_post(text, sources)` returns a verdict:

- **not fact-led** → always `ok` (a source is welcome but not required).
- **fact-led + ≥1 credible source** (tier ≤ 7) → `ok`, with clean attribution lines
  ("Source: ONS").
- **fact-led + only weak sources** (social/community, tier 8) → **not `ok`**; the weak
  sources are surfaced so a stronger one can be attached. Social/community sources are
  for *lived experience*, never hard facts.
- **fact-led + no source** → **not `ok`**; attach a credible source before approval.

## Source credibility hierarchy

Sources are ranked into tiers (1 = highest), from the V3 spec's preferred order:

| Tier | Sources |
| :--: | ------- |
| 1 | Official UK government · UK Parliament |
| 2 | NHS / NICE / ONS |
| 3 | Major UK broadcasters / news outlets |
| 4 | Recognised trade bodies / construction publications |
| 5 | Established charities |
| 6 | Academic / research |
| 7 | Reputable trade media |
| 8 | Social / community — **lived experience only, never hard facts** |

Unknown source types default to tier 7 (usable for facts, but only just). Tier 8 can
never back a hard fact.

## Source claims

Each `source_claim` stores the attribution metadata the spec requires: source, title,
`claim_text`, `quoted_text`, `paraphrase`, `url`, `publication_date`, `accessed_at`,
`confidence_score`, `primary_or_secondary`, and a `fact_checked_status`.

## API

| Method & path | Purpose |
| ------------- | ------- |
| `GET /v1/sources` | list sources, best-credibility-first |
| `POST /v1/sources` | register a credible source |
| `GET /v1/sources/hierarchy` | the credibility hierarchy (for the UI) |
| `GET /v1/sources/{id}/claims` · `POST …/claims` | claims for a source |
| `POST /v1/factcheck` | apply the rule to a draft (+ optional `source_ids`) |

## Attribution in posts

Keep attribution short and uncluttered — `Source: ONS`, `According to BBC News…`,
`Government figures show…`. The fact-check verdict returns ready-made `Source: …`
lines; the spec's guidance is to show one clean attribution, never overload a video
with source clutter.
