# Scheduling & the Media Pipeline

Two capabilities borrowed (as patterns) from the best self-hosted schedulers and
wired to our queue. See [`REFERENCES.md`](REFERENCES.md) for licences.

## Posting-slot queue (the consistency engine)

The signature feature of Buffer/Postiz/Mixpost: define a **weekly schedule of
posting slots per channel once**, then "fill the next free slot" automatically. This
is how the brand stays *consistent* — one of INVISABLE's core values — without
anyone choosing a time for every post.

```
Channel  ── has many ──►  ScheduleSlot (weekday + time, recurring weekly)

approve an item  →  schedule_next(item)  →  finds the earliest free slot for that
                                            platform's channel that isn't taken
                                         →  sets scheduled_at + status=scheduled
publish runs     →  publishes items whose scheduled_at has arrived
```

- `scheduling/engine.py` `next_open_slot()` computes the slot in the channel's
  timezone (via `zoneinfo`) and returns aware UTC; it skips already-taken slots so
  two posts never collide.
- `scheduling/defaults.py` seeds a sensible **Mon–Fri × 3-slots/day** schedule at
  deliberately off-the-hour times (08:07, 12:33, 17:47) — the "don't post on the
  hour like everyone else" trick these tools use.

```bash
invisable seed-channels   # 2 channels + default weekly schedule
invisable plan --persist  # 20 posts into the queue
# (approve some items)
invisable schedule        # fill the next open slots
invisable calendar        # see them laid out by day
```

API: `POST /v1/channels` (creates a default schedule), `POST /v1/channels/{id}/slots`,
`POST /v1/queue/{id}/schedule-next`, `GET /v1/calendar`.

## Media pipeline (closing the loop: idea → finished asset)

The Content Flywheel produces **asset specs** (a TikTok, a quote card, a voiceover…).
The media pipeline renders them into the **media library**, ready for approval.

```
queue item → MediaProducer → for each flywheel asset spec, the first capable
                             renderer produces it:
   ComfyUI (Flux image / Wan·Hunyuan·LTX video)  →  tiktok, reel, quote_graphic, carousel
   ElevenLabs                                     →  voiceover
   Whisper                                        →  captions
   passthrough                                    →  story_poll, comment_response (text)
                          → records each asset in the library (path + backend)
```

Every renderer **degrades to dry-run** (records a placeholder, never fails) so the
pipeline runs offline and on a GPU-less server. Configure `COMFYUI_BASE_URL`,
`ELEVENLABS_API_KEY`, etc. to render for real.

```bash
invisable produce <queue-item-id>     # render that item's assets
```

API: `POST /v1/media/produce/{id}`, `GET /v1/media?item_id=…`.

## End-to-end operational loop

```
seed-channels → plan --persist → (approve) → schedule → produce → publish
     │              │                │           │          │         │
  channels +    20 posts in      human OK    next free   render    dry-run
  slots         the queue                    slot/day    assets    or Postiz
```
