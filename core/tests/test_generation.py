"""Structured generation + the LLM-judge layered on the deterministic floor."""

from invisable_os.engines.generator import Generator
from invisable_os.engines.judge import LLMJudge
from invisable_os.engines.tournament import ContentTournamentEngine
from invisable_os.llm import JsonResponse, LLMResponse, extract_json
from invisable_os.models.content import ContentCandidate, Platform
from invisable_os.models.scoring import SCORE_WEIGHTS, ScoreCard


class FakeLLM:
    """Test double returning canned structured output."""

    def __init__(self, data: dict) -> None:
        self._data = data

    def complete_json(self, prompt, **kw) -> JsonResponse:
        return JsonResponse(data=self._data, backend="fake", model="fake-model")

    def complete(self, prompt, **kw) -> LLMResponse:
        return LLMResponse(text="", backend="fake", model="fake-model")


FULL_SCORES = {dim: 0.9 for dim in SCORE_WEIGHTS} | {"rationale": "strong, on-brand"}


# --- JSON extraction --------------------------------------------------------


def test_extract_json_handles_plain_and_fenced():
    assert extract_json('{"a": 1}') == {"a": 1}
    assert extract_json('```json\n{"a": 2}\n```') == {"a": 2}
    assert extract_json("here you go: {\"hook\": \"hi\"} cheers") == {"hook": "hi"}
    assert extract_json("not json at all") is None
    assert extract_json("") is None


def test_complete_json_offline_returns_none():
    from invisable_os.llm import get_llm

    resp = get_llm().complete_json("hi", schema_hint="x")
    assert resp.data is None
    assert resp.backend == "stub"


# --- Generator uses structured output when a model is present ----------------


def test_generator_uses_model_json_when_available():
    gen = Generator()
    gen.llm = FakeLLM({"hook": "Scroll-stopper", "body": "Real talk.", "call_to_action": "Share."})
    cands = gen.generate("awareness", Platform.INSTAGRAM, count=3)
    assert cands[0].hook == "Scroll-stopper"
    assert cands[0].body == "Real talk."
    assert cands[0].generator.startswith("fake:")


def test_generator_falls_back_to_template_on_empty_json():
    gen = Generator()
    gen.llm = FakeLLM({})  # malformed / empty → safe template
    cands = gen.generate("awareness", Platform.INSTAGRAM, count=2)
    assert cands[0].hook  # got a template, not blank
    assert cands[0].generator.startswith("stub:")


# --- LLM judge --------------------------------------------------------------


def test_judge_disabled_offline_returns_none():
    judge = LLMJudge()  # no key, no opt-in
    assert judge.available is False
    cand = ContentCandidate(brief="b", platform=Platform.INSTAGRAM, body="x")
    assert judge.score(cand) is None


def test_judge_scores_with_model():
    judge = LLMJudge(llm=FakeLLM(FULL_SCORES), force=True)
    assert judge.available is True
    card = judge.score(ContentCandidate(brief="b", platform=Platform.INSTAGRAM, hook="h", body="x"))
    assert card is not None
    assert card.trust == 0.9
    assert "judge(fake)" in card.rationale


def test_judge_blend_is_bounded_average():
    judge = LLMJudge(llm=FakeLLM(FULL_SCORES), force=True)
    det = ScoreCard(**{d: 0.2 for d in SCORE_WEIGHTS})
    jud = ScoreCard(**{d: 0.8 for d in SCORE_WEIGHTS})
    blended = judge.blend(det, jud)
    assert blended.trust == 0.5  # 0.5*0.2 + 0.5*0.8


def test_tournament_applies_judge_when_available():
    judge = LLMJudge(llm=FakeLLM(FULL_SCORES), force=True)
    engine = ContentTournamentEngine(judge=judge)
    result = engine.run("Awareness of invisible illness", Platform.INSTAGRAM, count=8, select=3)
    assert result.winners
    # The judge ran and its rationale is blended into the winners' scorecards.
    assert any("judge(fake)" in w.scorecard.rationale for w in result.winners)


def test_tournament_without_judge_stays_deterministic():
    engine = ContentTournamentEngine()  # default judge self-disables offline
    assert engine.judge.available is False
    result = engine.run("Awareness", Platform.INSTAGRAM, count=8, select=2)
    assert all("judge" not in w.scorecard.rationale for w in result.winners)
