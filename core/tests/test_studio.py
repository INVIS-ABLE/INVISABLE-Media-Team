"""The multi-agent production studio: team structure + its API surface."""

from fastapi.testclient import TestClient

from invisable_os.agents import AGENT_REGISTRY, TEAM_ORDER, Team, by_team, get_agent, pipeline
from invisable_os.main import app

client = TestClient(app)


# --- Team structure ---------------------------------------------------------


def test_every_agent_has_a_team_and_seven_teams_are_populated():
    assert {a.team for a in AGENT_REGISTRY} == set(Team)
    grouped = pipeline()
    assert list(grouped.keys()) == list(TEAM_ORDER)
    for team in Team:
        assert by_team(team), f"team {team} has no agents"


def test_pipeline_order_is_research_first_learning_last():
    assert TEAM_ORDER[0] == Team.RESEARCH
    assert TEAM_ORDER[-1] == Team.LEARNING


def test_headline_agents_present_and_carry_guardrails():
    for name in (
        "Visual Layout Agent", "Audio Quality Agent", "Copyright Risk Agent",
        "Postiz Scheduler Agent", "Founder Override Agent", "Performance Pattern Agent",
    ):
        agent = get_agent(name)
        assert agent is not None, name
        assert "PRIME DIRECTIVE" in agent.system_prompt()


def test_agent_names_are_unique():
    names = [a.name for a in AGENT_REGISTRY]
    assert len(names) == len(set(names))


# --- API surface ------------------------------------------------------------


def test_agents_teams_endpoint():
    data = client.get("/v1/agents/teams").json()
    assert data["pipeline"][0] == "research"
    assert set(data["teams"]) == {t.value for t in Team}
    assert any(a["name"] == "Visual Layout Agent" for a in data["teams"]["production"])


def test_safe_area_endpoint():
    data = client.get("/v1/safe-area", params={"platform": "tiktok", "surface": "reel"}).json()
    assert data["aspect"] == "9:16"
    assert {z["name"] for z in data["exclusions"]} >= {"top_ui", "right_rail", "bottom_caption_cta"}


def test_place_caption_endpoint_avoids_a_face():
    body = {
        "platform": "tiktok",
        "surface": "reel",
        "height": 0.12,
        "regions": [
            {"kind": "founder_face", "box": {"x0": 0.25, "y0": 0.55, "x1": 0.75, "y1": 0.85}}
        ],
    }
    data = client.post("/v1/layout/place-caption", json=body).json()
    assert data["ok"] is True
    box = data["box"]
    # The returned band must sit above the face (y1 <= 0.55).
    assert box["y1"] <= 0.56


def test_video_qc_endpoint_fails_a_bad_clip():
    spec = {
        "platform": "tiktok",
        "surface": "reel",
        "width": 1080,
        "height": 1080,  # wrong aspect
        "fps": 30,
        "duration_s": 20,
        "audio": {"true_peak_db": 0.5},  # clipping
        "captions": [],
        "caption_boxes": [],
        "regions": [],
        "sharpness": 0.9,
    }
    data = client.post("/v1/video/qc", json=spec).json()
    assert data["passed"] is False
    assert "aspect_ratio" in data["failures"]
    assert "audio_clipping" in data["failures"]
