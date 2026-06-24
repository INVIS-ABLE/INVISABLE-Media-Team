# Values — encoded, not just declared

The single most important property of INVISABLE OS is that its values are enforced
in code. This document is the human-readable companion to
[`core/invisable_os/guardrails/`](../core/invisable_os/guardrails/).

## The Prime Directive

> If a decision increases reach but damages trust, **reject it**.
>
> If a decision increases awareness, trust, community value, and founder
> recognition simultaneously, **prioritise it**.

This is implemented two ways:

- **As a hard gate** — `guardrails.check()` blocks anything that trips a hard
  prohibition. A blocked candidate scores `0.0` and can never be published.
- **As weighted scoring** — `SCORE_WEIGHTS` tilt the composite toward trust and
  community value, so "more reach" can never win on its own.

## Optimise for

trust · awareness · authenticity · consistency · education · humour · community
value · long-term brand building

These map directly to the eight dimensions of the `ScoreCard`.

## Never optimise for

controversy · outrage · misinformation · spam · fake engagement · fake stories ·
fabricated testimonials · fabricated founder experiences

There is deliberately **no dimension** in the scorer for any of these. They cannot
be optimised because they are not measured as positives — and several are actively
blocked by tripwires.

## Never do

- copy copyrighted works,
- duplicate creator content,
- impersonate people without authorisation,
- fabricate stories, testimonials, or founder experiences.

The platform **may** learn patterns, structures, formats, audience reactions, and
content mechanics. The Intelligence Harvester therefore stores **abstracted
signals only** — topic, format, sentiment, opportunity — never verbatim creator
content.

## Community engagement rules

Commenting must be respectful, supportive, positive, constructive and authentic. It
must avoid spam, generic engagement bait, heart/kiss/flirtatious emoji, and
excessive emoji use. The `CommunityEngagement` engine drafts comments and will only
return one that passes the guardrails; comment-format content is held to a stricter
emoji limit.

## Founder recognition

Recognition is treated as a **consequence of impact**, never a goal pursued by
fabrication. The Founder Engine keeps founder presence at ~80% of published content
by *ordering real content*, and the Watchtower computes a Founder Recognition Index
from genuine outcomes (media mentions, podcast invitations, speaking and partner/
sponsor enquiries, profile visits).

## How to change the values

Edit [`guardrails/policy.py`](../core/invisable_os/guardrails/policy.py) — it is the
single source of truth, surfaced at runtime via `GET /v1/values`. Add a test in
`tests/test_guardrails.py` for any new prohibition. Never weaken a hard gate
without an explicit, recorded decision.
