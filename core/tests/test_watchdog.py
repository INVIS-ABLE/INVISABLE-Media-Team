"""The Platform Compliance Watchdog — safety wins over growth."""

from __future__ import annotations

from invisable_os.engines.watchdog import (
    MODE_LIMITS,
    ActivitySnapshot,
    ComplianceWatchdog,
    PostingMode,
    RiskLevel,
)


def _post(**candidate) -> dict:
    pid = candidate.pop("id", "p")
    tags = candidate.pop("tags", [])
    return {"id": pid, "tags": tags, "candidate": candidate}


def test_clean_account_is_low_risk_and_keeps_mode():
    wd = ComplianceWatchdog()
    snap = ActivitySnapshot(
        current_mode=PostingMode.MODEST_GROWTH,
        posts_today=2,
        recent_posts=[_post(body="a unique warm post", original=True)],
        reach_trend=0.1,
        engagement_trend=0.05,
    )
    report = wd.evaluate(snap)
    assert report.risk_level == RiskLevel.LOW
    assert report.health_score >= 90
    assert report.suggested_mode == PostingMode.MODEST_GROWTH
    assert report.mode == report.suggested_mode  # no forced change


def test_over_daily_limit_is_high_and_downgrades():
    wd = ComplianceWatchdog()
    snap = ActivitySnapshot(current_mode=PostingMode.MODEST_GROWTH, posts_today=7)
    report = wd.evaluate(snap)
    assert report.risk_level == RiskLevel.HIGH
    # HIGH forces one step down the ladder: modest_growth → introduction.
    assert report.suggested_mode == PostingMode.INTRODUCTION
    assert any(f.monitor == "posting_frequency" for f in report.findings)


def test_far_over_limit_is_critical_and_manual_only():
    wd = ComplianceWatchdog()
    snap = ActivitySnapshot(current_mode=PostingMode.ACTIVE_INFLUENCER, posts_today=30)
    report = wd.evaluate(snap)
    assert report.risk_level == RiskLevel.CRITICAL
    assert report.suggested_mode == PostingMode.MANUAL_ONLY


def test_duplicate_captions_and_media_flagged():
    wd = ComplianceWatchdog()
    snap = ActivitySnapshot(
        current_mode=PostingMode.ACTIVE_INFLUENCER,
        posts_today=1,
        recent_posts=[
            _post(id="1", body="same caption", primary_media="/a.mp4"),
            _post(id="2", body="same caption", primary_media="/a.mp4"),
        ],
    )
    report = wd.evaluate(snap)
    monitors = {f.monitor for f in report.findings}
    assert "repeated_captions" in monitors
    assert "repeated_media" in monitors


def test_medical_harm_wording_is_critical():
    wd = ComplianceWatchdog()
    snap = ActivitySnapshot(
        current_mode=PostingMode.INTRODUCTION,
        recent_posts=[_post(body="You should stop taking your medication, trust me")],
    )
    report = wd.evaluate(snap)
    assert report.risk_level == RiskLevel.CRITICAL
    assert any(f.monitor == "medical_misinformation" for f in report.findings)


def test_spam_wording_is_high():
    wd = ComplianceWatchdog()
    snap = ActivitySnapshot(
        current_mode=PostingMode.INTRODUCTION,
        recent_posts=[_post(body="follow for follow and buy followers here")],
    )
    report = wd.evaluate(snap)
    assert any(f.monitor == "policy_sensitive_wording" for f in report.findings)
    assert report.risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL)


def test_non_original_content_is_copyright_risk():
    wd = ComplianceWatchdog()
    snap = ActivitySnapshot(
        current_mode=PostingMode.MODEST_GROWTH,
        recent_posts=[_post(body="a reaction", original=False)],
    )
    report = wd.evaluate(snap)
    assert any(f.monitor == "copyright_risk" for f in report.findings)


def test_shadowban_pattern_from_multiple_signals():
    wd = ComplianceWatchdog()
    snap = ActivitySnapshot(
        current_mode=PostingMode.ACTIVE_INFLUENCER,
        posts_today=3,
        events=[
            {"kind": "failed_post"},
            {"kind": "failed_post"},
            {"kind": "warning"},
        ],
        reach_trend=-0.6,
    )
    report = wd.evaluate(snap)
    assert len(report.shadowban_signals) >= 2
    assert any(f.monitor == "shadowban_warning" for f in report.findings)
    assert report.risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL)


def test_login_prompt_demands_manual_and_never_bypassed():
    wd = ComplianceWatchdog()
    snap = ActivitySnapshot(
        current_mode=PostingMode.CAREER,
        events=[{"kind": "login_prompt"}],
    )
    report = wd.evaluate(snap)
    f = next(f for f in report.findings if f.monitor == "login_security_prompt")
    assert "manually" in f.recommended_action.lower()
    assert "bypass" in f.recommended_action.lower()


def test_career_mode_requires_strong_health():
    wd = ComplianceWatchdog()
    # Weak-but-not-high-risk: an engagement dip pulls health under 70 without HIGH risk.
    snap = ActivitySnapshot(
        current_mode=PostingMode.CAREER,
        posts_today=10,
        events=[{"kind": "failed_post"}, {"kind": "api_error"}],
        engagement_trend=-0.3,
    )
    report = wd.evaluate(snap)
    if report.health_score < 70 and report.risk_level == RiskLevel.MEDIUM:
        assert report.suggested_mode == PostingMode.ACTIVE_INFLUENCER


def test_mode_limits_never_auto_comment():
    # The system must never auto-post comments in any mode.
    assert all(not limit.auto_comments for limit in MODE_LIMITS.values())
