# People, Consent & Relationship CRM

The Prime Directive forbids using a real person without authorisation. This makes
that rule operational: a durable consent store, a single consent gate in code, and
a Relationship CRM that nudges the founder to keep real relationships warm.

## The consent gate

A person is **usable** only when their consent is `approved` **and** not past its
`consent_expiry`. The one place that decision lives is
[`services/consent.py`](../core/invisable_os/services/consent.py) →
`consent_state(person)` → `{usable, reason, expired}` (`reason` is `ok`, `pending`,
`declined`, or `expired`). Every `/v1/people` response carries this verdict, and the
helper is the seam a future publish-time check calls once content carries an explicit
person link.

## API

| Method & path | Purpose |
| ------------- | ------- |
| `GET /v1/people` | Everyone the platform may feature, each with a live `consent` verdict |
| `POST /v1/people` | Add a person (defaults to `pending` consent) |
| `GET /v1/people/{id}` | One person + consent verdict (404 if unknown) |
| `POST /v1/people/{id}/consent` | Record/update consent: status, voice permission, allowed platforms/content types, expiry |
| `POST /v1/relationships/touch` | Log a contact with a partner/person + optional `follow_up_at` |
| `GET /v1/relationships/touches` | Touch history (filter by `partner_id` / `person_id`) |
| `GET /v1/relationships/followups` | Relationships due a follow-up on/before a date (default today) |
| `GET /v1/community/stories` | Consent-gated community submissions (filter by `status`) |
| `POST /v1/community/stories` | Submit a community story (defaults to `pending`) |
| `POST /v1/community/stories/{id}/consent` | Approve/decline a story before any social use |

## Workflow

The daily **Relationship Follow-ups** n8n workflow now calls
`GET /v1/relationships/followups` (was a placeholder that filtered partners by
status). It's read-only — it surfaces who is due a nudge; it never contacts anyone.

## Data

Stored in `person_row`, `relationship_touch`, and `community_story` (SQLite by
default, Postgres via `DATABASE_URL`), mirroring the canonical tables in
`db/schema.sql`. Domain models live in
[`models/departments.py`](../core/invisable_os/models/departments.py).

## Not yet (scoped follow-up)

Content candidates don't yet carry an explicit person link, so consent is enforced
at the data/CRM layer rather than auto-blocking a publish. When that link exists, the
publish path calls `consent_state` to hard-gate features of unconsented/expired
people — add a guardrail test before wiring it.
