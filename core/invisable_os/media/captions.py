"""Captions — turn a script into a real SRT subtitle file.

Burned-in captions are generated deterministically from the script text. Whisper's
role (transcribing rendered audio/video to *timed* captions) is provided as an
optional, best-effort hook for when audio exists; it is never required.
"""

from __future__ import annotations

import textwrap

from invisable_os.media.fsutil import write_text

SECONDS_PER_CUE = 3


def _timecode(seconds: int) -> str:
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d},000"


def to_srt(text: str, *, seconds_per_cue: int = SECONDS_PER_CUE, width: int = 42) -> str:
    """Chunk ``text`` into sequential SRT cues."""
    chunks = textwrap.wrap(text.strip(), width=width) or ["…"]
    lines: list[str] = []
    for i, chunk in enumerate(chunks):
        start = i * seconds_per_cue
        end = start + seconds_per_cue
        lines.append(str(i + 1))
        lines.append(f"{_timecode(start)} --> {_timecode(end)}")
        lines.append(chunk)
        lines.append("")
    return "\n".join(lines)


def write_captions(text: str, out_path: str) -> str:
    return write_text(out_path, to_srt(text))


def transcribe_audio(audio_path: str) -> str | None:
    """Optional: transcribe an audio file with local Whisper if available."""
    try:
        import whisper  # type: ignore
    except Exception:  # noqa: BLE001
        return None
    try:
        model = whisper.load_model("base")
        return model.transcribe(audio_path).get("text")
    except Exception:  # noqa: BLE001
        return None
