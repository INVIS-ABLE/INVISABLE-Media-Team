from invisable_os.engines.cultural import CulturalIntelligenceEngine
from invisable_os.engines.engagement import CommunityEngagement
from invisable_os.engines.founder import FounderEngine
from invisable_os.engines.harvester import IntelligenceHarvester
from invisable_os.engines.watchtower import AlgorithmWatchtower
from invisable_os.models.content import ContentCandidate, Platform
from invisable_os.models.metrics import PerformanceSignal, SuccessMetric

# --- Founder Engine ---------------------------------------------------------


def test_founder_balance_needs_founder_when_below_target():
    engine = FounderEngine()
    published = [
        ContentCandidate(brief="b", platform=Platform.INSTAGRAM, founder_centred=False)
        for _ in range(10)
    ]
    balance = engine.balance(published)
    assert balance.current == 0.0
    assert balance.needs_founder_next is True


def test_founder_rebalance_pulls_founder_forward():
    engine = FounderEngine()
    selected = [
        ContentCandidate(brief="b", platform=Platform.INSTAGRAM, founder_centred=False),
        ContentCandidate(brief="b", platform=Platform.INSTAGRAM, founder_centred=True),
    ]
    reordered = engine.rebalance(selected, published=[])
    assert reordered[0].founder_centred is True


# --- Cultural Engine --------------------------------------------------------


def test_cultural_resonance_rewards_british_register():
    engine = CulturalIntelligenceEngine()
    british, _ = engine.resonance("Proper knackered today mate, but chuffed to share this.")
    plain, _ = engine.resonance("I am very tired today but happy to share this.")
    assert british > plain


def test_cultural_flags_americanisms():
    engine = CulturalIntelligenceEngine()
    _, notes = engine.resonance("My favorite color is on vacation.")
    assert any("americanism" in n.lower() for n in notes)


# --- Watchtower -------------------------------------------------------------


def test_watchtower_founder_recognition_index_grows_with_recognition():
    wt = AlgorithmWatchtower()
    low = wt.founder_recognition_index({SuccessMetric.MEDIA_MENTIONS.value: 1})
    high = wt.founder_recognition_index(
        {
            SuccessMetric.MEDIA_MENTIONS.value: 20,
            SuccessMetric.PODCAST_INVITATIONS.value: 10,
            SuccessMetric.SPEAKING_OPPORTUNITIES.value: 8,
        }
    )
    assert 0.0 <= low < high <= 1.0


def test_watchtower_learns_from_saves():
    wt = AlgorithmWatchtower()
    report = wt.ingest(
        [
            PerformanceSignal(
                candidate_id="c1",
                platform="instagram",
                metric=SuccessMetric.SAVES,
                value=120,
                themes=["explainer"],
            )
        ]
    )
    assert report.learnings


# --- Harvester --------------------------------------------------------------


def test_harvester_returns_abstracted_signals():
    h = IntelligenceHarvester()
    signals = h.harvest(["invisible illness"])
    assert signals
    assert all(s.metadata.get("abstracted") for s in signals)


# --- Community Engagement ---------------------------------------------------


def test_engagement_comment_is_compliant():
    eng = CommunityEngagement()
    draft = eng.draft_comment("A creator sharing their chronic fatigue journey.")
    assert draft.approved
    assert draft.verdict.passed
