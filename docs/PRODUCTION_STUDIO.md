# Multi-Agent Production Studio

INVISABLE® OS is not one all-powerful AI. It is a **studio of many small, sharp,
single-job specialists**, wired into a pipeline where every output is checked by
quality gates before a human ever sees it.

> Small agents. Clear jobs. Fast decisions. Strict checks. Human approval where needed.

## The pipeline

```
research → strategy → writing → production → quality → publishing → learning
```

Each stage is a **team** of specialists. Output flows down the pipeline as structured
data; the Quality team gates everything; only clean, polished, high-scoring,
mission-aligned content reaches the approval queue.

The roster is real, callable code in
[`core/invisable_os/agents/registry.py`](../core/invisable_os/agents/registry.py).
Every agent's system prompt is prefixed with the shared `GUARDRAIL_PREAMBLE`, so the
Prime Directive and brand/medical/copyright rules travel with **every** call — an
agent cannot be prompted out of the values.

| Team | What it does | Example specialists |
|------|--------------|---------------------|
| **Research** | Scan the world, learn structures, never copy | Trend / News / Pop Culture / Meme / Creator / Invisible Illness / Trades Scanner, Algorithm Watcher |
| **Strategy** | Pick the angle, position the founder, check fit | Creative Director, Founder Positioning, Mission Alignment, Culture Fit, Platform Fit |
| **Writing** | Words: hooks, captions, scripts, CTAs | Hook / Caption / Script / Voiceover / One-Liner / British Humour / CTA / Hashtag Writer |
| **Production** | Build the assets | Video Builder, Caption Renderer, Audio Cleaner, **Visual Layout Agent**, Thumbnail, Carousel, Story, Meme, Effects |
| **Quality** | Gates — nothing ships that fails any gate | Brand Guardian, Copyright/Medical/Sponsor Risk, **Visual Obstruction**, Audio Quality, Caption Accuracy, Platform Compliance, Human Authenticity |
| **Publishing** | Approval, scheduling, amplification, recovery | Approval Queue, Postiz Scheduler, Story Amplification, Content Recovery, Founder Override |
| **Learning** | Feed results back into `INVISABLE_BRAIN` | Analytics, Performance Pattern, Content Graveyard, Winning Formula, Founder Recognition |

**API:** `GET /v1/agents/teams` returns the whole studio grouped by team in pipeline
order. `GET /v1/agents/route?task=…` routes a free-text task to the best specialists.

## Content creation flow

1. **Intelligence Harvester** scans web/social/trends (Crawl4AI / Firecrawl).
2. **Pattern Extractor** stores *structures*, never copied content.
3. **Content Tournament** generates 300–1000 candidate ideas.
4. **Strategy** agents rank the ideas.
5. **Writing** agents produce scripts / captions / hooks.
6. **Founder Engine** decides whether Stephen's voice/image/video is needed (target 80%).
7. **Production** agents build draft assets.
8. **Quality** agents check every output — including the Video Quality Gate.
9. Failed content is **repaired or rejected** (Content Recovery Agent).
10. Best content goes to the **approval queue**.
11. Approved content goes to **Postiz**.
12. **Algorithm Watchtower** tracks results.
13. **Learning** agents feed results back into `INVISABLE_BRAIN`.

### Daily volume target

| Stage | Count |
|-------|-------|
| Candidates generated | 500–1000 |
| Shortlisted | 100 |
| Drafts produced | 40–60 |
| Approved | 20–40 |
| Published | per schedule |

The 5090 box can generate thousands of raw assets — but only the best are published.

---

## The Visual Layout Agent (the headline upgrade)

This is what separates *"AI content spam"* from *proper media team output*. It stops
the studio shipping captions over faces, text under the TikTok buttons, or graphics
jammed into the platform UI.

It is **deterministic geometry** — normalised coordinates (`[0,1]`, origin top-left)
— so it needs no GPU and is fully testable. Heavy detectors (OpenCV/YOLO faces, OCR
text, logo detection) feed it a list of protected `Region` boxes; the placement
solver then finds a spot for each caption/overlay that clears the platform UI **and**
the protected regions — or reports exactly what it could not avoid.

Code: [`core/invisable_os/media/safe_area.py`](../core/invisable_os/media/safe_area.py).

### Safe-area templates

Each platform/surface has a template with **UI exclusion zones** (where the platform
paints its own chrome) and an inner **title-safe** box where our text belongs.

For 9:16 video the agent keeps captions and important graphics away from:

- the top UI / status area
- the bottom caption / CTA / creator-handle band
- the right-side action rail (like / comment / share / icons)
- anything outside the title-safe margin (too close to the edge)

Templates ship for TikTok Reel, Instagram Reel, YouTube Short, Instagram Story,
Instagram Feed and Carousel. `GET /v1/safe-area?platform=tiktok&surface=reel` returns
one as JSON.

### Placement solver

```python
from invisable_os.media.safe_area import VisualLayoutAgent, get_template, Region, RegionKind, Box, Surface
from invisable_os.models.content import Platform

t = get_template(Platform.TIKTOK, Surface.REEL)
face = Region(RegionKind.FOUNDER_FACE, Box(0.25, 0.55, 0.75, 0.85), label="stephen")
placement = VisualLayoutAgent().place_caption(t, height=0.12, regions=[face])
# → caption auto-moves above the face, inside the title-safe area, off the UI rail.
```

`POST /v1/layout/place-caption` exposes the same thing over HTTP.

---

## The Video Quality Gate

No video reaches the approval queue until it clears the gate. It runs the full
pre-approval checklist over a structured `VideoSpec`. The heavy probes that build that
spec (FFmpeg, Whisper, OpenCV/YOLO, OCR) sit behind the `VideoProbe` seam and degrade
to a dry-run when their binaries aren't installed — exactly like the renderers.

Code: [`core/invisable_os/media/video_qc.py`](../core/invisable_os/media/video_qc.py).
API: `POST /v1/video/qc`.

| Requirement | Check |
|-------------|-------|
| correct aspect ratio | `aspect_ratio` |
| correct resolution | `resolution` |
| good frame rate | `framerate` |
| sensible duration | `duration` |
| loudness normalised | `loudness` |
| no audio clipping | `audio_clipping` |
| no overlapping audio | `overlapping_narration` |
| voice clear over music | `voice_music_balance` |
| no unlicensed music risk | `music_licence` |
| valid (non-broken) subtitles | `subtitles_valid` |
| no badly-timed captions | `caption_timing` |
| no duplicated captions | `caption_duplication` |
| subtitles match speech | `caption_accuracy` |
| no captions over faces/objects/on-screen text | `visual_obstruction` |
| nothing under the platform UI | `platform_ui_clear` |
| no text too close to the edge | `edge_safe` |
| no blurry output | `sharpness` |
| no visual clutter | `visual_clutter` |
| generation models cleared for commercial use | `model_licence` |

A check is `pass`, `warn` (surfaced, non-blocking) or `fail` (blocks the gate). The
report lists failures and warnings:

```python
from invisable_os.media.video_qc import VideoQualityGate, VideoSpec
report = VideoQualityGate().check(VideoSpec(...))
report.passed          # False if any check failed
report.summary()       # {"passed": ..., "failures": [...], "warnings": [...], "checks": [...]}
```

### Where the real probes plug in

The gate is pure logic; the detectors are the integration seam
([`media/probes.py`](../core/invisable_os/media/probes.py)). Each follows the renderer
idiom — **use the real tool when it's installed, else pass the spec through as a
dry-run** — so the pipeline runs anywhere and only measures for real on the GPU box:

- **FFmpeg** → container (w/h/fps/duration) via `ffprobe`, loudness + true peak via
  `ebur128`. ✅ wired (`FFmpegProbe`).
- **Whisper / faster-whisper** → transcript + caption cues for accuracy & timing.
  ✅ wired (`WhisperProbe`).
- **OpenCV / YOLO (Ultralytics)** → faces, hands/tools/products, logos → `Region`s. *(seam ready)*
- **OCR (PaddleOCR / Tesseract)** → on-screen text regions → `Region`s. *(seam ready)*

```python
from invisable_os.media.probes import probe_video
from invisable_os.media.video_qc import VideoQualityGate

spec = probe_video("render.mp4")          # FFmpeg+Whisper fill in w/h/fps/loudness/captions
report = VideoQualityGate().check(spec)    # …then the gate runs on the measured spec
```

`POST /v1/video/probe` exposes the same `probe → gate` flow over HTTP for a
server-local path. The parsing (`parse_ffprobe`, `parse_ebur128`) is pure and
unit-tested against captured tool output, so it's verified even without the binaries.

See [TOOL_INTEGRATION_REVIEW.md](./TOOL_INTEGRATION_REVIEW.md) for the licence,
security, maintenance and Docker assessment of each, and whether to integrate it
directly or only use it as inspiration.

### The generation-model licence gate

Footage provenance (owned / licensed / CC / reference-only) is gated by the Remix
department's `reuse_check` ([`guardrails/rights.py`](../core/invisable_os/guardrails/rights.py)).
A **different axis** matters for AI-generated assets: *does the model's licence permit
commercial use?* FLUX.1 [dev] is non-commercial; **HunyuanVideo's community licence
excludes the UK/EU**; Ultralytics YOLO is AGPL. That axis is gated by
[`guardrails/model_licensing.py`](../core/invisable_os/guardrails/model_licensing.py):

- a registry of generation/detector models → commercial-use permission;
- **fail-closed** — an unknown model is blocked until a human registers it;
- wired into the Video Quality Gate as the `model_licence` check (set
  `VideoSpec.generation_models` to the models that built the clip);
- `GET /v1/licensing/models` and `POST /v1/licensing/check` expose it directly.

```python
from invisable_os.guardrails.model_licensing import licence_check
licence_check(["flux-schnell", "wan2.1"])     # passed=True
licence_check(["flux-dev"]).blocked           # ["FLUX.1 [dev]"] — non-commercial
```

This is the enforcement the tool review recommends: the Copyright Risk Agent blocks any
asset produced by a non-commercial model before it can reach approval.
