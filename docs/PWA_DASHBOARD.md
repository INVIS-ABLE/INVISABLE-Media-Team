# PWA Dashboard Layout

A single installable progressive web app (phone · iPad · PC · browser), talking only
to the `core` API. It is the founder's cockpit: approve, regenerate, schedule, and
see the whole org at a glance.

> **Built and shipped.** A dependency-free PWA lives in
> [`core/invisable_os/web/`](../core/invisable_os/web/) and is served by the API at
> **`/app`** (run `invisable serve`, open <http://localhost:8080/app>). It is
> installable (manifest + service worker, offline app-shell) and implements the
> Today / Queue / Calendar / Media / Agents / Values screens against the endpoints
> below. The richer screens in this document are the forward design; what's built
> today is the working core of it.

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

## 🎭 Remix, Parody & Trend Intelligence

A rights-safe scanner + remix studio. **Core rule:** the system analyses, parodies,
and transforms — it never downloads-and-reuploads other people's videos as-is.
Full design in [`REMIX_ENGINE.md`](REMIX_ENGINE.md).

### Screens

| Screen | What it does | API |
| ------ | ------------ | --- |
| **Scanner Dashboard** | The scan buttons (construction · invisible illness · autoimmune · tool theft · pop culture · TikTok · Instagram) | `POST /v1/scanner/scan`, `GET /v1/remix/modes` |
| **Reference Inbox** | Scanned links/topics: title, source, topic, rights status, risk score, *generate* | `GET /v1/scanner/items`, `POST /v1/scanner/manual-link` |
| **Rights Manager** | Set each asset's status (owned/licensed/CC/public-domain/consented/reference-only/blocked) | `GET /v1/rights-assets`, `PATCH /v1/rights-assets/{id}/rights`, `GET /v1/rights` |
| **Remix Studio** | Topic/link/reference + platform + humour + type + voice + partner → parody/voiceover/shot-list/caption/hashtags/tags | `POST /v1/remix/create` |
| **Pop Culture Index** | Film/TV/meme/sayings/phrases with paraphrase-safe versions + copyright risk | `GET/POST /v1/popculture`, `GET/POST /v1/meme-formats` |
| **Asset Library** | Owned/approved source clips, founder/ambassador/partner assets, B-roll, voiceovers, subtitles (rights-classified) | `GET /v1/rights-assets` |
| **Voiceover Queue** | Script · voice · ElevenLabs status · audio · subtitle status · export status | `POST /v1/voiceover/create` |
| **✅ Gate** | Run a clip spec through the Video Quality Gate; see every check pass/warn/fail, plus the generation-model licence registry (commercial vs blocked) | `POST /v1/video/qc`, `GET /v1/licensing/models` |

### The 15 buttons

`Scan Trends · Scan Construction · Scan Tool Theft · Scan Invisible Illness · Scan
Autoimmune Updates · Scan Pop Culture` (scan) — `Create Parody · Reaction Video ·
Voiceover Remix · Meme Batch · Trades Humour · Founder Skit · Sponsor-Safe Version ·
TikTok Trend Version · Instagram Reel Version` (create).

Every reference defaults to **reference_only** (inspiration only). Generated media
may use only `owned / licensed / public_domain / creative_commons /
user_submitted_consent / platform_duet_stitch` assets — enforced server-side.

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
