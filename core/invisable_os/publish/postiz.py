"""Postiz publisher.

Posts approved content via a Postiz instance. Falls back to a clear error result
(never an exception) so the scheduler keeps running if Postiz is unreachable.
"""

from __future__ import annotations

import logging
import os

import httpx

from invisable_os.publish.base import PublishResult

log = logging.getLogger(__name__)


class PostizPublisher:
    name = "postiz"

    def __init__(self) -> None:
        self.base_url = os.getenv("POSTIZ_API_URL", "").rstrip("/")
        self.api_key = os.getenv("POSTIZ_API_KEY", "")

    @property
    def configured(self) -> bool:
        return bool(self.base_url and self.api_key)

    def publish(self, item: dict) -> PublishResult:
        if not self.configured:
            return PublishResult(ok=False, backend=self.name, detail="Postiz not configured")
        candidate = item.get("candidate", {})
        parts = (candidate.get("hook"), candidate.get("body"), candidate.get("call_to_action"))
        text = "\n\n".join(p for p in parts if p)
        payload = {
            "content": text,
            "platform": item.get("platform"),
            "tags": item.get("tags", []),
        }
        try:
            with httpx.Client(timeout=10.0) as client:
                resp = client.post(
                    f"{self.base_url}/api/posts",
                    json=payload,
                    headers={"Authorization": f"Bearer {self.api_key}"},
                )
                resp.raise_for_status()
                data = resp.json()
            return PublishResult(
                ok=True, backend=self.name, external_id=str(data.get("id", "")), detail="posted"
            )
        except Exception as exc:  # noqa: BLE001 — degrade, never crash the scheduler
            log.warning("Postiz publish failed: %s", exc)
            return PublishResult(ok=False, backend=self.name, detail=str(exc))
