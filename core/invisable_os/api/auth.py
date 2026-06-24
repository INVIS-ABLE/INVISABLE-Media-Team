"""Optional API-key authentication for the /v1 surface.

The platform is **open by default** — with no ``INVISABLE_API_KEY`` set the API
behaves exactly as before, so offline runs, tests and local development need no
credentials. When the key *is* set, every ``/v1`` request must present it via the
``X-API-Key`` header (or ``Authorization: Bearer <key>``); otherwise it is rejected
with 401.

Health, root, the OpenAPI docs and the ``/app`` dashboard static files live outside
the guarded router and stay open so liveness probes and the installable PWA shell
keep working. For human access the recommended front line is still Cloudflare Access
in front of the tunnel; this key is the programmatic gate (n8n, scripts, the PWA's
stored key).

The key is read live from settings on every request, so it can be rotated or
toggled without rebuilding the app.
"""

from __future__ import annotations

from fastapi import Header, HTTPException

from invisable_os.config import get_settings


def require_api_key(
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    authorization: str | None = Header(default=None),
) -> None:
    """Reject the request unless it carries the configured API key (when one is set)."""
    expected = get_settings().api_key
    if not expected:  # auth disabled — open API
        return

    presented = x_api_key
    if not presented and authorization and authorization.lower().startswith("bearer "):
        presented = authorization[7:].strip()

    if presented != expected:
        raise HTTPException(status_code=401, detail="invalid or missing API key")
