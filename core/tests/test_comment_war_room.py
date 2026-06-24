"""Tests for the Comment War Room.

The most important behaviour: a comment in crisis is escalated to a human with
signposting and never auto-replied; trolls and spam are filtered out before any
reply; genuine questions and support get a vetted, supportive reply. The whole
thing is deterministic and offline.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from invisable_os.main import app
from invisable_os.services.comment_war_room import triage_comment, triage_comments

client = TestClient(app)


# --- classification ---------------------------------------------------------


def test_crisis_comment_is_escalated_with_signposting_not_auto_replied():
    t = triage_comment("honestly I've felt suicidal lately and nobody gets it")
    assert t["category"] == "crisis"
    assert t["action"] == "escalate"
    assert t["reply"] is None  # never auto-reply to a crisis
    assert t["sensitive"] is True
    assert any("Samaritans" in s for s in t["signposting"])


def test_abuse_is_do_not_engage():
    t = triage_comment("this is a scam and you're a fraud")
    assert t["category"] == "abuse"
    assert t["action"] == "do_not_engage"
    assert t["reply"] is None


def test_spam_is_ignored():
    t = triage_comment("check my profile for free followers www.spam.com")
    assert t["category"] == "spam"
    assert t["action"] == "ignore"
    assert t["reply"] is None


def test_partnership_lead_is_escalated():
    t = triage_comment("Hi, we'd love to discuss a sponsorship partnership with you")
    assert t["category"] == "lead"
    assert t["action"] == "escalate"


def test_question_gets_a_vetted_reply():
    t = triage_comment("how do you cope with fatigue on a long shift?")
    assert t["category"] == "question"
    assert t["action"] == "reply"
    assert t["reply"]
    assert t["reply_approved"] is True


def test_support_gets_a_warm_reply():
    t = triage_comment("this is amazing, thank you, really needed this today")
    assert t["category"] == "support"
    assert t["action"] == "reply"
    assert t["reply"]


def test_plain_comment_is_neutral():
    t = triage_comment("on site again today")
    assert t["category"] == "neutral"
    assert t["action"] == "reply"


# --- batch triage + ordering ------------------------------------------------


def test_batch_sorts_most_important_first():
    report = triage_comments(
        [
            "on site again today",                       # neutral
            "love this, thank you so much",              # support
            "I feel suicidal and alone",                 # crisis
            "want to discuss a partnership",             # lead
        ]
    )
    assert report["total"] == 4
    # Crisis first, then lead — both ahead of support and neutral.
    assert report["comments"][0]["category"] == "crisis"
    assert report["comments"][1]["category"] == "lead"
    assert report["escalations"] == 2


def test_batch_accepts_dicts_and_counts_by_action():
    report = triage_comments(
        [{"text": "how does this work?"}, {"text": "buy now at www.x.com"}]
    )
    assert report["by_action"]["reply"] == 1
    assert report["by_action"]["ignore"] == 1


# --- HTTP surface -----------------------------------------------------------


def test_war_room_api():
    r = client.post(
        "/v1/engagement/war-room",
        json={"comments": ["I felt suicidal", "thanks, this helped", "spam www.x.com"]},
    ).json()
    assert r["total"] == 3
    assert r["comments"][0]["category"] == "crisis"
    assert r["escalations"] >= 1
