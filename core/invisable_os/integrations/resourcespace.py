"""ResourceSpace (DAM) client — push finished assets into the asset library.

Implements ResourceSpace's signed API (``/api/?function=…&sign=…`` where
``sign = sha256(private_key + query)``). Used to sync produced/assembled media out of
local disk into a real Digital Asset Management system.

Raises on failure so the calling service can fall back to a dry-run; never used
directly by request handlers.
"""

from __future__ import annotations

import hashlib
import os
from urllib.parse import urlencode

import httpx


class ResourceSpaceClient:
    def __init__(
        self,
        base_url: str | None = None,
        user: str | None = None,
        private_key: str | None = None,
        *,
        client: httpx.Client | None = None,
    ) -> None:
        self.base_url = (base_url or os.getenv("RESOURCESPACE_URL", "")).rstrip("/")
        self.user = user or os.getenv("RESOURCESPACE_USER", "")
        self.private_key = private_key or os.getenv("RESOURCESPACE_PRIVATE_KEY", "")
        self._client = client or httpx.Client(timeout=20.0)

    @property
    def configured(self) -> bool:
        return bool(self.base_url and self.user and self.private_key)

    def _query(self, params: dict) -> str:
        base = urlencode({"user": self.user, **params})
        sign = hashlib.sha256((self.private_key + base).encode()).hexdigest()
        return f"{base}&sign={sign}"

    def call(self, function: str, **params) -> object:
        """Make a signed API call and return the parsed JSON (or text)."""
        query = self._query({"function": function, **params})
        resp = self._client.post(f"{self.base_url}/api/?{query}")
        resp.raise_for_status()
        try:
            return resp.json()
        except Exception:  # noqa: BLE001 — RS sometimes returns a bare scalar
            return resp.text.strip().strip('"')

    def create_resource(self, *, resource_type: int = 1, metadata: dict | None = None) -> str:
        """Create a resource and return its reference id."""
        ref = self.call(
            "create_resource",
            resource_type=resource_type,
            archive=0,
            metadata="" if metadata is None else _json(metadata),
        )
        return str(ref).strip().strip('"')

    def upload(self, ref: str, path: str) -> bool:
        """Attach a file to a resource via upload_multipart."""
        with open(path, "rb") as fh:
            query = self._query({"function": "upload_multipart", "ref": ref, "no_exif": 1})
            resp = self._client.post(
                f"{self.base_url}/api/?{query}", files={"file": (os.path.basename(path), fh)}
            )
        resp.raise_for_status()
        return True

    def sync_file(self, path: str, *, title: str = "", metadata: dict | None = None) -> dict:
        """Create a resource for ``path`` and upload it. Returns a ref + view URL."""
        meta = {"title": title or os.path.basename(path), **(metadata or {})}
        ref = self.create_resource(metadata=meta)
        self.upload(ref, path)
        return {"ref": ref, "url": f"{self.base_url}/?r={ref}", "title": meta["title"]}


def _json(obj: dict) -> str:
    import json

    return json.dumps(obj)
