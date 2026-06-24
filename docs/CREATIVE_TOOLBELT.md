# Creative Toolbelt

The visual-polish layer of INVISABLE OS — the bit that makes people stick around:
cleaner visuals, sharper captions, better pacing, safer overlays, stronger templates.

It is built as a sequence of focused, dry-run-safe increments. This first increment
lands the **scaffold** (the eight PWA sections) and the **Export Gate** (the contract
every finished video must clear). The authoring studios fill in next, each wired to a
backend that degrades to a dry-run when its tool/model isn't installed — exactly like
the existing renderers and probes.

## The eight sections

| Section | Status | Backed by |
| ------- | ------ | --------- |
| Design Studio | planned | brand palette (Values) + media library; open-source editor (Polotno / Open Design — licence reviewed before integration), Canva API optional later |
| Template Library | planned | VideoAssembler + safe-area templates; Remotion-style code-defined templates |
| Caption Studio | planned | the Whisper caption renderer; WhisperX for word-level timing |
| Video Builder | planned | `/v1/media/finish`; AI b-roll via the renderer seam (Wan2.1 / HunyuanVideo / LTX / CogVideoX / Mochi) |
| Meme Builder | planned | Pop Culture index + humour guardrails |
| Effects Library | planned | FFmpeg filters, gated by safe-zone + visual-quality |
| **Quality Checker** | **live** | the Export Gate (below) |
| **Asset Warchest** | **live** | `/v1/media` library; ResourceSpace DAM when configured |

Reference policy is unchanged (see `REFERENCES.md`): MIT/Apache patterns may inform
original code; AGPL tools (OpenCut, MediaCMS) are reference-only; we never copy code
or copyrighted frames, and generation-model licences are gated for commercial use.

## The Export Gate

One verdict every finished video must clear before export. It composes the existing
`VideoQualityGate` (which already runs the full granular checklist behind FFmpeg /
Whisper / OpenCV / OCR probes, each degrading to dry-run) into the export contract's
named categories:

```
POST /v1/export/gate   (body: a VideoSpec, same shape as /v1/video/qc)
   → { export_ready, blocking: [labels], warnings: [labels],
       categories: [{ key, label, status, checks: [QCCheck] }] }
```

Categories: **Audio clarity · Caption timing · Safe zone · Face & object obstruction ·
Text overlap · Platform aspect ratio · Visual quality · Copyright / risk**.

`export_ready` is true only when no category fails. A guardrail test asserts every
check the gate can emit maps to a category, so a failure can never slip past the
verdict unseen. The gate also now reports **face/object obstruction** and **text
overlap** as two distinct checks (previously bundled), matching the contract.

Surfaced in the dashboard's **Quality Checker** section, which runs the gate live on a
clean and a deliberately flawed sample so the pass/blocked UI is self-explanatory.
