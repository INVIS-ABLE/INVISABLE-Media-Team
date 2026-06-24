"""Community Engagement.

Generates and vets comments and replies. Engagement exists to *strengthen
relationships, build trust, support creators, and represent INVISABLE®
professionally* — never to farm reach.

Rules (from the directive), enforced via the shared guardrails:

* be respectful, supportive, positive, constructive, authentic;
* avoid spam comments, generic engagement bait, heart/kiss/flirtatious emoji, and
  excessive emoji use.

A drafted comment is only returned if it passes the guardrails; otherwise the
engine reports why and (offline) falls back to a clean, compliant template.
"""

from __future__ import annotations

from dataclasses import dataclass

from invisable_os.guardrails import check
from invisable_os.llm import get_llm
from invisable_os.models.content import ContentCandidate, ContentFormat, Platform
from invisable_os.models.scoring import GuardrailVerdict


@dataclass
class CommentDraft:
    text: str
    approved: bool
    verdict: GuardrailVerdict


class CommunityEngagement:
    """Drafts professional, compliant community comments."""

    def __init__(self) -> None:
        self.llm = get_llm()

    def draft_comment(
        self,
        post_summary: str,
        *,
        platform: Platform = Platform.INSTAGRAM,
        creator: str | None = None,
    ) -> CommentDraft:
        """Draft a supportive, constructive comment about a creator's post."""
        system = (
            "You write comments on behalf of INVISABLE®, an invisible-illness awareness "
            "movement. Be respectful, supportive, positive, constructive and authentic. "
            "No engagement-bait, no spam, no heart/kiss/flirtatious emoji, minimal emoji. "
            "Add genuine value or encouragement; never make it about us."
        )
        prompt = (
            f"Creator: {creator or 'a fellow creator'} on {platform.value}.\n"
            f"Their post (summary): {post_summary}\n"
            "Write one short, warm, specific comment."
        )
        response = self.llm.complete(prompt, system=system, max_tokens=120, prefer_fast=True)
        text = response.text.strip() if response.backend != "stub" else self._template(post_summary)

        candidate = ContentCandidate(
            brief=f"comment on: {post_summary}",
            platform=platform,
            content_format=ContentFormat.COMMENT,
            body=text,
            original=True,
        )
        verdict = check(candidate)
        if verdict.blocked:
            # Never ship a non-compliant comment — fall back to a clean template.
            text = self._template(post_summary)
            candidate.body = text
            verdict = check(candidate)
        return CommentDraft(text=text, approved=verdict.passed, verdict=verdict)

    def _template(self, post_summary: str) -> str:
        return (
            "Really appreciate you sharing this — talking about it openly helps more "
            "people feel seen. Thank you for using your voice."
        )
