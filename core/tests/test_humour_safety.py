"""The refined humour rules: laugh WITH the community, never punch down."""

from invisable_os.guardrails import check, risk_scan, swear_level
from invisable_os.models.content import ContentCandidate, ContentFormat, Platform


def _c(text: str, **kw) -> ContentCandidate:
    return ContentCandidate(
        brief="t",
        platform=Platform.TIKTOK,
        content_format=kw.pop("content_format", ContentFormat.SHORT_VIDEO),
        body=text,
        **kw,
    )


def test_self_deprecating_humour_is_allowed():
    for joke in (
        "My immune system called in sick before I did.",
        "The van starts more reliably than I do.",
        "Tool theft wasn't enough, so my body joined in.",
    ):
        assert check(_c(joke)).passed, joke


def test_natural_british_swearing_is_allowed():
    verdict = check(_c("For fuck sake, the van got nicked again. What a bloody nightmare."))
    assert verdict.passed
    assert verdict.swear_level == "strong"


def test_swear_level_classification():
    assert swear_level("this is bloody annoying") == "light"
    assert swear_level("what a load of bollocks") == "moderate"
    assert swear_level("absolutely fucked it") == "strong"
    assert swear_level("a perfectly clean sentence") == "none"


def test_punching_down_is_blocked():
    verdict = check(_c("Honestly, disabled people are just lazy and need to get over it."))
    assert verdict.blocked
    assert any("punching down" in v.lower() for v in verdict.violations)


def test_slur_is_blocked():
    verdict = check(_c("That's so spastic."))
    assert verdict.blocked
    assert any("slur" in v.lower() for v in verdict.violations)


def test_harassment_of_individual_is_blocked():
    verdict = check(_c("You're pathetic and nobody likes you."))
    assert verdict.blocked


def test_first_person_frustration_about_groups_context_still_allowed():
    # Self-referential frustration is allowed even if it mentions struggle.
    verdict = check(_c("I'm so done with feeling like a burden on my worst days."))
    assert verdict.passed


def test_medical_advice_is_advisory_risk_not_block():
    verdict = check(_c("Honestly when you have a flare, rest helps me more than pushing through."))
    # 'you have' triggers the advisory medical flag but does not hard-block.
    assert "medical_advice" in verdict.risk_flags
    assert verdict.passed
    assert verdict.needs_human_review


def test_risk_scan_flags_benefits_content():
    flags = risk_scan("Here's what the new PIP and universal credit changes mean.")
    assert "benefits_advice" in flags
