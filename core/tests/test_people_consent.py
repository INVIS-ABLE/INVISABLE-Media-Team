"""People & Consent + Relationship CRM.

The platform must never feature a real person without explicit, current consent.
These tests pin that rule (approved AND not expired = usable), the relationship
follow-up nudge, and community-story consent gating — through the repository and
the live API. The autouse ``isolated_db`` fixture gives each test a fresh SQLite DB.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from invisable_os.main import app
from invisable_os.models.departments import (
    CommunityStory,
    ConsentStatus,
    Person,
    RelationshipTouch,
)
from invisable_os.services.consent import consent_state
from invisable_os.store import get_repository


def _client() -> TestClient:
    return TestClient(app)


# -- consent_state helper (the gate) ----------------------------------------


def test_consent_state_only_approved_and_unexpired_is_usable():
    assert consent_state({"consent_status": "approved"}, today="2026-06-24")["usable"]
    assert not consent_state({"consent_status": "pending"}, today="2026-06-24")["usable"]
    assert not consent_state({"consent_status": "declined"}, today="2026-06-24")["usable"]
    expired = consent_state(
        {"consent_status": "approved", "consent_expiry": "2026-01-01"}, today="2026-06-24"
    )
    assert not expired["usable"]
    assert expired["reason"] == "expired"
    ok = consent_state(
        {"consent_status": "approved", "consent_expiry": "2099-01-01"}, today="2026-06-24"
    )
    assert ok["usable"] and ok["reason"] == "ok"


# -- repository round-trip ---------------------------------------------------


def test_person_consent_lifecycle():
    repo = get_repository()
    pid = repo.add_person(Person(full_name="Jane Doe", role="ambassador"))
    p = repo.get_person(pid)
    assert p["consent_status"] == "pending"
    assert not consent_state(p)["usable"]

    repo.set_consent(pid, "approved", voice_permission=True, allowed_platforms=["instagram"])
    p = repo.get_person(pid)
    assert p["consent_status"] == "approved"
    assert p["voice_permission"] is True
    assert consent_state(p)["usable"]


def test_due_followups_returns_only_due():
    repo = get_repository()
    repo.record_touch(RelationshipTouch(partner_id="ct1", summary="intro call",
                                        follow_up_at="2026-06-20"))
    repo.record_touch(RelationshipTouch(partner_id="gt", summary="later",
                                        follow_up_at="2099-01-01"))
    repo.record_touch(RelationshipTouch(partner_id="x", summary="no follow-up"))
    due = repo.due_followups("2026-06-24")
    assert [d["partner_id"] for d in due] == ["ct1"]


def test_community_story_consent_gating():
    repo = get_repository()
    sid = repo.add_community_story(CommunityStory(summary="My fatigue story"))
    assert repo.list_community_stories(status="pending")
    repo.set_story_consent(sid, ConsentStatus.APPROVED.value)
    assert not repo.list_community_stories(status="pending")
    assert repo.list_community_stories(status="approved")[0]["id"] == sid


# -- API ---------------------------------------------------------------------


def test_api_people_and_consent_flow():
    c = _client()
    pid = c.post("/v1/people", json={"full_name": "Sam Trades", "role": "ambassador"}).json()["id"]

    listed = c.get("/v1/people").json()["people"]
    assert any(p["id"] == pid for p in listed)
    assert all("consent" in p for p in listed)  # every person carries a consent verdict
    assert c.get(f"/v1/people/{pid}").json()["consent"]["usable"] is False

    approved = c.post(f"/v1/people/{pid}/consent", json={"consent_status": "approved"}).json()
    assert approved["consent"]["usable"] is True
    assert c.post("/v1/people/nope/consent", json={"consent_status": "approved"}).status_code == 404


def test_api_relationship_followups():
    c = _client()
    c.post("/v1/relationships/touch",
           json={"partner_id": "ct1", "summary": "demo", "follow_up_at": "2020-01-01"})
    due = c.get("/v1/relationships/followups").json()
    assert due["count"] == 1
    assert due["followups"][0]["partner_id"] == "ct1"
    # A future-only cutoff still finds the very-overdue one; a past cutoff excludes nothing newer.
    assert c.get("/v1/relationships/followups?on_or_before=2019-01-01").json()["count"] == 0


def test_api_community_stories():
    c = _client()
    sid = c.post("/v1/community/stories", json={"summary": "story"}).json()["id"]
    assert c.get("/v1/community/stories?status=pending").json()["stories"]
    c.post(f"/v1/community/stories/{sid}/consent", json={"consent_status": "approved"})
    assert c.get("/v1/community/stories?status=approved").json()["stories"][0]["id"] == sid
