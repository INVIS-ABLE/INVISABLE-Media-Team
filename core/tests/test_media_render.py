"""Real media rendering: ComfyUI + ElevenLabs clients, captions, and fallbacks."""

import os

import httpx
import pytest

from invisable_os.media.captions import to_srt, write_captions
from invisable_os.media.comfyui import ComfyUIClient, build_workflow
from invisable_os.media.elevenlabs import ElevenLabsClient
from invisable_os.media.producer import MediaProducer
from invisable_os.media.renderers import CaptionRenderer, ComfyUIRenderer, ElevenLabsRenderer
from invisable_os.models.content import ContentCandidate, Platform

PNG = b"\x89PNG\r\n\x1a\n_fake_image_bytes"
MP3 = b"ID3_fake_audio_bytes"


# --- ComfyUI workflow + client ----------------------------------------------


def test_build_workflow_injects_prompt_and_seed():
    g = build_workflow("a builder resting", width=512, height=768, seed=42)
    assert g["6"]["inputs"]["text"] == "a builder resting"
    assert g["3"]["inputs"]["seed"] == 42
    assert g["5"]["inputs"]["width"] == 512 and g["5"]["inputs"]["height"] == 768
    assert g["9"]["class_type"] == "SaveImage"


def _comfy_handler(request: httpx.Request) -> httpx.Response:
    path = request.url.path
    if path == "/prompt":
        return httpx.Response(200, json={"prompt_id": "p1"})
    if path == "/history/p1":
        return httpx.Response(200, json={"p1": {"outputs": {"9": {"images": [
            {"filename": "out.png", "subfolder": "", "type": "output"}]}}}})
    if path == "/view":
        return httpx.Response(200, content=PNG)
    return httpx.Response(404)


def test_comfyui_client_generate_writes_file(tmp_path):
    client = httpx.Client(transport=httpx.MockTransport(_comfy_handler))
    out = str(tmp_path / "img.png")
    path = ComfyUIClient("http://comfy", client=client).generate("invisible illness", out, seed=1)
    assert os.path.isfile(path)
    assert open(path, "rb").read() == PNG


def test_comfyui_client_raises_without_images(tmp_path):
    def handler(request):
        if request.url.path == "/prompt":
            return httpx.Response(200, json={"prompt_id": "p1"})
        # Completed (truthy outputs) but produced no images.
        return httpx.Response(200, json={"p1": {"outputs": {"9": {"images": []}}}})
    client = httpx.Client(transport=httpx.MockTransport(handler))
    with pytest.raises(RuntimeError):
        ComfyUIClient("http://comfy", client=client).generate("x", str(tmp_path / "a.png"))


# --- ElevenLabs -------------------------------------------------------------


def test_elevenlabs_synthesize_writes_audio(tmp_path):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["xi-api-key"] == "key"
        assert "/v1/text-to-speech/" in request.url.path
        return httpx.Response(200, content=MP3)
    client = httpx.Client(transport=httpx.MockTransport(handler))
    out = str(tmp_path / "v.mp3")
    path = ElevenLabsClient("key", base_url="http://el", client=client).synthesize("hello", out)
    assert open(path, "rb").read() == MP3


# --- Captions ---------------------------------------------------------------


def test_to_srt_is_well_formed():
    srt = to_srt("This is a fairly long script line that should wrap across cues nicely.")
    assert srt.startswith("1\n")
    assert "00:00:00,000 --> 00:00:03,000" in srt


def test_write_captions_creates_srt(tmp_path):
    path = write_captions("you are not alone", str(tmp_path / "c.srt"))
    assert os.path.isfile(path)
    assert "you are not alone" in open(path).read()


# --- Renderer behaviour -----------------------------------------------------


def test_renderers_dry_run_when_not_live():
    r = ComfyUIRenderer().render("tiktok", "clip", out_dir="data/x", live=False)
    assert r.backend == "dry-run"
    v = ElevenLabsRenderer().render("voiceover", "say hi", out_dir="data/x", live=True)  # no key
    assert v.backend == "dry-run"


def test_comfyui_renderer_live_writes_via_client(tmp_path, monkeypatch):
    monkeypatch.setenv("COMFYUI_BASE_URL", "http://comfy")

    class FakeClient:
        def __init__(self, base_url, **kw):
            pass

        def generate(self, prompt, out_path, **kw):
            from invisable_os.media.fsutil import write_bytes
            return write_bytes(out_path, PNG)

    monkeypatch.setattr("invisable_os.media.comfyui.ComfyUIClient", FakeClient)
    r = ComfyUIRenderer().render("quote_graphic", "a quote", out_dir=str(tmp_path), live=True)
    assert r.backend == "comfyui"
    assert os.path.isfile(r.path)


def test_comfyui_renderer_falls_back_on_error(tmp_path, monkeypatch):
    monkeypatch.setenv("COMFYUI_BASE_URL", "http://comfy")

    class Boom:
        def __init__(self, *a, **k):
            pass

        def generate(self, *a, **k):
            raise RuntimeError("backend down")

    monkeypatch.setattr("invisable_os.media.comfyui.ComfyUIClient", Boom)
    # A backend error must degrade to dry-run, never raise.
    r = ComfyUIRenderer().render("quote_graphic", "a quote", out_dir=str(tmp_path), live=True)
    assert r.backend == "dry-run"
    assert r.ok


def test_caption_renderer_live_writes_srt(tmp_path):
    r = CaptionRenderer().render("caption", "you're not alone", out_dir=str(tmp_path), live=True)
    assert r.backend == "captions"
    assert os.path.isfile(r.path) and r.path.endswith(".srt")


# --- Producer live mode -----------------------------------------------------


def test_producer_live_writes_text_assets(tmp_path):
    producer = MediaProducer(out_dir=str(tmp_path), live=True)
    cand = ContentCandidate(brief="Tool theft", platform=Platform.TIKTOK, hook="Not again.")
    results = producer.produce(cand)
    written = [r for r in results if r.backend in {"captions", "passthrough"}]
    assert written, "caption / story_poll / comment_response should be written in live mode"
    assert all(os.path.isfile(r.path) for r in written)


def test_producer_dry_run_writes_nothing(tmp_path):
    producer = MediaProducer(out_dir=str(tmp_path), live=False)
    cand = ContentCandidate(brief="Tool theft", platform=Platform.TIKTOK, hook="Not again.")
    results = producer.produce(cand)
    assert all(r.backend == "dry-run" for r in results)
    assert not any(os.path.exists(r.path) for r in results)
