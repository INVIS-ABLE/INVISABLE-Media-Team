# Tool / Repo Integration Review

PROMPT 8 names ten open-source tools as the integration layer for the production
studio. This is the review the directive asks for: each is assessed for **licence,
security, active maintenance, Docker compatibility, API compatibility**, and whether
it should be **integrated directly** or **used only as inspiration**.

> ⚠️ **Verify before you ship.** Licences and maintenance status change. The notes
> below reflect the state of these projects as of the knowledge cutoff (Jan 2026) and
> must be re-checked at integration time. Several carry **commercial-use conditions**
> that matter for INVISABLE® as a revenue-generating media agency — those are flagged
> 🚩. When in doubt, get the licence confirmed by a human before integrating.

## Verdict at a glance

| # | Tool | Role | Licence (verify) | Verdict |
|---|------|------|------------------|---------|
| 1 | **Postiz** | Scheduling / publishing | AGPL-3.0 🚩 | **Integrate** (service over API) |
| 2 | **Mixpost** | Backup scheduler | Lite: MIT · Pro: paid | **Integrate optional / study** |
| 3 | **OpenShorts** | AI shorts pipeline | Verify 🚩 | **Inspire** (verify before integrating) |
| 4 | **Short Video Maker** | Lightweight shorts | MIT (but Remotion dep 🚩) | **Integrate w/ caveat** |
| 5 | **FFmpeg** | Core rendering | LGPL-2.1 / GPL build 🚩 | **Integrate** (core) |
| 6 | **Whisper / faster-whisper** | Transcription / captions | MIT | **Integrate** (core) |
| 7 | **Crawl4AI** | AI-ready crawling | Apache-2.0 | **Integrate** |
| 8 | **Firecrawl** | Web→RAG ingestion | AGPL-3.0 🚩 / cloud API | **Integrate** (API or self-host) |
| 9 | **ComfyUI + Flux/Wan/Hunyuan/LTX** | Image/video gen | ComfyUI GPL-3.0 · **models vary** 🚩 | **Integrate** (mind model licences) |
| 10 | **OCR/vision: PaddleOCR, Tesseract, OpenCV, YOLO** | Visual safety/QC | Apache/Apache/Apache · **Ultralytics AGPL** 🚩 | **Integrate** (swap YOLO licence) |

Most of these are **already referenced** in the codebase as renderer/probe backends
([`media/renderers.py`](../core/invisable_os/media/renderers.py),
[`media/video_qc.py`](../core/invisable_os/media/video_qc.py)) and degrade to dry-run
until configured — so integration is "wire the backend", not "rebuild the seam".

---

## 1. Postiz — scheduling / publishing layer
- **Licence:** AGPL-3.0. 🚩 AGPL's network-use clause means if you modify Postiz and
  expose it as a network service, you must offer your modified source. **Running it
  unmodified, and calling it as a separate service over its API, keeps our codebase
  at arm's length** — that's the recommended posture.
- **Maintenance:** active, well-starred, frequent releases.
- **Docker:** first-class `docker compose` deployment.
- **API:** REST API for accounts, channels and scheduled posts.
- **Verdict: integrate** as the scheduling/publishing layer — but as an external
  service we call, not a library we fork. This is the `Postiz Scheduler Agent`'s
  backend. Keep our publishing abstraction (`publish/`) in front of it so Mixpost can
  swap in.

## 2. Mixpost — alternative / backup scheduler
- **Licence:** *Mixpost Lite* is open-source (MIT); *Mixpost Pro* is a paid product.
  Confirm which edition you deploy.
- **Maintenance:** active (Laravel/PHP).
- **Docker:** official images.
- **API:** available (broader in Pro).
- **Verdict: optional integrate / study.** Good failover if one part of the Postiz
  stack doesn't suit. Because we already abstract publishing behind `publish/base.py`,
  adding a Mixpost adapter is low-cost. Don't run both as primary — pick one,
  keep the other warm.

## 3. OpenShorts — AI shorts/video pipeline base
- **Licence:** 🚩 **verify** — less established than the others; confirm the licence,
  ownership and that it isn't wrapping paid third-party APIs you'd inherit.
- **Maintenance:** verify activity and issue responsiveness before depending on it.
- **Docker / API:** verify.
- **Verdict: inspire first.** Study its clip-generation and auto-publish flow for
  ideas, but **do not** put it on the critical path until licence + maintenance +
  security are confirmed. Our own Production team + FFmpeg + Whisper already cover the
  shorts pipeline; OpenShorts is an accelerant, not a dependency.

## 4. Short Video Maker — lightweight shorts builder
- **Licence:** the project itself is permissive (MIT-style), **but** it typically
  builds on **Remotion** for rendering. 🚩 **Remotion is free for individuals and
  companies up to a small headcount; larger/commercial teams need a paid licence.**
  This is the single most important caveat in this doc for a commercial agency —
  confirm Remotion's current terms and company-size thresholds before relying on it.
- **Maintenance:** active.
- **Docker:** yes.
- **API:** runs as a service / CLI; text-in → video-out.
- **Verdict: integrate with caveat.** Excellent for fast TTS+caption+background-video
  shorts. **Resolve the Remotion licence first.** If it doesn't clear, replicate the
  same flow with FFmpeg (which we already use), losing only convenience.

## 5. FFmpeg — core video processing engine
- **Licence:** LGPL-2.1 by default; **GPL** if built with GPL components (e.g. libx264,
  libx265). 🚩 Use an LGPL build, or accept GPL terms knowingly. Distributing FFmpeg
  binaries carries attribution/source obligations — calling the system `ffmpeg` as a
  separate process is the clean pattern.
- **Maintenance:** the industry standard; extremely active.
- **Docker:** trivially available.
- **API:** CLI + libav*; we drive it via subprocess.
- **Verdict: integrate (core).** Cropping, 9:16/1:1/4:5 export, burning captions,
  `loudnorm`/`ebur128` audio normalisation and true-peak measurement for the Video
  Quality Gate. This is the workhorse of the Production and Quality teams.

## 6. Whisper / faster-whisper — transcription & captions
- **Licence:** OpenAI Whisper is **MIT**; faster-whisper (CTranslate2) is **MIT**.
  Clean for commercial use.
- **Maintenance:** active; faster-whisper is the performance choice (CTranslate2).
- **Docker:** yes; GPU optional.
- **API:** Python; produces word/segment timestamps.
- **Verdict: integrate (core).** Transcripts and timed cues power `caption_accuracy`
  and `caption_timing` in the gate, plus quote-mining and clip detection. Prefer
  **faster-whisper** on the GPU box.

## 7. Crawl4AI — AI-ready web crawling
- **Licence:** **Apache-2.0** — permissive, commercial-friendly.
- **Maintenance:** active, popular.
- **Docker:** yes.
- **API:** Python; outputs LLM/RAG-ready markdown/structured content.
- **Verdict: integrate.** Backs the Intelligence Harvester for scanning sites into the
  Brain. Pairs with Firecrawl (use whichever suits a given source).

## 8. Firecrawl — web→RAG ingestion
- **Licence:** **AGPL-3.0** for self-host 🚩 (same network-use caveat as Postiz), plus
  a hosted **cloud API** (commercial SaaS) that sidesteps the AGPL question entirely.
- **Maintenance:** very active.
- **Docker:** self-host compose available.
- **API:** clean REST; `/scrape`, `/crawl`.
- **Verdict: integrate.** Use the **cloud API** for simplicity, or self-host behind a
  service boundary. Clean scraping for the intelligence bank. Keep ingestion behind an
  interface so Crawl4AI/Firecrawl are interchangeable.

## 9. ComfyUI + Flux / Wan / Hunyuan / LTX — heavy image/video generation
- **Licence:** ComfyUI is **GPL-3.0** (run it as a separate service — already wired in
  `renderers.py` as `ComfyUIRenderer`). 🚩 **The real licensing risk is the models, not
  the runtime:**
  - **FLUX.1 [dev]** ships under a **non-commercial** licence — **not usable for paid
    agency output**; **FLUX.1 [schnell]** is **Apache-2.0** (commercial OK). Verify per
    model and per version.
  - **Wan / Hunyuan / LTX-Video** each have their **own** licences and acceptable-use
    terms — check each before commercial use.
- **Maintenance:** ComfyUI extremely active; model ecosystem moves fast.
- **Docker:** yes (GPU required — the 5090 box).
- **API:** HTTP prompt-queue API (already integrated, dry-run until `COMFYUI_BASE_URL`).
- **Verdict: integrate, with a model-licence gate.** Add a `Copyright Risk Agent`
  check that the chosen model permits commercial use before any asset it produced can
  pass to approval. Default to commercially-clear models (e.g. FLUX schnell) for
  published work.

## 10. OCR / vision stack — PaddleOCR, Tesseract, OpenCV, YOLO/Ultralytics
- **Licences:** PaddleOCR **Apache-2.0**, Tesseract **Apache-2.0**, OpenCV **Apache-2.0**
  — all clean. 🚩 **Ultralytics YOLO (v5/v8/11) is AGPL-3.0**, which for a commercial
  product effectively pushes you to their **paid enterprise licence** unless you can
  satisfy AGPL. **Mitigation:** use an Apache/MIT-licensed detector instead (older
  YOLO forks under permissive licences, OpenCV DNN with a permissive model, or a
  permissive RT-DETR), or buy the Ultralytics enterprise licence.
- **Maintenance:** all active.
- **Docker:** yes; GPU optional.
- **API:** Python.
- **Verdict: integrate** — this stack feeds the **Visual Layout Agent** and the gate's
  `visual_obstruction` check the `Region`s it needs (faces, hands/tools/products,
  logos, on-screen text). **Swap Ultralytics YOLO for a permissively-licensed detector
  before commercial use.**

---

## Integration principles

1. **Service boundaries over forks.** Postiz, Firecrawl, ComfyUI and FFmpeg are called
   as separate services/processes. This keeps AGPL/GPL obligations off our codebase and
   lets us swap backends. The existing renderer/probe seams already enforce this.
2. **Everything degrades to dry-run.** No backend is a hard dependency for the pipeline
   to run; configure env vars to switch a backend from dry-run to live.
3. **Licence is a gate, not an afterthought.** The `Copyright Risk Agent` should block
   any asset produced by a non-commercial model (Flux dev) or any clip using uncleared
   music — the Video Quality Gate already has the `music_licence` check; extend the same
   pattern to generated visuals.
4. **Commercial-use flags (🚩) are blockers until cleared by a human**, not warnings.
