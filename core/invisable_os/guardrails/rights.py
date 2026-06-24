"""Rights & copyright guardrail — the Remix department's hard gate.

The Remix, Parody & Trend Intelligence Engine may *analyse, reference, parody,
react to, transform, summarise, and create inspired content*. It must **never**
automatically download and reupload other people's videos as-is.

This module encodes that rule as enforced behaviour, exactly like the Prime
Directive in :mod:`invisable_os.guardrails.engine`:

* :func:`can_reuse`      — may this rights status appear in generated media at all?
* :func:`can_download`   — may yt-dlp fetch this reference?
* :func:`reuse_check`    — verify an asset (or list) before it enters production.

The deterministic rule is simple and unbypassable: only the six *usable* statuses
(owned, licensed, public_domain, creative_commons, user_submitted_consent,
platform_duet_stitch) may be reused. ``reference_only`` and ``blocked`` never can.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from invisable_os.models.remix import (
    USABLE_RIGHTS,
    PermittedAsset,
    RightsStatus,
    VideoReference,
    is_usable,
)

# Verbatim, for display and logging — the department's version of a directive.
RIGHTS_RULE = (
    "The system must not automatically download, repost, or reupload other "
    "people's videos as-is. It may analyse trends, store links as references, "
    "transcribe permitted content for analysis, and create original, parody, "
    "commentary, or voiceover content over owned/licensed/permitted footage. "
    "Reference-only material can inspire ideas but can never be reuploaded."
)


class RightsVerdict(BaseModel):
    """The outcome of a rights check — mirrors :class:`GuardrailVerdict`'s shape."""

    passed: bool
    violations: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


def can_reuse(status: RightsStatus | str) -> bool:
    """True if media with this rights status may be used in generated output."""
    return is_usable(status)


def can_download(reference: VideoReference) -> bool:
    """True only if yt-dlp may fetch this reference (usable rights, not blocked)."""
    return reference.downloadable


def reuse_check(
    assets: PermittedAsset | VideoReference | list[PermittedAsset | VideoReference],
) -> RightsVerdict:
    """Gate one or more media items before they enter production.

    Any item whose rights status is not usable is a hard violation — the whole
    check fails, exactly like the content guardrails. ``reference_only`` items are
    called out explicitly so the operator understands they may inspire but not be
    reuploaded.
    """
    items = assets if isinstance(assets, list) else [assets]
    violations: list[str] = []
    notes: list[str] = []

    for item in items:
        status = RightsStatus(item.rights_status)
        label = getattr(item, "title", None) or getattr(item, "url", "") or item.id
        if status in USABLE_RIGHTS:
            continue
        if status == RightsStatus.REFERENCE_ONLY:
            violations.append(
                f"'{label}' is reference_only — it may inspire ideas but must never "
                "be downloaded or reuploaded as-is."
            )
        elif status == RightsStatus.BLOCKED:
            violations.append(f"'{label}' is blocked — do not use in any form.")
        else:
            violations.append(f"'{label}' has unusable rights status '{status}'.")

    passed = not violations
    if passed:
        notes.append("All media cleared for reuse. " + RIGHTS_RULE)
    return RightsVerdict(passed=passed, violations=violations, notes=notes)


def filter_usable(
    assets: list[PermittedAsset | VideoReference],
) -> list[PermittedAsset | VideoReference]:
    """Return only the items whose rights status permits reuse."""
    return [a for a in assets if is_usable(a.rights_status)]
