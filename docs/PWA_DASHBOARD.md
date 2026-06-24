# PWA Dashboard Layout

A single installable progressive web app (phone · iPad · PC · browser), talking only
to the `core` API. It is the founder's cockpit: approve, regenerate, schedule, and
see the whole org at a glance.

## Navigation (left rail)

```
🏠 Today            🗂️ Queues           🧠 Intelligence      🤝 Relationships
   • 20-post plan      • Approval           • Trend radar         • Ambassador CRM
   • Generate 20       • Rejected           • Scanner results     • Partner growth
   • Mission scores    • TikTok             • Competitor intel    • Tag network
   • Regenerate        • Instagram          • Opportunities       • People & consent
                       • Reels / Stories
                       • Carousels

🎬 Studio           📚 Knowledge         📊 Analytics         🏛️ Governance
   • Campaign builder   • NHS & benefits     • Growth             • Mission dashboard
   • Flywheel view      • Construction       • Founder Recognition• Quality scores
   • Asset library      • Hook library         Index              • Risk flags
   • B-roll / voices    • Content DNA        • Watch time/saves   • Content graveyard
```

## Today (home)

The default screen. Shows the day's 20-post plan from `POST /v1/daily/plan`:

```
┌──────────────────────────────────────────────────────────────────┐
│  Today · 20 posts          [ Generate today's 20 ]  [ Scan now ]   │
├──────────────────────────────────────────────────────────────────┤
│  ▸ humour · TikTok            mission 0.41  quality 7.8 ⚠ improve   │
│    "My immune system called in sick before I did."                 │
│    assets: 7   tags: 3   [approve] [regenerate] [schedule]         │
│  ▸ education · Carousel       mission 0.52  quality 8.4 ✓           │
│    "But you don't look ill."                                        │
│    assets: 7   [approve] [regenerate] [schedule]                   │
│  ▸ founder · Reel             mission 0.61  quality 8.1 ✓  👤        │
│    "Why I started INVISABLE."                                       │
│  …                                                                 │
└──────────────────────────────────────────────────────────────────┘
```

Each card surfaces: pillar, platform, **mission verdict**, **quality average**, a
⚠ flag if any dimension is below 8/10, an advisory badge if it needs human review
(medical/legal/benefits/sponsor/copyright), founder badge, asset count, and tags.

## Key screens → API

| Screen | Endpoint |
| ------ | -------- |
| Generate today's 20 | `POST /v1/daily/plan` |
| Run one campaign | `POST /v1/tournament/run` |
| Mission score an idea | `POST /v1/mission/advise` |
| Quality score an idea | `POST /v1/quality/score` |
| Flywheel a winner | `POST /v1/flywheel/spin` |
| Guardrail / risk check | `POST /v1/guardrails/check` |
| Draft a comment | `POST /v1/engagement/comment` |
| Personality mix | `GET /v1/personality/mix` |
| Agent library / router | `GET /v1/agents`, `/v1/agents/route` |
| Brain learning stats | `GET /v1/brain/stats` |
| Values | `GET /v1/values` |

## Core interactions

- **Approve** → moves to the scheduler queue.
- **Regenerate** → re-runs the slot's tournament; the rejected version drops to the
  Content Graveyard so the platform learns not to repeat it.
- **Schedule** → hands to Postiz/Metricool via n8n.
- Everything is **mission- and quality-first**: the founder sees *why* a post is
  worth publishing, not just the post.

## Build notes

- PWA shell (installable, offline-capable read views, push for approvals).
- Auth behind Cloudflare Access; the API behind the Tunnel.
- The dashboard ships separately; this repo provides the **API contract** above.
