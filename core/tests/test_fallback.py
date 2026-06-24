"""Tests for the voice + posting fallback chains.

The platform never hard-fails on a missing provider: each chain ends in a terminal
link that is always available, so selection always succeeds. Deterministic and
offline.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from invisable_os.main import app
from invisable_os.services.fallback import (
    POSTING_FALLBACK_CHAIN,
    VOICE_FALLBACK_CHAIN,
    fallback_status,
    select_posting,
    select_voice,
)

client = TestClient(app)


# --- voice ------------------------------------------------------------------


def test_voice_prefers_the_first_available_link():
    pick = select_voice({"ElevenLabs", "Piper"})
    assert pick["selected"] == "ElevenLabs"
    assert pick["degraded"] is False
    assert pick["terminal_fallback"] is False


def test_voice_degrades_to_next_when_preferred_missing():
    pick = select_voice({"F5-TTS", "Piper"})
    assert pick["selected"] == "F5-TTS"
    assert pick["degraded"] is True


def test_voice_falls_back_to_text_when_nothing_configured():
    pick = select_voice(set())
    assert pick["selected"] == "text"
    assert pick["terminal_fallback"] is True
    assert pick["selected"] == VOICE_FALLBACK_CHAIN[-1]


def test_voice_detects_from_env():
    pick = select_voice(environ={"ELEVENLABS_API_KEY": "sk-test"})
    assert pick["selected"] == "ElevenLabs"


# --- posting ----------------------------------------------------------------


def test_posting_prefers_metricool_when_available():
    pick = select_posting({"Metricool", "Postiz"})
    assert pick["selected"] == "Metricool"
    assert pick["degraded"] is False


def test_posting_falls_back_to_csv_when_nothing_configured():
    pick = select_posting(set())
    assert pick["selected"] == "CSV"
    assert pick["terminal_fallback"] is True
    assert pick["selected"] == POSTING_FALLBACK_CHAIN[-1]


def test_posting_detects_from_env():
    pick = select_posting(environ={"POSTIZ_API_KEY": "x"})
    assert pick["selected"] == "Postiz"


# --- combined status --------------------------------------------------------


def test_fallback_status_reports_both_chains():
    status = fallback_status(environ={})
    assert status["ok"] is True
    assert status["voice"]["selected"] == "text"
    assert status["posting"]["selected"] == "CSV"
    assert status["all_degraded"] is True


def test_fallback_status_not_all_degraded_when_one_provider_present():
    status = fallback_status(environ={"ELEVENLABS_API_KEY": "sk"})
    assert status["voice"]["selected"] == "ElevenLabs"
    assert status["all_degraded"] is False


# --- HTTP surface -----------------------------------------------------------


def test_fallback_api():
    r = client.get("/v1/fallback/status").json()
    assert "voice" in r and "posting" in r
    assert r["voice"]["selected"] in VOICE_FALLBACK_CHAIN
    assert r["posting"]["selected"] in POSTING_FALLBACK_CHAIN
