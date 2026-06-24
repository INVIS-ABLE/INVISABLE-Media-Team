from invisable_os.agents import AGENT_REGISTRY, get_agent, route, system_prompt_for
from invisable_os.engines.flywheel import ContentFlywheel
from invisable_os.engines.mission import MissionEngine
from invisable_os.engines.personality import (
    CONTENT_PERSONALITY_MIX,
    pillar_targets,
    rotate_styles,
)
from invisable_os.engines.quality import QualityEngine
from invisable_os.engines.tagging import TagNetwork
from invisable_os.models.content import ContentCandidate, Platform
from invisable_os.models.departments import TagNetworkMember

# --- Personality ------------------------------------------------------------


def test_personality_mix_sums_to_one():
    assert abs(sum(CONTENT_PERSONALITY_MIX.values()) - 1.0) < 1e-9


def test_pillar_targets_sum_to_total():
    targets = pillar_targets(20)
    assert sum(targets.values()) == 20


def test_rotate_styles_avoids_immediate_repeats():
    styles = rotate_styles(5)
    assert len(styles) == 5
    assert len(set(styles)) == 5


# --- Mission Advisor --------------------------------------------------------


def test_mission_advance_for_strong_mission_content():
    engine = MissionEngine()
    strong = ContentCandidate(
        brief="b",
        platform=Platform.INSTAGRAM,
        body=(
            "Invisible illness is real and you're not alone. This is why I started "
            "INVISABLE — our community deserves to be seen. The mission is honest awareness."
        ),
        founder_centred=True,
    )
    weak = ContentCandidate(brief="b", platform=Platform.INSTAGRAM, body="Nice weather today.")
    s_strong = engine.advise(strong)
    s_weak = engine.advise(weak)
    assert s_strong.total() > s_weak.total()
    assert s_strong.verdict == "advance"
    assert s_weak.verdict == "reject"


# --- Quality ----------------------------------------------------------------


def test_quality_score_dimensions_and_threshold():
    q = QualityEngine().score(
        ContentCandidate(
            brief="b",
            platform=Platform.INSTAGRAM,
            hook="“But you don't look ill.”",
            body="Honestly, here's why that hurts. You're not alone. Let me explain.",
            call_to_action="Share if this is you.",
        )
    )
    dims = q.dimensions()
    assert len(dims) == 11
    assert all(0.0 <= v <= 10.0 for v in dims.values())
    # passes() requires every dimension at/above the bar.
    assert q.passes() == all(v >= 8.0 for v in dims.values())


# --- Flywheel ---------------------------------------------------------------


def test_flywheel_spins_one_idea_into_many_assets():
    out = ContentFlywheel().spin(
        ContentCandidate(brief="Tool theft", platform=Platform.TIKTOK, hook="Not again.")
    )
    kinds = {a.kind for a in out.assets}
    assert {"tiktok", "reel", "caption", "quote_graphic", "carousel"} <= kinds
    assert len(out) >= 5
    assert out.future_idea


# --- Tag Network ------------------------------------------------------------


def test_tag_network_respects_rules():
    net = TagNetwork(
        [
            TagNetworkMember(display_name="A", instagram_handle="@a", tiktok_handle="@a_tt"),
            TagNetworkMember(display_name="B", instagram_handle="@b", paused=True),
            TagNetworkMember(display_name="C", instagram_handle="@c", do_not_tag=True),
            TagNetworkMember(display_name="D", instagram_handle="@d", approved=False),
        ]
    )
    sel = net.select(Platform.INSTAGRAM, max_tags=5)
    assert sel.handles == ["@a"]  # B paused, C do-not-tag, D not approved


def test_tag_network_platform_specific_handles():
    net = TagNetwork([TagNetworkMember(display_name="A", tiktok_handle="@a_tt")])
    # No instagram handle → nothing eligible on instagram.
    assert net.select(Platform.INSTAGRAM).handles == []
    assert net.select(Platform.TIKTOK).handles == ["@a_tt"]


def test_tag_network_caps_max_tags():
    members = [TagNetworkMember(display_name=str(i), instagram_handle=f"@u{i}") for i in range(10)]
    sel = TagNetwork(members).select(Platform.INSTAGRAM, max_tags=3)
    assert len(sel.handles) == 3


# --- Agent Library ----------------------------------------------------------


def test_agent_registry_populated_and_prompts_carry_guardrails():
    assert len(AGENT_REGISTRY) >= 30
    brand = get_agent("Brand Guardian")
    assert brand is not None
    assert "PRIME DIRECTIVE" in brand.system_prompt()


def test_agent_router_matches_relevant_specialists():
    names = [a.name for a in route("write a funny tiktok hook about tool theft")]
    assert any("Hook" in n or "Humour" in n for n in names)
    assert system_prompt_for("Mission Alignment Agent") is not None
