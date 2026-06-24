"""Generation-model licence gate.

The Remix department's :mod:`invisable_os.guardrails.rights` gate covers *footage
provenance* — is this clip owned / licensed / CC / reference-only? This module covers
a **different axis**: when an asset is *generated* by an AI model (ComfyUI/Flux/Wan/
Hunyuan/LTX) or analysed by a detector (Ultralytics YOLO), **does that model's licence
permit commercial use** for a UK media agency?

This is the gap flagged in :doc:`TOOL_INTEGRATION_REVIEW` — e.g. FLUX.1 [dev] is
**non-commercial**, and HunyuanVideo's community licence **excludes the UK/EU** — and
the kind of thing the Copyright Risk Agent must block before a generated asset reaches
the approval queue. It mirrors the ``music_licence`` check in the Video Quality Gate,
extended to generated visuals.

The gate is **fail-closed**: an unknown model is treated as *not cleared* until a human
registers it, so a new model can never silently ship commercial output.

⚠️ Licences change. The registry reflects the state at the knowledge cutoff and every
entry should be re-verified against the model card before relying on it. ``verify=True``
marks entries that especially warrant a fresh check.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from pydantic import BaseModel, Field


@dataclass(frozen=True)
class ModelLicence:
    """One generation/detector model and whether its output is commercial-safe."""

    name: str  # canonical, human-readable model id
    licence: str  # licence name
    commercial: bool  # may its output be used in paid/commercial work?
    kind: str  # image | video | audio | tts | asr | detector
    note: str = ""
    verify: bool = False  # especially warrants a fresh licence check
    aliases: tuple[str, ...] = field(default_factory=tuple)


# Registry. Conservative and honest; not legal advice — verify against the model card.
MODEL_LICENCES: tuple[ModelLicence, ...] = (
    # --- Image generation ---------------------------------------------------
    ModelLicence(
        "FLUX.1 [schnell]", "Apache-2.0", True, "image",
        "Commercial use OK.", aliases=("flux-schnell", "flux.1-schnell", "flux1-schnell"),
    ),
    ModelLicence(
        "FLUX.1 [dev]", "FLUX.1 [dev] Non-Commercial License", False, "image",
        "NON-COMMERCIAL — outputs may not be used for paid agency work. "
        "Use FLUX.1 [schnell] or a licensed FLUX Pro endpoint instead.",
        aliases=("flux-dev", "flux.1-dev", "flux1-dev", "flux dev"),
    ),
    ModelLicence(
        "FLUX.1.1 [pro]", "BFL commercial API licence", True, "image",
        "Commercial via Black Forest Labs' licensed API/endpoint.", verify=True,
        aliases=("flux-pro", "flux.1.1-pro", "flux1.1-pro"),
    ),
    ModelLicence(
        "Stable Diffusion XL", "CreativeML OpenRAIL++-M", True, "image",
        "Commercial OK, but the OpenRAIL use-based restrictions apply.",
        aliases=("sdxl", "stable-diffusion-xl"),
    ),
    ModelLicence(
        "Stable Diffusion 3.5", "Stability AI Community License", True, "image",
        "Free for commercial use only under the revenue threshold; above it needs an "
        "enterprise licence. Check current threshold.", verify=True,
        aliases=("sd3", "sd3.5", "stable-diffusion-3", "stable-diffusion-3.5"),
    ),
    # --- Video generation ---------------------------------------------------
    ModelLicence(
        "Wan 2.1", "Apache-2.0", True, "video",
        "Commercial use OK.", aliases=("wan", "wan2.1", "wan-2.1"),
    ),
    ModelLicence(
        "LTX-Video", "Lightricks open-weights licence", True, "video",
        "Generally permits commercial use; confirm the current model-card terms.",
        verify=True, aliases=("ltx", "ltxv", "ltx-video"),
    ),
    ModelLicence(
        "HunyuanVideo", "Tencent Hunyuan Community License", False, "video",
        "Commercial allowed elsewhere but the licence EXCLUDES the EU/UK (and a few "
        "other territories) and >100M-MAU products. As a UK org, treat as not cleared "
        "without separate permission.", verify=True,
        aliases=("hunyuan", "hunyuan-video", "hunyuanvideo"),
    ),
    ModelLicence(
        "Stable Video Diffusion", "Stability AI licence", False, "video",
        "Originally a non-commercial research licence; verify the current terms before "
        "any commercial use.", verify=True, aliases=("svd", "stable-video-diffusion"),
    ),
    # --- Audio / voice ------------------------------------------------------
    ModelLicence(
        "Kokoro TTS", "Apache-2.0", True, "tts",
        "Commercial use OK.", aliases=("kokoro",),
    ),
    ModelLicence(
        "XTTS v2", "Coqui Public Model License (CPML)", False, "tts",
        "Non-commercial model licence — not for paid output.",
        aliases=("xtts", "xtts-v2", "coqui-xtts"),
    ),
    ModelLicence(
        "Whisper", "MIT", True, "asr",
        "Transcription model; commercial OK.", aliases=("openai-whisper", "faster-whisper"),
    ),
    # --- Detectors (feed the Visual Layout Agent / QC) ----------------------
    ModelLicence(
        "Ultralytics YOLO", "AGPL-3.0", False, "detector",
        "AGPL effectively requires Ultralytics' paid enterprise licence for a closed "
        "commercial product. Swap for an Apache/MIT detector (e.g. permissive RT-DETR, "
        "OpenCV DNN) or buy the enterprise licence.", verify=True,
        aliases=("yolo", "yolov8", "yolo11", "ultralytics"),
    ),
    ModelLicence(
        "PaddleOCR", "Apache-2.0", True, "detector",
        "Commercial OK.", aliases=("paddle-ocr", "paddleocr"),
    ),
    ModelLicence(
        "Tesseract", "Apache-2.0", True, "detector",
        "Commercial OK.", aliases=("tesseract-ocr",),
    ),
)


def _norm(name: str) -> str:
    return name.strip().lower()


_BY_KEY: dict[str, ModelLicence] = {}
for _m in MODEL_LICENCES:
    for _key in (_m.name, *_m.aliases):
        _BY_KEY[_norm(_key)] = _m


def get_licence(name: str) -> ModelLicence | None:
    """Look up a model's licence by canonical name or alias (case-insensitive)."""
    return _BY_KEY.get(_norm(name))


class LicenceVerdict(BaseModel):
    """The outcome of a model-licence check — mirrors RightsVerdict's shape."""

    passed: bool
    blocked: list[str] = Field(default_factory=list)
    cleared: list[str] = Field(default_factory=list)
    unknown: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


def licence_check(models: list[str], *, commercial: bool = True) -> LicenceVerdict:
    """Gate the generation/detector models used to build an asset.

    Fail-closed: an unknown model is a violation (register it first). When
    ``commercial`` is False (e.g. internal/reference output) any registered model is
    allowed and only unknown models are flagged.
    """
    blocked: list[str] = []
    cleared: list[str] = []
    unknown: list[str] = []
    notes: list[str] = []

    for name in models:
        lic = get_licence(name)
        if lic is None:
            unknown.append(name)
            notes.append(f"'{name}' is not in the model-licence registry — register it "
                         "with its licence before commercial use (fail-closed).")
            continue
        if commercial and not lic.commercial:
            blocked.append(lic.name)
            notes.append(f"'{lic.name}' ({lic.licence}): {lic.note}")
        else:
            cleared.append(lic.name)
            if lic.verify:
                notes.append(f"'{lic.name}' ({lic.licence}): cleared but verify — {lic.note}")

    passed = not blocked and not unknown
    return LicenceVerdict(
        passed=passed, blocked=blocked, cleared=cleared, unknown=unknown, notes=notes,
    )
