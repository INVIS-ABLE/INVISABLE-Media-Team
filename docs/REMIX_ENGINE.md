# Remix, Parody & Trend Intelligence Engine

> Find what people are talking about → understand the trend → create an
> INVISABLE®-safe version → generate script / voiceover / video plan → queue it for
> approval.

A large scanner + creative remix brain for INVISABLE®. It scans the internet for
current topics (construction, tool theft, trades humour, invisible illness,
autoimmune updates, pop culture, film quotes, meme formats, TikTok/Instagram
trends) and turns what it learns into **original** parody, reaction, voiceover,
meme, and skit content — always on-mission, always British, never punching down.

It is a **rights-safe remix engine, not a "steal and repost" machine.**

- Engine: [`core/invisable_os/engines/remix.py`](../core/invisable_os/engines/remix.py)
- Models: [`core/invisable_os/models/remix.py`](../core/invisable_os/models/remix.py)
- Rights guardrail: [`core/invisable_os/guardrails/rights.py`](../core/invisable_os/guardrails/rights.py)
- API: [`core/invisable_os/api/remix_routes.py`](../core/invisable_os/api/remix_routes.py)
- Tables: [`db/schema.sql`](../db/schema.sql) (`scanner_sources`, `scanned_items`,
  `media_assets`, `pop_culture_references`, `meme_formats`, `remix_jobs`,
  `extracted_hooks`, `subtitles`)

---

## The core rule (enforced in code)

> **The system must never automatically download and reupload other people's videos
> as-is.**

The system **may**: analyse public trends · store links as references · transcribe
*permitted* content for analysis · create original scripts inspired by a trend ·
create parody/commentary/reaction scripts · create voiceovers over
owned/licensed/permitted footage · use public-domain / Creative Commons / owned /
licensed / user-approved assets · suggest duet/stitch/reaction workflows where
platform rules allow.

This is not a slogan — it is the rights filter in
[`guardrails/rights.py`](../core/invisable_os/guardrails/rights.py), which every
asset passes through before it can enter production (mirrors how the Prime Directive
is enforced for content).

### Rights status system

Every media item carries exactly one `rights_status`:

| Status | May enter video assembly? | Meaning |
| ------ | :-----------------------: | ------- |
| `owned` | ✅ | Created by INVISABLE — use freely. |
| `licensed` | ✅ | Use within licence terms. |
| `public_domain` | ✅ | Use; store the source. |
| `creative_commons` | ✅ | Use per the CC licence terms (attribution where required). |
| `user_submitted_consent` | ✅ | Use per the submitted consent record. |
| `platform_duet_stitch` | ✅ | Use **only** through native platform features where allowed. |
| `reference_only` | ❌ | Analyse for ideas — **never** reuse as footage. |
| `blocked` | ❌ | Do not use in any form. |

A bare third-party link defaults to **`reference_only`** with high copyright risk,
so nothing is ever reusable unless explicit ownership/licence evidence elevates it.

```python
from invisable_os.guardrails import reuse_check, can_download
reuse_check(asset).passed          # False for reference_only / blocked
can_download(reference)            # yt-dlp gate — usable rights only
```

---

## The 15 PWA buttons (content modes)

Six **scan** modes return abstracted trend signals; nine **create** modes return
rights-safe creative packs.

| Scan | Create |
| ---- | ------ |
| Scan Trends | Create Parody · Create Reaction Video |
| Scan Construction | Create Voiceover Remix · Create Meme Batch |
| Scan Tool Theft | Create Trades Humour · Create Founder Skit |
| Scan Invisible Illness | Create Sponsor-Safe Version |
| Scan Autoimmune Updates | Create TikTok Trend Version |
| Scan Pop Culture | Create Instagram Reel Version |

```python
from invisable_os.engines.remix import RemixTrendEngine
from invisable_os.models.remix import ContentMode

engine = RemixTrendEngine()
engine.run(ContentMode.SCAN_TOOL_THEFT)                       # → trend items
engine.run(ContentMode.CREATE_PARODY, topic="tool theft and invisible illness")
```

---

## PWA screens

1. **Scanner Dashboard** — the scan buttons (construction, invisible illness,
   autoimmune, tool theft, pop culture, TikTok, Instagram).
2. **Reference Inbox** — scanned links/topics with title, source, topic, rights
   status, risk score and a *generate content* action.
3. **Rights Manager** — set each asset's status (owned / licensed / CC /
   public-domain / consented / reference-only / blocked).
4. **Remix Studio** — input topic/link/reference + platform + humour level + content
   type + voiceover style + partner + tag-network toggle → parody script, voiceover
   script, video shot list, caption, hashtags, tags, approval status.
5. **Pop Culture Index** — film/TV/meme/British sayings/viral phrases/trades &
   chronic-illness humour, each with a paraphrase-safe version and copyright risk.
6. **Asset Library** — owned videos, approved clips, founder/ambassador/partner
   assets, B-roll, voiceovers, subtitles, finished exports.
7. **Voiceover Queue** — script, selected voice, ElevenLabs status, generated audio,
   subtitle status, export status.

> **Live in the dashboard.** All seven screens are implemented as tabs in the
> installable PWA ([`core/invisable_os/web`](../core/invisable_os/web)): **Scanner
> Dashboard**, **Reference Inbox**, **Remix Studio**, **Rights Manager**, **Pop
> Culture Index**, **Voiceover Queue**, and **Asset Library**. They are wired to this
> API: `GET /v1/remix/modes`, `POST /v1/scanner/scan`, `POST /v1/scanner/manual-link`,
> `GET /v1/scanner/items`, `POST /v1/remix/create`, `GET /v1/rights`,
> `GET|POST /v1/rights-assets`, `GET|POST /v1/popculture`, `GET /v1/meme-formats`, and
> `POST /v1/voiceover/create`. The Inbox's *generate content* button hands a reference
> straight into the Remix Studio; the Voiceover Queue only offers usable-rights assets
> and shows the ElevenLabs + subtitle + FFmpeg job it builds.

---

## Workflows

| # | Workflow | Engine entry point |
| - | -------- | ------------------ |
| 1 | **Scan → Idea** (summarise, tag, score, store, suggest 5 angles) | `scan_to_ideas`, `suggest_angles` |
| 2 | **Reference video → Parody** (mark `reference_only`, inspire original) | `reference_to_parody` |
| 3 | **Owned clip → Voiceover video** (rights-confirm → ElevenLabs → Whisper → FFmpeg) | `VoiceoverEngine.build` |
| 4 | **Pop culture → INVISABLE® version** (copyright check → paraphrase-safe) | `pop_culture_to_version` |
| 5 | **Construction news → Content** (serious / humour / banter / tie-in / sponsor-safe) | `construction_news_to_content` |

### Parody workflow (the creative core)

1. Analyse the trend. 2. Identify what makes it funny/viral. 3. Create an *original*
INVISABLE® version. 4. Avoid direct copying. 5. Add British humour. 6. Add the
invisible-illness / trades angle. 7. Check brand safety (the hard gate).
8. Send to the approval queue.

**Example** — input *"Make a parody about tool theft and invisible illness"* →
output a pack with a 15-sec TikTok script, a 30-sec Reel script, a voiceover
version, a skit version, caption, hashtags, tags, required visuals, **rights-safe**
asset suggestions, and a risk score.

---

## Tool pool

| Stage | Tools |
| ----- | ----- |
| Scanning / discovery | [Feedly](https://feedly.com), [Google Trends](https://trends.google.com), [AnswerThePublic](https://answerthepublic.com), [Reddit](https://www.reddit.com), [Perplexity](https://www.perplexity.ai) |
| Video / reference handling | [yt-dlp](https://github.com/yt-dlp/yt-dlp) *(permitted/licensed material only)*, [FFmpeg](https://ffmpeg.org), [Whisper](https://github.com/openai/whisper), [auto-subtitle](https://github.com/m1guelpf/auto-subtitle) |
| Asset database / index | [ChromaDB](https://www.trychroma.com), [PostgreSQL](https://www.postgresql.org), [AtroDAM](https://github.com/atrocore/atrodam) |
| Posting | [Metricool](https://metricool.com), [TikTok Content Posting API](https://developers.tiktok.com/doc/content-posting-api-get-started), [Instagram Content Publishing API](https://developers.facebook.com/docs/instagram-platform/content-publishing/) |

> yt-dlp supports thousands of sites; the system uses it **only** where rights/terms
> allow (owned, licensed, public-domain, Creative Commons, consented, or
> platform-permitted material). FFmpeg trims/crops/resizes/converts/subtitles/
> assembles; Whisper transcribes and surfaces hooks; AtroDAM (GPLv3) manages the
> digital assets and derivatives.

---

## API

All under `/v1` (see `/docs` once `invisable serve` is running):

```
GET   /rights                      # the rights system + the copyright rule
POST  /rights/check                # gate a set of assets/references before reuse
POST  /scanner/source              # register a scanner source
GET   /scanner/sources
POST  /scanner/scan                # run a scan mode → reference inbox
GET   /scanner/items               # the reference inbox
POST  /scanner/manual-link         # add a link/topic → rights + 5 angles
GET   /remix/modes                 # the 15 buttons
POST  /remix/create                # run any create mode; queues a remix job
POST  /remix/scan-to-ideas         # "Scan tool theft today" command
POST  /remix/reference-to-parody   # Workflow 2
POST  /remix/construction-news     # Workflow 5
POST  /remix/pop-culture           # Workflow 4
GET   /remix/jobs   ·  POST /remix/jobs/{id}/{action}
POST  /rights-assets  ·  GET /rights-assets  ·  PATCH /rights-assets/{id}/rights
POST  /voiceover/create            # voiceover over an APPROVED asset (gated)
POST  /export/video-plan           # rights-safe FFmpeg assembly plan
GET   /popculture   ·  POST /popculture
GET   /meme-formats ·  POST /meme-formats
```

## CLI

```bash
invisable scan scan_tool_theft                       # run a scanner
invisable remix create_parody --topic "tool theft"   # run a create mode
invisable seed-popculture                            # seed the pop-culture index
```

---

## Brand humour rule

Humour can be self-deprecating and British. It can joke about the founder's own
experiences, body, health chaos, van life, trades chaos, tool theft, bureaucracy,
and life being ridiculous. It must **never** punch down, use slurs, use racism, mock
disabled people or illness sufferers as a group, or target vulnerable people — the
same line enforced by the humour guardrails. The goal is to make INVISABLE® funny,
sharp, human and relatable, **not cruel**.
