"""Video assembly: FFmpeg command building, the assembler, and assemble_post."""

import os

from invisable_os.media import VideoAssembler, build_command
from invisable_os.models.content import QueueStatus
from invisable_os.services import assemble_post
from invisable_os.store import get_repository


def _fake_runner(out_bytes=b"FINISHED_VIDEO"):
    def run(cmd):
        # cmd[-1] is the output path; emulate FFmpeg writing the file.
        with open(cmd[-1], "wb") as f:
            f.write(out_bytes)
    return run


# --- command building -------------------------------------------------------


def test_build_command_image_with_audio_and_captions():
    cmd = build_command(visual="bg.png", out_path="out.mp4", audio="vo.mp3", captions="c.srt")
    assert "-loop" in cmd  # still image is looped
    assert "subtitles=c.srt" in cmd
    assert "-shortest" in cmd and "-c:a" in cmd  # audio mixed
    assert "-tune" in cmd and cmd[-1] == "out.mp4"


def test_build_command_video_input_is_not_looped():
    cmd = build_command(visual="clip.mp4", out_path="out.mp4", audio="vo.mp3")
    assert "-loop" not in cmd
    assert "clip.mp4" in cmd


def test_build_command_image_without_audio_uses_duration():
    cmd = build_command(visual="bg.png", out_path="out.mp4", duration=10)
    assert "-t" in cmd and "10" in cmd
    assert "-an" in cmd
    assert not any(c.startswith("subtitles=") for c in cmd)


# --- assembler --------------------------------------------------------------


def test_assemble_dry_run_when_ffmpeg_unavailable(tmp_path):
    # force_available=False and (assume) no ffmpeg in CI → dry-run.
    out = str(tmp_path / "final.mp4")
    res = VideoAssembler(force_available=False).assemble(visual=None, out_path=out)
    assert res.backend == "dry-run"
    assert res.ok


def test_assemble_runs_ffmpeg_and_writes_file(tmp_path):
    visual = tmp_path / "bg.png"
    visual.write_bytes(b"\x89PNG_fake")
    out = str(tmp_path / "final.mp4")
    asm = VideoAssembler(runner=_fake_runner(), force_available=True)
    res = asm.assemble(visual=str(visual), out_path=out, audio=None, captions=None)
    assert res.backend == "ffmpeg"
    assert os.path.isfile(out)
    assert res.command and res.command[0] == "ffmpeg"


def test_assemble_falls_back_when_runner_raises(tmp_path):
    visual = tmp_path / "bg.png"
    visual.write_bytes(b"x")

    def boom(cmd):
        raise RuntimeError("ffmpeg exploded")

    res = VideoAssembler(runner=boom, force_available=True).assemble(
        visual=str(visual), out_path=str(tmp_path / "o.mp4")
    )
    assert res.backend == "dry-run"  # never raises
    assert res.ok


# --- assemble_post service --------------------------------------------------


def _seed_real_assets(repo, item_id, tmp_path):
    img = tmp_path / "quote.png"
    img.write_bytes(b"img")
    vo = tmp_path / "voice.mp3"
    vo.write_bytes(b"aud")
    srt = tmp_path / "caps.srt"
    srt.write_text("1\n00:00:00,000 --> 00:00:03,000\nhi\n")
    repo.add_media_asset(item_id, "quote_graphic", "img", str(img), "comfyui")
    repo.add_media_asset(item_id, "voiceover", "vo", str(vo), "elevenlabs")
    repo.add_media_asset(item_id, "caption", "caps", str(srt), "captions")
    return str(img), str(vo), str(srt)


def test_assemble_post_stitches_real_assets(tmp_path):
    repo = get_repository()
    item_id = repo.enqueue({
        "candidate_id": "c1", "candidate": {"hook": "h", "platform": "tiktok"},
        "status": QueueStatus.APPROVED.value, "platform": "tiktok",
    })
    img, vo, srt = _seed_real_assets(repo, item_id, tmp_path)

    asm = VideoAssembler(runner=_fake_runner(), force_available=True)
    res = assemble_post(item_id, assembler=asm)
    assert res["backend"] == "ffmpeg"
    assert os.path.isfile(res["final_video"])
    assert res["inputs"] == {"visual": img, "audio": vo, "captions": srt}
    # A final_video asset is recorded in the library.
    finals = [a for a in repo.list_media(item_id) if a["kind"] == "final_video"]
    assert len(finals) == 1 and finals[0]["backend"] == "ffmpeg"


def test_assemble_post_dry_run_without_real_assets(tmp_path):
    repo = get_repository()
    item_id = repo.enqueue({
        "candidate_id": "c2", "candidate": {"hook": "h", "platform": "tiktok"},
        "status": QueueStatus.PENDING_REVIEW.value, "platform": "tiktok",
    })
    # Only a dry-run plan exists (no real file).
    repo.add_media_asset(item_id, "quote_graphic", "x", "data/x/quote_graphic.png", "dry-run")
    asm = VideoAssembler(runner=_fake_runner(), force_available=True)
    res = assemble_post(item_id, assembler=asm)
    assert res["backend"] == "dry-run"
    assert res["inputs"]["visual"] is None


def test_assemble_post_missing_item():
    assert "error" in assemble_post("nope")
