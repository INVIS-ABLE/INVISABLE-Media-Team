"""Central configuration for INVISABLE OS.

All settings are read from the environment (see ``.env.example``). Every value has
a safe default so the platform boots and is testable without any credentials — it
simply runs in a *degraded but functional* mode, falling back to deterministic
behaviour wherever an external service would normally be called.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration, populated from environment variables."""

    model_config = SettingsConfigDict(
        env_prefix="INVISABLE_",
        env_file=".env",
        extra="ignore",
        case_sensitive=False,
    )

    # --- Core ---------------------------------------------------------------
    env: str = "development"
    api_host: str = "0.0.0.0"
    api_port: int = 8080
    log_level: str = "INFO"

    # --- Brand / Founder ----------------------------------------------------
    brand_name: str = "INVISABLE"
    founder_name: str = "Stephen Garnham"
    founder_presence_target: float = Field(
        default=0.80,
        ge=0.0,
        le=1.0,
        description="Target share of published content that centres the founder.",
    )

    # --- LLMs (read without the INVISABLE_ prefix where the vendor name owns it) -
    claude_model: str = "claude-opus-4-8"
    claude_fast_model: str = "claude-sonnet-4-6"
    ollama_model: str = "qwen2.5:14b"

    @property
    def has_claude(self) -> bool:
        import os

        return bool(os.getenv("ANTHROPIC_API_KEY"))

    @property
    def api_key(self) -> str | None:
        """Optional API key gating the /v1 surface.

        When ``INVISABLE_API_KEY`` is unset the API is open (the offline/dev
        default); when set, every /v1 request must present it via ``X-API-Key``.
        Read live so it can be toggled without rebuilding the app.
        """
        import os

        return os.getenv("INVISABLE_API_KEY") or None

    @property
    def anthropic_api_key(self) -> str | None:
        import os

        return os.getenv("ANTHROPIC_API_KEY")

    @property
    def ollama_base_url(self) -> str:
        import os

        return os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

    @property
    def database_url(self) -> str:
        import os

        return os.getenv(
            "DATABASE_URL",
            "postgresql+asyncpg://invisable:invisable@localhost:5432/invisable",
        )

    @property
    def chroma_host(self) -> str:
        import os

        return os.getenv("CHROMA_HOST", "localhost")

    @property
    def chroma_port(self) -> int:
        import os

        return int(os.getenv("CHROMA_PORT", "8000"))


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide settings singleton."""
    return Settings()
