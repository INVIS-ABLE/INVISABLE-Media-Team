"""Department data models.

Lightweight domain models for the relationship, intelligence, knowledge, and
production departments. These mirror the PostgreSQL schema in ``db/schema.sql`` and
are what the corresponding engines pass around. Consent and approval are modelled
explicitly because the platform must never misuse a real person's likeness or voice.
"""

from __future__ import annotations

import uuid
from enum import StrEnum

from pydantic import BaseModel, Field


class ConsentStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    DECLINED = "declined"
    EXPIRED = "expired"


class TagNetworkMember(BaseModel):
    """An approved account in the fixed tag network. Never tag outside this list."""

    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    display_name: str
    tiktok_handle: str | None = None
    instagram_handle: str | None = None
    category: str = "network"  # ambassador | partner | sponsor | creator | trustee
    relationship: str = ""
    approved: bool = True
    paused: bool = False
    do_not_tag: bool = False
    notes: str = ""


class Person(BaseModel):
    """A real person with explicit consent and usage permissions."""

    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    full_name: str
    public_display_name: str = ""
    role: str = ""  # founder | ambassador | trustee | partner | supporter
    tiktok_handle: str | None = None
    instagram_handle: str | None = None
    consent_status: ConsentStatus = ConsentStatus.PENDING
    voice_permission: bool = False
    allowed_platforms: list[str] = Field(default_factory=list)
    allowed_content_types: list[str] = Field(default_factory=list)
    consent_expiry: str | None = None  # ISO date
    do_not_use_notes: str = ""

    @property
    def usable(self) -> bool:
        return self.consent_status == ConsentStatus.APPROVED


class Partner(BaseModel):
    """A partner or sponsor relationship (CT1, GT Insurance, Bald Builders, …)."""

    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    name: str
    kind: str = "partner"  # partner | sponsor | prospect
    sector: str = ""  # tools | insurance | construction | health | local
    status: str = "active"
    last_contact: str | None = None
    interests: list[str] = Field(default_factory=list)
    notes: str = ""


class Competitor(BaseModel):
    """A tracked account — learn structure and audience response, never copy."""

    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    handle: str
    category: str = ""  # charity | autoimmune_creator | trades_influencer | brand
    growth_signal: str = ""  # our abstracted note, e.g. "growing with workplace content"
    lessons: list[str] = Field(default_factory=list)


class Opportunity(BaseModel):
    """A media / speaking / sponsorship / award opportunity surfaced by the scanner."""

    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    kind: str  # podcast | speaking | event | award | sponsorship | grant
    title: str
    fit_score: float = 0.5
    why: str = ""
    suggested_action: str = ""


class RelationshipTouch(BaseModel):
    """A logged contact with a partner or person, with an optional follow-up date.

    The Relationship CRM nudges the founder to keep real relationships warm; the
    ``follow_up_at`` date drives the daily Relationship Follow-ups workflow.
    """

    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    partner_id: str | None = None
    person_id: str | None = None
    summary: str = ""
    channel: str = ""  # email | call | dm | event | in_person
    touched_at: str | None = None  # ISO datetime; defaults to now on persist
    follow_up_at: str | None = None  # ISO date


class CommunityStory(BaseModel):
    """A story submitted via the Community Story Portal, with consent gating."""

    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    summary: str
    condition: str = ""
    wants_to_be_named: bool = False
    allows_social_use: bool = False
    consent_status: ConsentStatus = ConsentStatus.PENDING
    suggested_formats: list[str] = Field(default_factory=list)
