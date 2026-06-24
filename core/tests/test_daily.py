from invisable_os.engines.daily import DAILY_BRIEF, DailyContentDirector


def test_daily_brief_is_twenty_posts():
    assert len(DAILY_BRIEF) == 20


def test_plan_day_produces_a_full_day():
    plan = DailyContentDirector().plan_day(candidates_per_slot=8)
    summary = plan.summary()
    assert summary["total"] == 20
    # Every post is spun into a family of assets (the flywheel).
    assert summary["total_assets"] >= 20 * 5
    # Each post carries a mission verdict and a quality average.
    assert all("mission_verdict" in p for p in summary["posts"])
    assert all(p["quality_avg"] >= 0 for p in summary["posts"])


def test_plan_day_covers_multiple_pillars():
    plan = DailyContentDirector().plan_day(candidates_per_slot=8)
    by_pillar = plan.summary()["by_pillar"]
    # The day spans education, community, humour, founder, partner, trends.
    assert len(by_pillar) >= 4
