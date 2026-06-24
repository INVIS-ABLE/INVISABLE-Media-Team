# Departments

INVISABLE OS is organised as a **media organisation**, not a toolbox. Each
department is a set of cooperating engines + agents + database tables, all sharing
`INVISABLE_BRAIN` and the same guardrails. This is what turns "a lot of content"
into "content that moves INVISABLE forward".

| Department | Engines (`core/invisable_os/engines/`) | Key agents | Tables |
| ---------- | -------------------------------------- | ---------- | ------ |
| 📝 **Content** | `tournament`, `generator`, `scoring` | Creative Director, Hook/Caption Writer, Educator, Storyteller, Founder Voice | `content_candidate`, `candidate_score` |
| 🎬 **Video / Production** | `flywheel` | Video Prompt Engineer, Voiceover Writer, Graphic Designer, B-Roll & Asset Librarian | `asset`, `person` |
| 🔎 **Research / Knowledge** | `harvester`, `cultural` | Researcher, Trend Analyst, NHS & Benefits Agent, Construction Knowledge Agent | `trend_signal`, `knowledge_item` |
| 📊 **Analytics** | `watchtower` | Analytics Agent, Repurposing Agent | `performance_signal`, `founder_recognition` |
| ⚙️ **Automation** | `daily` | Scheduler Agent, Campaign Factory Agent | `publish_decision` |
| 🕵️ **Intelligence** | `harvester` (+ competitor/opportunity models) | Competitor Intelligence, Opportunity Scanner, Sponsor Opportunity | `competitor`, `opportunity` |
| 🤝 **Relationship** | `tagging` | Relationship CRM, Partner Growth | `partner`, `relationship_touch`, `tag_network_member` |
| 🎯 **Growth** | `engagement` | Viral Hook Librarian, Comment-to-Content, Community Story | `hook_library`, `community_story` |
| 🎨 **Creative** | `personality` | Humour Agent, Meme Generator, Story Arc Builder | — |
| 🎤 **PR** | — | Press/Media Agent, Press Release Generator | `media_contact` |
| 🎭 **Remix, Parody & Trend Intelligence** | `remix` | Trend Scanner, Rights & Copyright Officer, Parody Writer, Reaction/Voiceover/Pop-Culture/Subtitle agents | `scanner_sources`, `scanned_items`, `media_assets`, `pop_culture_references`, `meme_formats`, `remix_jobs`, `extracted_hooks`, `subtitles` |
| 🏛️ **Governance** | `guardrails`, `mission`, `quality` | Brand Guardian, Compliance, **Mission Alignment**, Quality Control | `mission_score`, `risk_flag` |

> 🎭 The Remix department is a **rights-safe** trend scanner + parody/remix studio:
> it analyses, parodies, and transforms, but never downloads-and-reuploads other
> people's videos as-is. See [`REMIX_ENGINE.md`](REMIX_ENGINE.md).

## How a piece of content flows through the org

```
Research/Intelligence  →  surfaces a topic + abstracted signals
        │
Content (Tournament)   →  generates 100s, gates, scores, improves, selects
        │
Governance             →  Guardrails (hard gate) · Mission Advisor (5 impacts)
                          Quality Control (11 dims, must clear 8/10) · Brand Guardian veto
        │
Creative               →  personality + humour layer (laugh WITH us)
        │
Production (Flywheel)  →  one idea → TikTok, Reel, caption, quote card, carousel,
                          story poll, comment angle, future idea
        │
Relationship (Tagging) →  attach approved network tags (never outside the list)
        │
Automation (Daily)     →  schedule the day's 20 posts
        │
Analytics (Watchtower) →  learn from results → INVISABLE_BRAIN → smarter next cycle
```

## The two governance engines most creators don't have

- **Mission Advisor** (`mission.py`) — every idea is scored on awareness, community,
  fundraising, partner, and long-term mission impact, then given a verdict
  (`advance` / `hold` / `reject`). Long-term impact is weighted highest. *The most
  valuable engine in the platform.*
- **Quality Control** (`quality.py`) — the 11-dimension /10 rubric. Anything below
  the bar on any dimension goes back to be improved before it can enter the
  approval queue.

See [`ENGINES.md`](ENGINES.md) for the original engines and
[`AGENT_LIBRARY.md`](AGENT_LIBRARY.md) for every agent's brief.
