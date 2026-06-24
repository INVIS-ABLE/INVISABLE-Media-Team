"""Fallback chains — graceful degradation for voice and posting.

The platform never hard-fails on a missing provider. Voice generation walks a
chain (ElevenLabs → OpenVoice → F5-TTS → Piper → text) and posting walks another
(Metricool → Postiz → TryPost → CSV); each ends in a terminal fallback that is
*always* available — plain text for voice, a CSV export for posting — so a draft
can always be produced and always be handed off, even fully offline.

This module decides which link to use given what's actually configured. Provider
availability is read from the environment (an API key / URL present = available);
the terminal link is always available, so selection can never fail. The canonical
chains live with the Failsafe module so backup/status and selection agree.
"""

from __future__ import annotations

import os

from invisable_os.services.backup import POSTING_FALLBACK_CHAIN, VOICE_FALLBACK_CHAIN

# Provider → the env var(s) whose presence means "this provider is configured".
# The terminal link of each chain is intentionally absent here: it's always on.
_VOICE_ENV: dict[str, tuple[str, ...]] = {
    "ElevenLabs": ("ELEVENLABS_API_KEY",),
    "OpenVoice": ("OPENVOICE_URL", "INVISABLE_OPENVOICE_URL"),
    "F5-TTS": ("F5_TTS_URL", "INVISABLE_F5_TTS_URL"),
    "Piper": ("PIPER_BIN", "PIPER_PATH", "INVISABLE_PIPER_BIN"),
}
_POSTING_ENV: dict[str, tuple[str, ...]] = {
    "Metricool": ("METRICOOL_API_KEY", "METRICOOL_TOKEN"),
    "Postiz": ("POSTIZ_API_KEY", "POSTIZ_API_URL"),
    "TryPost": ("TRYPOST_API_KEY", "TRYPOST_API_URL"),
}


def _present(env_keys: tuple[str, ...], environ: dict) -> bool:
    return any(environ.get(k) for k in env_keys)


def _detect(chain: list[str], env_map: dict[str, tuple[str, ...]], environ: dict) -> set[str]:
    """Which links of a chain are available right now (terminal link always is)."""
    available = {link for link, keys in env_map.items() if _present(keys, environ)}
    available.add(chain[-1])  # terminal fallback is always available
    return available


def _select(chain: list[str], available: set[str]) -> dict:
    """Walk the chain and pick the first available link."""
    selected = next((link for link in chain if link in available), chain[-1])
    return {
        "chain": list(chain),
        "available": [link for link in chain if link in available],
        "selected": selected,
        "degraded": selected != chain[0],
        "terminal_fallback": selected == chain[-1],
    }


def select_voice(available: set[str] | None = None, *, environ: dict | None = None) -> dict:
    """Pick the voice backend to use from the fallback chain."""
    env = environ if environ is not None else os.environ
    avail = available if available is not None else _detect(VOICE_FALLBACK_CHAIN, _VOICE_ENV, env)
    avail = set(avail)
    avail.add(VOICE_FALLBACK_CHAIN[-1])  # text is always available
    return _select(VOICE_FALLBACK_CHAIN, avail)


def select_posting(available: set[str] | None = None, *, environ: dict | None = None) -> dict:
    """Pick the posting backend to use from the fallback chain."""
    env = environ if environ is not None else os.environ
    avail = (
        available if available is not None
        else _detect(POSTING_FALLBACK_CHAIN, _POSTING_ENV, env)
    )
    avail = set(avail)
    avail.add(POSTING_FALLBACK_CHAIN[-1])  # CSV is always available
    return _select(POSTING_FALLBACK_CHAIN, avail)


def fallback_status(*, environ: dict | None = None) -> dict:
    """Both chains, what's available, and which link is selected right now."""
    voice = select_voice(environ=environ)
    posting = select_posting(environ=environ)
    return {
        "voice": voice,
        "posting": posting,
        "all_degraded": voice["terminal_fallback"] and posting["terminal_fallback"],
        "ok": True,  # selection can never fail — terminal links are always available
    }
