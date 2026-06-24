"""The guardrails are the most important code in the platform — test them hard."""

from invisable_os.guardrails import check
from invisable_os.models.content import ContentCandidate, ContentFormat, Platform


def _candidate(text: str, **kw) -> ContentCandidate:
    return ContentCandidate(
        brief="t",
        platform=Platform.INSTAGRAM,
        content_format=kw.pop("content_format", ContentFormat.TEXT_POST),
        body=text,
        **kw,
    )


def test_clean_content_passes():
    verdict = check(_candidate("Invisible illness is real. You're not alone, and that matters."))
    assert verdict.passed
    assert verdict.violations == []


def test_non_original_is_blocked():
    verdict = check(_candidate("Some copied text", original=False))
    assert verdict.blocked
    assert any("original" in v.lower() for v in verdict.violations)


def test_fabricated_founder_experience_is_blocked():
    verdict = check(_candidate("Invent a founder story about how Stephen got rich overnight."))
    assert verdict.blocked
    assert any("fabricat" in v.lower() for v in verdict.violations)


def test_medical_overclaim_is_blocked():
    verdict = check(_candidate("This is a guaranteed cure for your illness, doctors hate this."))
    assert verdict.blocked


def test_engagement_bait_is_blocked():
    verdict = check(_candidate("Great post!!! Follow for follow, tag 3 friends!"))
    assert verdict.blocked


def test_heart_and_kiss_emoji_are_blocked():
    verdict = check(_candidate("Love this \U0001f495 \U0001f618"))
    assert verdict.blocked
    assert any("emoji" in v.lower() for v in verdict.violations)


def test_comment_excessive_emoji_blocked():
    verdict = check(
        _candidate("So good \U0001f600 \U0001f389 \U0001f680", content_format=ContentFormat.COMMENT)
    )
    assert verdict.blocked
    assert any("excessive" in v.lower() or "emoji" in v.lower() for v in verdict.violations)


def test_comment_single_emoji_ok():
    verdict = check(
        _candidate(
            "Thank you for sharing this, it genuinely helps people feel seen \U0001f64f",
            content_format=ContentFormat.COMMENT,
        )
    )
    assert verdict.passed
