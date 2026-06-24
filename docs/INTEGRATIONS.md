# Integrations

Outbound adapters in [`core/invisable_os/integrations/`](../core/invisable_os/integrations/).
Each is **graceful**: unconfigured or unreachable, it degrades to a dry-run/empty
result instead of raising, so the platform always runs offline and in CI. Clients
take an injectable `httpx.Client`, so the real request/response code is exercised via
`httpx.MockTransport` without network.

`GET /v1/integrations` reports what's configured.

## ResourceSpace — asset library (DAM)

Pushes a post's **finished** media (produced/assembled files) out of local disk into
a real Digital Asset Management system, so assets are catalogued, searchable and
shareable rather than living only under `data/`.

- `ResourceSpaceClient` implements the signed API (`/api/?function=…&sign=…`,
  `sign = sha256(private_key + query)`): `create_resource` → `upload_multipart`.
- `sync_post_to_dam(item_id)` uploads every **real** library asset for a post and
  records a `dam_ref` (with the ResourceSpace URL) against it. Assets that are still
  dry-run plans, or any that fail to upload, fall back to a dry-run `dam_ref` — one
  bad file never blocks the rest.

```bash
RESOURCESPACE_URL=… RESOURCESPACE_USER=… RESOURCESPACE_PRIVATE_KEY=… \
  invisable dam-sync <queue-item-id>
```
API: `POST /v1/dam/sync/{item_id}`.

## Metricool — metrics → Watchtower (the learning loop)

Closes the loop from *published* back to *smarter*: real post performance feeds the
Algorithm Watchtower, updating its learnings and the **Founder Recognition Index**,
which in turn nudge future scoring.

```
Metricool /analytics/posts  →  metricool_to_signals()  →  PerformanceSignal[]
   →  AlgorithmWatchtower.ingest()  →  learnings + Founder Recognition Index
   →  persisted via repository.record_signal()
```

- `MetricoolClient.fetch(start, end)` pulls post metrics (empty offline).
- `metricool_to_signals()` maps Metricool keys (shares, saves, comments, profile
  visits, followers, watch time, retention, website clicks) → our `SuccessMetric`
  vocabulary; unknown keys are ignored.
- `sync_metrics(...)` ingests them (from Metricool, or signals you pass directly),
  learns, persists, and returns the report incl. the Founder Recognition Index.

```bash
METRICOOL_API_TOKEN=… METRICOOL_BLOG_ID=… invisable metrics-sync
```
API: `POST /v1/metrics/sync` (body: `{}` to pull from Metricool, or
`{"signals": [...]}` to ingest directly). A nightly n8n workflow should call this so
the platform compounds what it learns each day.

### Per-post attribution — which posts earned the recognition

The Founder Recognition Index is a saturating function of *aggregate* recognition
metrics, so a post's contribution isn't simply its raw numbers.
`AlgorithmWatchtower.attribute_recognition()` computes each metric's contribution to
the index, then allocates it to posts in proportion to their share — an exact split
(per-post contributions sum back to the index) with a per-metric breakdown.

```
GET /v1/founder/recognition/by-post?limit=10
   → { index, attributed_posts, posts: [{ candidate_id, hook, platform,
                                          contribution, breakdown, metrics }] }
```

Surfaced in the dashboard's **Founder Recognition** view as "Top performing posts",
answering "which post drove the podcast invitations?". Empty until recognition-bearing
signals (media mentions, podcast/speaking invitations, partner/sponsor enquiries,
profile visits) are synced against published posts.

## Status & safety

| Integration | Configured by | Offline behaviour |
| ----------- | ------------- | ----------------- |
| ResourceSpace | `RESOURCESPACE_URL` + `_USER` + `_PRIVATE_KEY` | dry-run `dam_ref` |
| Metricool | `METRICOOL_API_TOKEN` + `_BLOG_ID` | no-op (0 signals) |

Secrets live in env vars only; both clients degrade rather than raise, so a missing
or down integration never takes the platform down.
