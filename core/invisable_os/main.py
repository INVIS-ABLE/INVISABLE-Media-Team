"""FastAPI application entrypoint for INVISABLE OS.

    uvicorn invisable_os.main:app --reload

The app is the spine that makes the engines one platform: n8n workflows, Open WebUI,
and the daily content cycle all talk to these endpoints.
"""

from __future__ import annotations

import logging

from fastapi import FastAPI

from invisable_os import __version__
from invisable_os.api import router
from invisable_os.config import get_settings
from invisable_os.guardrails.policy import PRIME_DIRECTIVE


def create_app() -> FastAPI:
    settings = get_settings()
    logging.basicConfig(level=settings.log_level)

    app = FastAPI(
        title="INVISABLE® AI Media Agency OS",
        version=__version__,
        description=(
            "The central operating system of the INVISABLE® movement. "
            "Prime Directive: " + PRIME_DIRECTIVE
        ),
    )

    @app.get("/health")
    def health() -> dict:
        return {
            "status": "ok",
            "version": __version__,
            "brand": settings.brand_name,
            "founder": settings.founder_name,
            "founder_presence_target": settings.founder_presence_target,
            "claude_configured": settings.has_claude,
        }

    @app.get("/")
    def root() -> dict:
        return {
            "name": "INVISABLE® AI Media Agency OS",
            "prime_directive": PRIME_DIRECTIVE,
            "docs": "/docs",
        }

    app.include_router(router)
    return app


app = create_app()
