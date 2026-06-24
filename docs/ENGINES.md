# The Engines

Each engine is a real module in [`core/invisable_os/engines/`](../core/invisable_os/engines/).
They share `INVISABLE_BRAIN` and the `guardrails`.

## Content Tournament Engine — `tournament.py`

> Generate hundreds of candidates daily; score, improve, rank, and select only the
> highest-quality outputs.

Pipeline: **generate → guardrail gate → score → improve top contenders → re-score
→ rank (dedup) → select → rebalance for founder presence → remember winners.**

- Guardrails are the first gate and are absolute.
- Improvement targets a contender's *weakest value dimension* and always re-gates.
- Winners are written to the Brain as `winning_pattern` memories.

`POST /v1/tournament/run`

## Scorer — `scoring.py`

Turns the eight values into a number. Deterministic by default (fast at volume,
fully tested); an optional LLM pass can refine rationale. Reads
`performance_learning` memories so past results nudge future scores — bounded so no
single learning dominates the values.

## Generator — `generator.py`

Produces the field of candidates. LLM-driven at volume (Claude/Ollama), with safe,
original, deterministic templates offline. Eight structural *angles* (myth-vs-
reality, explainer, solidarity, gentle humour, founder voice, practical tip,
community prompt, reframe) ensure variety. Never fabricates founder experiences.

## Cultural Intelligence Engine — `cultural.py`

> British culture, humour, trades culture, football culture, social trends.

Scores **cultural resonance** (rewards natural British register, flags
Americanisms — plain English is never penalised) and supplies a cultural briefing
to the generator. Encodes *register and tone*, never stereotypes. Learns
`cultural_note` memories.

## Founder Engine — `founder.py`

> Keep founder presence at ~80% of published content.

Measures founder-centredness, reports the running balance vs. target, and
**proportionally** reorders the publishing queue so the running founder share
tracks the target (not 100%). Never fabricates founder content — it orders the real
content that exists.

## Algorithm Watchtower — `watchtower.py`

> Monitor platform performance; feed learning back into the Brain.

Ingests `PerformanceSignal`s, learns which themes drive genuine value (saves,
shares, story submissions), writes `performance_learning` memories, and computes
the **Founder Recognition Index** from recognition-bearing metrics using a
saturating transform so a single spike can't dominate.

`POST /v1/watchtower/ingest`

## Intelligence Harvester — `harvester.py`

> Monitor public sources, trend signals, creator content, discussions, opportunities.

Reduces everything to **abstracted signals** (topic, kind, summary, source_type) —
never verbatim creator content — and stores them as `trend_signal` memories.
Connectors (Firecrawl, Crawl4AI, Feedly, Google Trends, AnswerThePublic) plug in
behind `harvest()`.

`POST /v1/harvest`

## Community Engagement — `engagement.py`

Drafts supportive, constructive, professional comments and only returns ones that
pass the guardrails (stricter emoji limits for comments). Strengthens relationships
and represents INVISABLE® well; never farms reach.

`POST /v1/engagement/comment`

## Remix, Parody & Trend Intelligence Engine — `remix.py`

> Scan the internet, index culture, track trends, store references, and create
> **original** INVISABLE® content from them — a rights-safe remix studio, not a
> "steal and repost" machine.

Sub-systems: **TrendScanner** (six scan modes → abstracted `trend_signal`s),
**RightsManager** (conservative classification + yt-dlp download gating),
**PopCultureIndex** (paraphrase-safe references + meme formats), **ParodyEngine**
(original parody/skit/voiceover packs, brand-safety gated), **VoiceoverEngine**
(ElevenLabs + Whisper/auto-subtitle + FFmpeg job over *usable* footage only).

The **core rule** is enforced in [`guardrails/rights.py`](../core/invisable_os/guardrails/rights.py):
the system must never automatically download and reupload other people's videos
as-is. Only `owned`, `licensed`, `public_domain`, `creative_commons`,
`user_submitted_consent`, and `platform_duet_stitch` may enter video assembly;
`reference_only` can inspire ideas but is never reuploaded.

Full design: [`REMIX_ENGINE.md`](REMIX_ENGINE.md).

`POST /v1/scanner/scan` · `POST /v1/remix/create` · `POST /v1/voiceover/create` · `GET /v1/rights`
