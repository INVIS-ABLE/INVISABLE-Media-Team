"""Content Flywheel.

One idea must never be one asset. Every winning idea is spun into a family of
assets so a single insight produces 5–10 pieces of content:

    a TikTok · an Instagram Reel · a caption · a quote graphic · a carousel angle
    · a story poll · a comment-response opportunity · a future content idea

This is the difference between a content factory and a media organisation: leverage.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from invisable_os.models.content import ContentCandidate, ContentFormat, Platform


@dataclass
class Asset:
    """A single derived asset spec, ready for the relevant production department."""

    kind: str  # tiktok | reel | caption | quote_graphic | carousel | story_poll | ...
    platform: Platform
    content_format: ContentFormat
    brief: str
    hook: str = ""


@dataclass
class FlywheelOutput:
    seed_id: str
    seed_hook: str
    assets: list[Asset] = field(default_factory=list)
    future_idea: str = ""

    def __len__(self) -> int:
        return len(self.assets)


class ContentFlywheel:
    """Turns one candidate into a family of derived assets."""

    def spin(self, seed: ContentCandidate) -> FlywheelOutput:
        topic = seed.brief.strip().rstrip(".")
        hook = seed.hook or f"Something about {topic.lower()}"
        body = seed.body

        assets = [
            Asset(
                kind="tiktok",
                platform=Platform.TIKTOK,
                content_format=ContentFormat.SHORT_VIDEO,
                brief=f"15–30s TikTok from: {topic}",
                hook=hook,
            ),
            Asset(
                kind="reel",
                platform=Platform.INSTAGRAM,
                content_format=ContentFormat.SHORT_VIDEO,
                brief=f"30–45s Instagram Reel from: {topic}",
                hook=hook,
            ),
            Asset(
                kind="caption",
                platform=seed.platform,
                content_format=ContentFormat.TEXT_POST,
                brief=f"Caption for the post: {body[:120]}",
                hook=hook,
            ),
            Asset(
                kind="quote_graphic",
                platform=Platform.INSTAGRAM,
                content_format=ContentFormat.IMAGE,
                brief=f"Quote card pulling the strongest line from: {topic}",
                hook=hook,
            ),
            Asset(
                kind="carousel",
                platform=Platform.INSTAGRAM,
                content_format=ContentFormat.CAROUSEL,
                brief=f"5-slide carousel explaining: {topic}",
                hook=hook,
            ),
            Asset(
                kind="story_poll",
                platform=Platform.INSTAGRAM,
                content_format=ContentFormat.STORY,
                brief=f"Story poll inviting the community to weigh in on: {topic}",
                hook=hook,
            ),
            Asset(
                kind="comment_response",
                platform=seed.platform,
                content_format=ContentFormat.COMMENT,
                brief=f"A supportive comment-response angle for discussions about: {topic}",
                hook=hook,
            ),
        ]
        return FlywheelOutput(
            seed_id=seed.id,
            seed_hook=hook,
            assets=assets,
            future_idea=f"Follow-up: a deeper take on '{topic}' from a different angle next week.",
        )
