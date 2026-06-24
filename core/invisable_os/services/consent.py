"""Consent gating — the values rule that a real person is never used without
explicit, current authorisation, expressed in code.

A person is *usable* only when their consent is ``approved`` **and** not past its
expiry date. This helper is the single place that decision lives, so the People
screen, the Relationship CRM, and any future publish-time check all agree. When
content gains an explicit person link, the publish path can call
:func:`consent_state` to hard-gate features of unconsented or expired people.
"""

from __future__ import annotations

from datetime import date


def consent_state(person: dict, today: str | None = None) -> dict:
    """Return ``{usable, reason, expired}`` for a person dict.

    ``reason`` is ``"ok"`` when usable, otherwise the blocking cause
    (``"pending" | "declined" | "expired"``).
    """
    today = today or date.today().isoformat()
    status = person.get("consent_status", "pending")
    expiry = person.get("consent_expiry")
    expired = bool(expiry and str(expiry) < today)

    if status == "approved" and not expired:
        return {"usable": True, "reason": "ok", "expired": False}
    reason = "expired" if (status == "approved" and expired) else status
    return {"usable": False, "reason": reason, "expired": expired}
