# n8n Workflow Map

n8n is the orchestration spine. Each workflow calls the `core` API
(`{{$env.INVISABLE_CORE_URL}}` = `http://core:8080`), which holds all the logic. The
already-shipped daily cycle lives at [`n8n/workflows/daily_content_cycle.json`](../n8n/workflows/daily_content_cycle.json).

## Core workflows

### 1. Daily Content Cycle  *(shipped)*
```
schedule 07:00
  → POST /v1/harvest            (Intelligence: abstracted signals)
  → POST /v1/daily/plan         (20 posts, each gated/scored/spun)
  → IF selected > 0
      → fan out winners → approval queue (PWA)
      → (on approve) Scheduler → Postiz/Metricool
```

### 2. Scanner Sweep  *(hourly)*
```
schedule :17 hourly
  → POST /v1/harvest  {topics: [invisible illness, trades, tool theft, benefits, trends]}
  → store abstracted signals; raise opportunities (podcasts/speaking/sponsors)
```

### 3. Comment-to-Content  *(every 30 min)*
```
poll platform comments/DMs (Composio)
  → cluster questions/objections/confusion
  → POST /v1/agents/route?task=comment...   (Comment-to-Content Agent)
  → draft FAQ / reply video briefs → approval queue
```

### 4. Nightly Learning  *(23:40)*
```
pull platform metrics (Metricool)
  → POST /v1/watchtower/ingest   (learn themes, update Founder Recognition Index)
  → write learnings to INVISABLE_BRAIN (auto, inside core)
```

### 5. Campaign Factory  *(on demand / webhook)*
```
webhook {topic e.g. "tool theft" | "CT1 advert"}
  → POST /v1/daily/plan or /v1/tournament/run per format
  → produce 5 TikToks, 5 Reels, 2 carousels, 2 stories, partner-safe + humour + founder + press versions
  → tag list (/v1/agents) + Brand Guardian + Mission/Quality gates
  → approval queue
```

### 6. Media Production  *(triggered by approved video briefs)*
```
approved brief
  → 5090 machine: ComfyUI (Flux image / Wan|Hunyuan|LTX video)
  → ElevenLabs voiceover
  → Whisper captions
  → OpenCut assembly → ResourceSpace
  → back to approval queue with rendered asset
```

### 7. Relationship Follow-ups  *(daily 09:03)*
```
query relationship_touch.follow_up_at <= today
  → notify founder via PWA: "Follow up with X (last contact …)"
```

## Conventions

- Every workflow is **read-mostly against the core API**; the core owns the rules.
- Nothing publishes without passing through the **approval queue** (human gate).
- Secrets live in n8n credentials / env vars, never in workflow JSON.
- Uptime Kuma monitors each workflow's health webhook; Watchtower keeps images current.
