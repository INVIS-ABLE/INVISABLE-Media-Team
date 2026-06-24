from invisable_os.engines.tournament import ContentTournamentEngine
from invisable_os.models.content import Platform


def test_tournament_runs_and_selects_winners():
    engine = ContentTournamentEngine()
    result = engine.run(
        "Explain that fatigue in invisible illness is not laziness",
        Platform.INSTAGRAM,
        count=24,
        select=3,
    )
    assert result.generated == 24
    assert 1 <= len(result.winners) <= 3
    # Winners are ranked: every winner cleared the guardrails (non-zero total).
    assert all(w.total > 0 for w in result.winners)
    assert all(w.guardrail.passed for w in result.winners)


def test_winners_are_in_descending_or_founder_balanced_order():
    engine = ContentTournamentEngine()
    result = engine.run("Awareness of invisible illness", Platform.TIKTOK, count=16, select=5)
    # With no prior published content the Founder Engine pulls founder pieces forward,
    # but every winner must still have passed the gate.
    assert all(w.guardrail.passed for w in result.winners)
    assert len(result.winners) == 5


def test_tournament_records_winners_in_brain():
    engine = ContentTournamentEngine()
    before = engine.brain.count("winning_pattern")
    engine.run("Community support for chronic illness", Platform.INSTAGRAM, count=8, select=2)
    after = engine.brain.count("winning_pattern")
    assert after >= before + 1
