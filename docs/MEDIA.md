# Media Rendering

The Content Flywheel produces **asset specs**; the media pipeline turns them into
**real files** in the media library. Each renderer talks to its real backend in
**live** mode and falls back to a **dry-run** placeholder otherwise — so the pipeline
runs identically on a GPU box with keys, on a laptop with none, and in CI.

## Backends

| Asset kinds | Renderer | Backend | Output |
| ----------- | -------- | ------- | ------ |
| `quote_graphic`, `carousel`, `image` | ComfyUI | Flux via ComfyUI | `.png` |
| `tiktok`, `reel` | ComfyUI | Wan/Hunyuan/LTX via ComfyUI | `.mp4` |
| `voiceover` | ElevenLabs | ElevenLabs TTS | `.mp3` |
| `caption` | Captions | SRT writer (Whisper optional) | `.srt` |
| `story_poll`, `comment_response` | Passthrough | text | `.txt` |

## ComfyUI

`media/comfyui.py` implements the real ComfyUI HTTP flow:

```
POST /prompt {prompt: <graph>}      → prompt_id
GET  /history/{prompt_id}  (poll)   → outputs
GET  /view?filename=…&type=output   → image/video bytes → written to disk
```

A standard text-to-image graph is built by `build_workflow(prompt, width, height,
seed, …)`. To use your own graph (e.g. a Flux or video pipeline), set
`COMFYUI_WORKFLOW` to a JSON file using `%PROMPT%` / `%SEED%` / `%WIDTH%` /
`%HEIGHT%` placeholders. The checkpoint defaults to `COMFYUI_CHECKPOINT`.

## ElevenLabs

`media/elevenlabs.py` posts to `/v1/text-to-speech/{voice_id}` with `xi-api-key` and
writes the returned MP3. Voice and model are configurable
(`ELEVENLABS_VOICE_ID`, `ELEVENLABS_MODEL`).

## Captions

`media/captions.py` writes a real `.srt` from the script text (deterministic timing).
`transcribe_audio()` is an optional best-effort hook that uses local Whisper to
caption *rendered audio* when `openai-whisper` is installed — never required.

## Live vs dry-run

The producer runs **live** when any media backend is configured
(`COMFYUI_BASE_URL` / `ELEVENLABS_API_KEY`) or `INVISABLE_MEDIA_OUT=1`; otherwise
dry-run (no files written, no network). In live mode:

- a configured backend renders for real;
- an *unconfigured or failing* backend degrades to a dry-run placeholder for that
  asset — one broken backend never blocks the rest of the post's assets.

```bash
# laptop, no GPU/keys: text + captions are still written for real
INVISABLE_MEDIA_OUT=1 invisable produce <queue-item-id>

# GPU box with keys: images, video, and voice render for real
COMFYUI_BASE_URL=http://localhost:8188 ELEVENLABS_API_KEY=… invisable produce <id>
```

Rendered files land under `data/assets/generated/<queue-item-id>/<backend>/…` and are
recorded in the media library (`GET /v1/media?item_id=…`, or the dashboard's **Media**
tab).
