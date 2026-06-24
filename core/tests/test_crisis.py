"""Tests for Crisis / Sensitive Topic Mode.

The platform must treat the heaviest topics with extra care: no jokes, no clickbait,
a source and human approval required, and real UK signposting attached. Everything
here is deterministic and offline.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from invisable_os.guardrails import SensitiveTopic, crisis_review, detect_sensitive_topics
from invisable_os.main import app

client = TestClient(app)


# --- detection --------------------------------------------------------------


def test_detects_suicide_self_harm():
    assert SensitiveTopic.SUICIDE_SELF_HARM in detect_sensitive_topics(
        "I felt suicidal and didn't want to be here"
    )


def test_detects_multiple_topics():
    topics = detect_sensitive_topics("after the funeral I ended up in hospital")
    assert SensitiveTopic.DEATH_BEREAVEMENT in topics
    assert SensitiveTopic.HOSPITAL in topics


def test_ordinary_content_is_not_sensitive():
    assert detect_sensitive_topics("funny POV about tool theft on site") == []


# --- the review verdict -----------------------------------------------------


def test_sensitive_content_demands_care():
    v = crisis_review("I felt suicidal last winter")
    assert v.sensitive is True
    assert v.no_jokes and v.no_clickbait
    assert v.approval_required is True
    assert v.source_required is True  # suicide/self-harm requires a source
    assert v.signposting  # Samaritans signpost attached


def test_signposting_is_topic_specific():
    v = crisis_review("I felt suicidal")
    assert any("Samaritans" in s for s in v.signposting)
    b = crisis_review("my nan passed away")
    assert any("Cruse" in s for s in b.signposting)


def test_non_sensitive_has_no_requirements():
    v = crisis_review("a warm, funny post about pacing on a busy week")
    assert v.sensitive is False
    assert not v.approval_required
    assert v.signposting == []


def test_bereavement_does_not_force_a_source_but_needs_approval():
    v = crisis_review("grief is heavy; we lost someone dear")
    assert v.sensitive is True
    assert v.approval_required is True
    assert v.source_required is False  # lived-experience grief, not a factual claim


# --- HTTP surface -----------------------------------------------------------


def test_crisis_api():
    r = client.post(
        "/v1/crisis/check",
        json={"text": "disability discrimination got me sacked, heading to tribunal"},
    ).json()
    assert r["sensitive"] is True
    assert r["requirements"]["approval_required"] is True
    assert r["requirements"]["source_required"] is True
    assert r["signposting"]

    clean = client.post("/v1/crisis/check", json={"text": "sunny day on site"}).json()
    assert clean["sensitive"] is False
