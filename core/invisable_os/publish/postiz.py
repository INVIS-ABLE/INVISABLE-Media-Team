"""Postiz publisher — publish/schedule approved content via a Postiz instance.

Two posting modes back the **Postiz Scheduler Agent**:

* :meth:`PostizPublisher.publish` — post now;
* :meth:`PostizPublisher.schedule` — hand Postiz a future date so it posts natively.

The payload is built by a **pure function** (:func:`build_postiz_payload`) so it is
unit-tested without a live Postiz, and the HTTP transport is injectable (an
``httpx`` transport) so the network path is tested with ``httpx.MockTransport``.
When Postiz isn't configured the publisher degrades to a clear, non-throwing result
so the scheduler keeps running — exactly like the renderers/probes.

Channel mapping: Postiz posts go to *integration* ids, not platform names. Map our
``Platform`` → Postiz integration id via the ``POSTIZ_INTEGRATIONS`` env (JSON, e.g.
``{"instagram": "intg_1", "tiktok": "intg_2"}``) or pass ``integrations=`` directly.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime

import httpx

from invisable_os.publish.base import PublishResult

log = logging.getLogger(__name__)

DEFAULT_POSTS_PATH = "/public/v1/posts"
DEFAULT_INTEGRATIONS_PATH = "/public/v1/integrations"


def _load_integrations() -> dict[str, str]:
    raw = os.getenv("POSTIZ_INTEGRATIONS", "")
    if not raw:
        return {}
    try:
        data = json.loads(raw)
        return {str(k).lower(): str(v) for k, v in data.items()} if isinstance(data, dict) else {}
    except (ValueError, TypeError):
        log.warning("POSTIZ_INTEGRATIONS is not valid JSON; ignoring")
        return {}


def post_text(item: dict) -> str:
    """The publishable text for a queue item — hook, body, CTA joined."""
    candidate = item.get("candidate", {})
    parts = (candidate.get("hook"), candidate.get("body"), candidate.get("call_to_action"))
    return "\n\n".join(p for p in parts if p).strip()


def build_postiz_payload(
    item: dict,
    integrations: dict[str, str],
    *,
    when: datetime | None = None,
) -> dict:
    """Build the Postiz ``/posts`` payload for a queue item (pure, unit-tested).

    ``when`` set → a scheduled post at that time; otherwise post now. The item's
    platform is mapped to its Postiz integration id; an unmapped platform yields an
    empty integration list (the caller surfaces that as a clear error).
    """
    platform = str(item.get("platform", "")).lower()
    integration_id = integrations.get(platform)
    text = post_text(item)

    post: dict = {"content": text}
    if integration_id:
        post["integration"] = {"id": integration_id}

    payload: dict = {
        "type": "schedule" if when else "now",
        "tags": item.get("tags", []),
        "posts": [post],
    }
    if when:
        # Postiz expects an ISO-8601 timestamp.
        payload["date"] = when.isoformat()
    return payload


class PostizPublisher:
    name = "postiz"

    def __init__(
        self,
        *,
        base_url: str | None = None,
        api_key: str | None = None,
        integrations: dict[str, str] | None = None,
        transport: httpx.BaseTransport | None = None,
        posts_path: str | None = None,
        timeout: float = 10.0,
    ) -> None:
        base = base_url if base_url is not None else os.getenv("POSTIZ_API_URL", "")
        self.base_url = base.rstrip("/")
        self.api_key = api_key if api_key is not None else os.getenv("POSTIZ_API_KEY", "")
        self.integrations = integrations if integrations is not None else _load_integrations()
        self.posts_path = posts_path or os.getenv("POSTIZ_POSTS_PATH", DEFAULT_POSTS_PATH)
        self._transport = transport
        self._timeout = timeout

    @property
    def configured(self) -> bool:
        return bool(self.base_url and self.api_key)

    def integration_for(self, platform: str) -> str | None:
        return self.integrations.get(str(platform).lower())

    def publish(self, item: dict) -> PublishResult:
        """Post an item now."""
        return self._send(item, when=None)

    def schedule(self, item: dict, when: datetime) -> PublishResult:
        """Hand Postiz a future post so it schedules natively."""
        return self._send(item, when=when)

    def _client(self) -> httpx.Client:
        return httpx.Client(
            base_url=self.base_url,
            timeout=self._timeout,
            transport=self._transport,
            headers={"Authorization": f"Bearer {self.api_key}"},
        )

    def _send(self, item: dict, *, when: datetime | None) -> PublishResult:
        if not self.configured:
            return PublishResult(ok=False, backend=self.name, detail="Postiz not configured")
        if not self.integration_for(item.get("platform", "")):
            return PublishResult(
                ok=False, backend=self.name,
                detail=f"no Postiz integration mapped for platform '{item.get('platform')}'",
            )
        payload = build_postiz_payload(item, self.integrations, when=when)
        action = "scheduled" if when else "posted"
        try:
            with self._client() as client:
                resp = client.post(self.posts_path, json=payload)
                resp.raise_for_status()
                data = resp.json() if resp.content else {}
            external_id = str(data.get("id") or data.get("postId") or "")
            detail = f"{action}" + (f" for {when.isoformat()}" if when else "")
            return PublishResult(ok=True, backend=self.name, external_id=external_id, detail=detail)
        except Exception as exc:  # noqa: BLE001 — degrade, never crash the scheduler
            log.warning("Postiz %s failed: %s", action, exc)
            return PublishResult(ok=False, backend=self.name, detail=str(exc))
