# End-to-End Smoke Test & Live-Adapter Runbook

A single command walks a real day through the whole platform and reports, per
step, whether each external adapter ran **live** or fell back to **dry-run**:

```
health → integrations → harvest → daily plan (persist) → seed channels →
approve → produce media → assemble video → publish → DAM sync →
metrics sync → watchtower ingest → founder recognition
```

Implemented in [`core/invisable_os/smoke.py`](../core/invisable_os/smoke.py) and
guarded by `core/tests/test_smoke_e2e.py` (the walk must pass in dry-run on every CI
run). Every adapter degrades gracefully, so this is safe to run anywhere.

## Run it

```bash
cd core && source .venv/bin/activate

# 1. In-process, temp SQLite, no credentials — exercises the whole flow in dry-run.
python -m invisable_os.smoke

# 2. Against a running server (local or deployed) — exercises whatever is configured.
SMOKE_BASE_URL=http://localhost:8080 python -m invisable_os.smoke
```

A clean dry-run prints `RESULT: PASS` with `adapters live: none (all dry-run)`.
With credentials set, the matching rows show the live backend (e.g.
`publish (run)  backend=postiz`) and `adapters live:` lists them.

Check what the server thinks is configured at any time:

```bash
curl -s localhost:8080/v1/integrations | jq .
# {"postiz":true,"metricool":false,"resourcespace":false,"comfyui":true,"elevenlabs":false,...}
```

## Going live — credentials per adapter

Set the env vars below (e.g. in `.env`) and re-run the smoke test. Each adapter is
**independent**: configure one and only that one goes live; the rest stay dry-run.
Always smoke-test one adapter at a time first so a bad credential is obvious.

| Adapter | Goes live when these are set | What it calls | Drives via |
| ------- | ---------------------------- | ------------- | ---------- |
| **Postiz** (publish) | `POSTIZ_API_URL`, `POSTIZ_API_KEY` (+ `POSTIZ_INTEGRATIONS` JSON mapping platform→integration id) | `POST {url}/public/v1/posts` (override `POSTIZ_POSTS_PATH`) | `POST /v1/publish/run` · `invisable publish` |
| **Metricool** (metrics) | `METRICOOL_API_TOKEN`, `METRICOOL_BLOG_ID` | `GET /api/v2/analytics/posts` | `POST /v1/metrics/sync` · `invisable metrics-sync` |
| **ResourceSpace** (DAM) | `RESOURCESPACE_URL`, `RESOURCESPACE_USER`, `RESOURCESPACE_PRIVATE_KEY` | signed `create_resource` + `upload_multipart` | `POST /v1/dam/sync/{id}` · `invisable dam-sync` |
| **ComfyUI** (image/video) | `COMFYUI_BASE_URL` (+ optional `COMFYUI_CHECKPOINT`, `COMFYUI_IMAGE_SIZE`, `COMFYUI_WORKFLOW`) | `POST /prompt` → poll `/history` → `GET /view` | `POST /v1/media/produce/{id}` · `invisable produce` |
| **ElevenLabs** (voiceover) | `ELEVENLABS_API_KEY` (+ optional `ELEVENLABS_VOICE_ID`, `ELEVENLABS_MODEL`) | `POST /v1/text-to-speech/{voice}` | `POST /v1/media/produce/{id}` (voiceover asset) |
| **Whisper** (captions) | local `whisper` package (optional; deterministic SRT otherwise) | local | `produce` (captions) |
| **FFmpeg** (assembly) | `ffmpeg` on PATH (+ real input files) | local `ffmpeg` | `POST /v1/media/assemble/{id}` · `invisable assemble` |
| **Claude / Ollama** (generation) | `ANTHROPIC_API_KEY` or a reachable `OLLAMA_BASE_URL` | LLM API | every generation step (tournament/daily) |

Notes:
- **Generation quality:** with no LLM the deterministic templates don't clear the
  11-dimension quality bar, so the day's posts land as `needs_improvement` (the gate
  working as designed). With Claude/Ollama configured they clear it and arrive as
  `pending_review`.
- **Publishing is due-gated:** `publish/run` takes approved-now items and scheduled
  items whose time has arrived — future-scheduled posts correctly don't publish yet.
- **Nothing auto-publishes:** the approval queue is always a human gate; the smoke
  test approves items explicitly to exercise the downstream path.
- **Auth:** if `INVISABLE_API_KEY` is set, pass it to `SMOKE_BASE_URL` runs via the
  server; the in-process run leaves it unset.

## Per-adapter unit tests (no network)

Each live adapter has a unit test that drives it through a mocked transport, so the
request shape/auth is verified without credentials:

```bash
pytest tests/test_postiz.py tests/test_integrations.py tests/test_media_render.py \
       tests/test_media_assemble.py tests/test_smoke_e2e.py -q
```
