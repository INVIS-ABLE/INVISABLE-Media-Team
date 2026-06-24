# Agent Library

77 specialist agents, organised as a **multi-agent production studio** of seven
pipeline teams. The **canonical source** is
[`core/invisable_os/agents/registry.py`](../core/invisable_os/agents/registry.py) —
it is real, callable code:

- `GET /v1/agents` lists every agent
- `GET /v1/agents/teams` groups them into the seven teams, in pipeline order
- `GET /v1/agents/route?task=…` routes a task to the best-matched specialists

Every agent's system prompt is prefixed with the shared `GUARDRAIL_PREAMBLE`, so the
Prime Directive, brand safety, originality, anti-fabrication, copyright/medical rules,
and the humour rules travel with **every** call — an agent cannot be prompted out of
the values. Each agent also notes it is *one small specialist in a larger studio*:
do one job well, return clean structured output for the next stage, trust the gates.

## The pipeline

```
research → strategy → writing → production → quality → publishing → learning
```

Each agent has a `department` (which part of the agency it belongs to) and a `team`
(which pipeline stage it serves). See
[`docs/PRODUCTION_STUDIO.md`](./PRODUCTION_STUDIO.md) for the full flow.

### 1. Research — scan the world, learn structures, never copy
Trend Scanner · News Scanner · Pop Culture Scanner · Meme Scanner · Creator Scanner ·
Invisible Illness Scanner · Trades Scanner · Algorithm Watcher · Researcher ·
Trend Analyst · NHS & Benefits Knowledge Agent · Construction Knowledge Agent ·
Competitor Intelligence Agent · Opportunity Scanner Agent · Sponsor Opportunity Agent

### 2. Strategy — pick the angle, position the founder, check fit
Creative Director · Founder Positioning Agent · Mission Alignment Agent ·
Culture Fit Agent · Platform Fit Agent

### 3. Writing — hooks, captions, scripts, CTAs
Hook Writer · Caption Writer · Script Writer · Voiceover Writer · One-Liner Writer ·
British Humour Writer · CTA Writer · Hashtag Writer · Storyteller · Educator ·
Founder Voice Agent

### 4. Production — build the assets
Video Builder · Video Prompt Engineer · Caption Renderer · Audio Cleaner ·
**Visual Layout Agent** · Thumbnail Agent · Carousel Builder · Story Builder ·
Meme Builder · Effects Agent · Graphic Designer · B-Roll Librarian · Asset Librarian ·
Voice Library Agent

### 5. Quality — gates; nothing ships that fails any gate
Brand Guardian · Copyright Risk Agent · Medical Risk Agent · Charity Reputation Agent ·
Sponsor Safety Agent · **Visual Obstruction Agent** · Audio Quality Agent ·
Caption Accuracy Agent · Platform Compliance Agent · Human Authenticity Agent ·
Compliance / Sensitivity Checker · Quality Control Agent

### 6. Publishing — approval, scheduling, amplification, recovery
Approval Queue Agent · Postiz Scheduler Agent · Story Amplification Agent ·
Content Recovery Agent · Founder Override Agent · Campaign Factory Agent

### 7. Learning — feed results back into `INVISABLE_BRAIN`
Analytics Agent · Performance Pattern Agent · Content Graveyard Agent ·
Winning Formula Agent · Founder Recognition Agent · Repurposing Agent ·
Viral Hook Librarian · Comment-to-Content Agent · Community Story Agent ·
Relationship CRM Agent · Partner Growth Agent · Press/Media Agent ·
Press Release Generator · Story Arc Builder

## Using an agent

```python
from invisable_os.agents import get_agent, route, by_team, pipeline, Team

route("write a funny tiktok hook about tool theft")   # → [Hook Writer, Humour…, …]
get_agent("Visual Layout Agent").system_prompt()      # full prompt, guardrails included
by_team(Team.QUALITY)                                 # every quality-gate specialist
pipeline()                                            # {Team: [Agent, …]} in order
```
