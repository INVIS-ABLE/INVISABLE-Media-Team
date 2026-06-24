"""Media pipeline.

Turns the Content Flywheel's *asset specs* (a TikTok, a quote card, a voiceover…)
into actual rendered media via the production stack — ComfyUI/Flux (image), Wan/
Hunyuan/LTX (video), ElevenLabs (voice), Whisper (captions), OpenCut (assembly).

Every renderer degrades to a safe **dry-run** that records a placeholder asset, so
the pipeline is operational offline and on a server with no GPU; configure the
backends to render for real. This closes the loop: idea → plan → assets in the
media library, ready for the approval queue.
"""

from invisable_os.media.base import Renderer, RenderResult
from invisable_os.media.producer import MediaProducer
from invisable_os.media.safe_area import (
    Surface,
    VisualLayoutAgent,
    get_template,
)
from invisable_os.media.video_qc import VideoQCReport, VideoQualityGate, VideoSpec

__all__ = [
    "Renderer",
    "RenderResult",
    "MediaProducer",
    "Surface",
    "VisualLayoutAgent",
    "get_template",
    "VideoQualityGate",
    "VideoSpec",
    "VideoQCReport",
]
