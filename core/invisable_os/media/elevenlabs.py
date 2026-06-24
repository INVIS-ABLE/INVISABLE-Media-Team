"""ElevenLabs client — text-to-speech voiceover.

Calls the ElevenLabs TTS endpoint and writes the returned audio to disk. Raises on
failure so the renderer can fall back to dry-run.
"""

from __future__ import annotations

import os

import httpx

from invisable_os.media.fsutil import write_bytes

DEFAULT_VOICE = "21m00Tcm4TlvDq8ikWAM"  # a neutral default voice
DEFAULT_MODEL = "eleven_multilingual_v2"


class ElevenLabsClient:
    def __init__(
        self,
        api_key: str,
        *,
        voice_id: str | None = None,
        model_id: str | None = None,
        base_url: str | None = None,
        client: httpx.Client | None = None,
    ) -> None:
        self.api_key = api_key
        self.voice_id = voice_id or os.getenv("ELEVENLABS_VOICE_ID", DEFAULT_VOICE)
        self.model_id = model_id or os.getenv("ELEVENLABS_MODEL", DEFAULT_MODEL)
        self.base_url = (base_url or os.getenv("ELEVENLABS_BASE_URL", "https://api.elevenlabs.io")).rstrip("/")
        self._client = client or httpx.Client(timeout=30.0)

    def synthesize(self, text: str, out_path: str) -> str:
        resp = self._client.post(
            f"{self.base_url}/v1/text-to-speech/{self.voice_id}",
            headers={"xi-api-key": self.api_key, "accept": "audio/mpeg"},
            json={
                "text": text,
                "model_id": self.model_id,
                "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
            },
        )
        resp.raise_for_status()
        return write_bytes(out_path, resp.content)
