from invisable_os.engines.scoring import Scorer
from invisable_os.models.content import ContentCandidate, Platform
from invisable_os.models.scoring import SCORE_WEIGHTS, ScoreCard


def test_score_weights_sum_to_one():
    assert abs(sum(SCORE_WEIGHTS.values()) - 1.0) < 1e-9


def test_weighted_total_bounds():
    full = ScoreCard(**{k: 1.0 for k in SCORE_WEIGHTS})
    empty = ScoreCard()
    assert abs(full.weighted_total() - 1.0) < 1e-9
    assert empty.weighted_total() == 0.0


def test_substantive_content_outscores_thin_content():
    scorer = Scorer()
    rich = ContentCandidate(
        brief="b",
        platform=Platform.INSTAGRAM,
        hook="“But you don't look ill.”",
        body=(
            "Here's why that hurts: invisible illness is invisible. Let me explain — "
            "you're not alone, and honestly there's no quick fix. The reality is hard."
        ),
        call_to_action="Share your experience if this is you.",
    )
    thin = ContentCandidate(
        brief="b", platform=Platform.INSTAGRAM, hook="hi", body="ok"
    )
    assert scorer.score(rich).weighted_total() > scorer.score(thin).weighted_total()


def test_founder_content_lifts_authenticity():
    scorer = Scorer()
    founder = ContentCandidate(
        brief="b",
        platform=Platform.INSTAGRAM,
        body="As the founder, I started INVISABLE because this matters.",
        founder_centred=True,
    )
    plain = ContentCandidate(brief="b", platform=Platform.INSTAGRAM, body="Some content here.")
    assert scorer.score(founder).authenticity >= scorer.score(plain).authenticity
