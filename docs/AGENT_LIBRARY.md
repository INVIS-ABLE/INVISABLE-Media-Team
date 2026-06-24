# Agent Library

45 specialist agents across the departments. The **canonical source** is
[`core/invisable_os/agents/registry.py`](../core/invisable_os/agents/registry.py) —
it is real, callable code: `GET /v1/agents` lists them and `GET /v1/agents/route?task=…`
routes a task to the best-matched specialists.

Every agent's system prompt is prefixed with the shared `GUARDRAIL_PREAMBLE`, so the
Prime Directive, brand safety, originality, anti-fabrication, and the humour rules
travel with **every** call — an agent cannot be prompted out of the values.

## Roster (by department)

### Content
- **Creative Director** — Set the angle and standard for each brief; ensure variety and brand voice.
- **Hook Writer** — Write scroll-stopping opening lines that are honest, not clickbait.
- **Caption Writer** — Write platform-native captions in a warm, British, human voice.
- **Hashtag Specialist** — Choose relevant, non-spammy hashtags that reach the right community.
- **Storyteller** — Shape real, consented experiences into honest narrative arcs.
- **Educator** — Explain invisible illness clearly and accurately in plain English.
- **Founder Voice Agent** — Write in Stephen Garnham's genuine advocacy voice; never invent experiences.

### Creative
- **Humour Agent** — Add warm, self-deprecating, British humour; never punch down.
- **Meme Generator** — Create brand-safe trades / chronic-illness / community memes.
- **Story Arc Builder** — Turn one idea into a TikTok, Reel, carousel, quote card and founder take.

### Video / Production
- **Video Prompt Engineer** — Write prompts for Flux/Wan/Hunyuan/LTX and a shot/B-roll plan.
- **Voiceover Writer** — Write natural, spoken-word scripts for ElevenLabs narration.
- **Graphic Designer** — Brief quote cards and carousels for Canva/ComfyUI within brand style.
- **B-Roll Librarian** — Maintain libraries of sites, vans, tools, hospitals, offices, daily life.
- **Asset Librarian** — Catalogue and retrieve approved assets; enforce consent on real people.
- **Voice Library Agent** — Manage consented founder/ambassador/narrator voices for consistency.

### Research / Knowledge
- **Researcher** — Gather accurate, public, verifiable information on a topic.
- **Trend Analyst** — Identify genuine, relevant trends; never chase outrage.
- **NHS & Benefits Knowledge Agent** — Track PIP/ESA/NHS/employment-law changes; explain plainly; flag for review.
- **Construction Knowledge Agent** — Track tool-theft, safety, insurance and industry changes for trades.

### Intelligence
- **Competitor Intelligence Agent** — Track what comparable creators post and what resonates; learn, never copy.
- **Opportunity Scanner Agent** — Find podcasts, speaking, events, awards, sponsorships likely to fit.
- **Sponsor Opportunity Agent** — Surface sponsor/CSR opportunities with a fit score and outreach idea.

### Relationship
- **Relationship CRM Agent** — Maintain ambassador/partner contact history, interests, follow-ups.
- **Partner Growth Agent** — Track partners (CT1, GT Insurance, Bald Builders) and suggest joint campaigns.

### Growth
- **Viral Hook Librarian** — Save high-performing hooks and remix them into fresh, original openings.
- **Comment-to-Content Agent** — Turn genuine questions/objections in comments into helpful content.
- **Community Story Agent** — Categorise consented submitted stories and suggest formats.

### PR
- **Press/Media Agent** — Maintain journalist/podcast databases and suggest which story to pitch.
- **Press Release Generator** — Turn campaigns into accurate, media-ready releases.

### Analytics
- **Analytics Agent** — Read performance, find what genuinely resonated, feed learning back.
- **Repurposing Agent** — Identify top performers worth repurposing across formats.

### Automation
- **Scheduler Agent** — Sequence the approved queue across platforms and times.
- **Campaign Factory Agent** — Expand one topic into a full multi-format campaign with tags and CTAs.

### Governance (veto power)
- **Brand Guardian** — Hold veto power over anything off-brand, risky, or trust-damaging.
- **Compliance / Sensitivity Checker** — Check for ableism, hate, harassment, misinformation and policy risk.
- **Mission Alignment Agent** — Score every idea on awareness/community/fundraising/partner/long-term impact.
- **Quality Control Agent** — Score the 11 quality dimensions and send anything below bar back to improve.

### Remix, Parody & Trend Intelligence
- **Trend Scanner Agent** — Scan public sources and abstract them into clean trend signals — never copies.
- **Rights & Copyright Officer** — Classify every media item's rights status and block reuse of anything reference-only or unlicensed.
- **Parody Writer** — Write original, transformative parody inspired by a trend — never a copy, never punching down.
- **Reaction Script Writer** — Write reaction/commentary scripts and duet/stitch ideas where platform rules allow.
- **Voiceover Remix Agent** — Voiceover scripts over owned/licensed footage; spec the ElevenLabs + subtitle + FFmpeg job.
- **Pop Culture Curator** — Maintain the film/TV/meme/phrase index with paraphrase-safe versions and copyright risk.
- **Subtitle & Transcription Agent** — Whisper/auto-subtitle transcription, hook extraction, burned-in captions.

## Using an agent

```python
from invisable_os.agents import get_agent, route

route("write a funny tiktok hook about tool theft")   # → [Hook Writer, Humour Agent, …]
get_agent("Brand Guardian").system_prompt()           # full prompt, guardrails included
```
