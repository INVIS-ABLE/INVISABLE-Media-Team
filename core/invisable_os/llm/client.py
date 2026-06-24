"""A small, dependency-light LLM client with graceful degradation.

Resolution order:

1. **Claude** via the ``anthropic`` SDK, if ``ANTHROPIC_API_KEY`` is set and the
   SDK is installed.
2. **Ollama** over HTTP, if it is reachable.
3. **Deterministic stub**, otherwise — never raises, always returns something
   usable so upstream engines keep working.

The interface is intentionally tiny: ``complete(system, prompt)``.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import httpx

from invisable_os.config import Settings, get_settings

log = logging.getLogger(__name__)


@dataclass
class LLMResponse:
    text: str
    backend: str
    model: str


class LLMClient:
    """Unified completion client across Claude, Ollama, and a stub fallback."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    # -- public API ----------------------------------------------------------

    def complete(
        self,
        prompt: str,
        *,
        system: str = "",
        max_tokens: int = 1024,
        prefer_fast: bool = False,
    ) -> LLMResponse:
        """Return a completion, trying Claude → Ollama → stub."""
        if self.settings.has_claude:
            try:
                return self._complete_claude(
                    prompt, system=system, max_tokens=max_tokens, prefer_fast=prefer_fast
                )
            except Exception as exc:  # noqa: BLE001 — degrade, never crash the OS
                log.warning("Claude backend failed, falling back: %s", exc)

        try:
            return self._complete_ollama(prompt, system=system, max_tokens=max_tokens)
        except Exception as exc:  # noqa: BLE001
            log.info("Ollama backend unavailable, using deterministic stub: %s", exc)

        return self._complete_stub(prompt, system=system)

    # -- backends ------------------------------------------------------------

    def _complete_claude(
        self, prompt: str, *, system: str, max_tokens: int, prefer_fast: bool
    ) -> LLMResponse:
        from anthropic import Anthropic  # imported lazily; optional dependency

        client = Anthropic(api_key=self.settings.anthropic_api_key)
        model = (
            self.settings.claude_fast_model if prefer_fast else self.settings.claude_model
        )
        message = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system or "You are INVISABLE OS, a values-driven media assistant.",
            messages=[{"role": "user", "content": prompt}],
        )
        text = "".join(
            block.text for block in message.content if getattr(block, "type", "") == "text"
        )
        return LLMResponse(text=text, backend="claude", model=model)

    def _complete_ollama(
        self, prompt: str, *, system: str, max_tokens: int
    ) -> LLMResponse:
        url = f"{self.settings.ollama_base_url.rstrip('/')}/api/generate"
        payload = {
            "model": self.settings.ollama_model,
            "prompt": prompt,
            "system": system,
            "stream": False,
            "options": {"num_predict": max_tokens},
        }
        with httpx.Client(timeout=5.0) as client:
            resp = client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
        return LLMResponse(
            text=data.get("response", ""), backend="ollama", model=self.settings.ollama_model
        )

    def _complete_stub(self, prompt: str, *, system: str) -> LLMResponse:
        """Deterministic, offline fallback.

        It does not pretend to be clever — it echoes a structured, safe response so
        engines that call the LLM still produce coherent (if plain) output. Crucially
        it never fabricates a story or a founder experience.
        """
        head = prompt.strip().splitlines()[0] if prompt.strip() else "(empty prompt)"
        text = (
            "[offline-stub] No live model configured. "
            f"Acknowledged request: {head[:160]}"
        )
        return LLMResponse(text=text, backend="stub", model="deterministic-stub")


_singleton: LLMClient | None = None


def get_llm() -> LLMClient:
    """Return a process-wide LLM client."""
    global _singleton
    if _singleton is None:
        _singleton = LLMClient()
    return _singleton
