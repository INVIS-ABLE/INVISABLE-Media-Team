"""Export Gate — the single contract every finished video must clear before export.

The :class:`VideoQualityGate` already runs the full granular checklist. This composes
its checks into the seven export-contract categories the Creative Toolbelt promises —
audio clarity, caption timing, safe-zone, face/object obstruction, text overlap,
platform aspect ratio, copyright/risk — so the dashboard's Quality Checker (and any
export step) gets one ``export_ready`` verdict with a per-category breakdown.

Pure: a :class:`VideoSpec` in, a structured verdict out. No I/O.
"""

from __future__ import annotations

from invisable_os.media.video_qc import CheckStatus, VideoQualityGate, VideoSpec

# (key, label, {granular check names}) — the export contract, in display order.
EXPORT_CATEGORIES: list[tuple[str, str, set[str]]] = [
    ("audio_clarity", "Audio clarity",
     {"loudness", "audio_clipping", "voice_music_balance", "overlapping_narration"}),
    ("caption_timing", "Caption timing",
     {"subtitles_valid", "caption_timing", "caption_duplication", "caption_accuracy"}),
    ("safe_zone", "Safe zone",
     {"safe_area", "edge_safe", "platform_ui_clear"}),
    ("face_obstruction", "Face & object obstruction",
     {"visual_obstruction"}),
    ("text_overlap", "Text overlap",
     {"text_overlap"}),
    ("aspect_ratio", "Platform aspect ratio",
     {"aspect_ratio", "resolution", "framerate", "duration"}),
    ("visual_quality", "Visual quality",
     {"sharpness", "visual_clutter"}),
    ("copyright_risk", "Copyright / risk",
     {"model_licence", "music_licence"}),
]

# Guardrail: every check the gate can emit must land in a category, or a FAIL could
# slip past ``export_ready`` unseen. Verified by test_export_gate.



def _category_status(checks: list) -> str:
    if not checks:
        return "not_applicable"
    if any(c.status == CheckStatus.FAIL for c in checks):
        return "fail"
    if any(c.status == CheckStatus.WARN for c in checks):
        return "warn"
    return "pass"


def export_gate(spec: VideoSpec, *, gate: VideoQualityGate | None = None) -> dict:
    """Run the quality gate and fold it into the seven export-contract categories."""
    report = (gate or VideoQualityGate()).check(spec)
    by_name = {c.name: c for c in report.checks}

    categories = []
    for key, label, names in EXPORT_CATEGORIES:
        present = [by_name[n] for n in names if n in by_name]
        categories.append({
            "key": key,
            "label": label,
            "status": _category_status(present),
            "checks": [c.model_dump() for c in present],
        })

    blocking = [c["label"] for c in categories if c["status"] == "fail"]
    warnings = [c["label"] for c in categories if c["status"] == "warn"]
    return {
        "export_ready": not blocking,
        "blocking": blocking,
        "warnings": warnings,
        "categories": categories,
    }
