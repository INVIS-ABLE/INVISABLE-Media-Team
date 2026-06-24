-- ============================================================================
-- INVISABLE® AI Media Agency OS — PostgreSQL schema
--
-- Structured memory for the platform. ChromaDB holds the semantic side of
-- INVISABLE_BRAIN; Postgres holds the relational record of candidates, decisions,
-- performance signals, harvested signals, and the founder-recognition ledger.
-- ============================================================================

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- --- Content candidates ------------------------------------------------------
CREATE TABLE IF NOT EXISTS content_candidate (
    id              TEXT PRIMARY KEY,
    brief           TEXT NOT NULL,
    platform        TEXT NOT NULL,
    content_format  TEXT NOT NULL,
    hook            TEXT NOT NULL DEFAULT '',
    body            TEXT NOT NULL DEFAULT '',
    call_to_action  TEXT NOT NULL DEFAULT '',
    founder_centred BOOLEAN NOT NULL DEFAULT FALSE,
    original        BOOLEAN NOT NULL DEFAULT TRUE,
    themes          TEXT[] NOT NULL DEFAULT '{}',
    generator       TEXT NOT NULL DEFAULT 'unknown',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_candidate_platform ON content_candidate (platform);
CREATE INDEX IF NOT EXISTS idx_candidate_founder  ON content_candidate (founder_centred);

-- --- Scores & guardrail verdicts --------------------------------------------
CREATE TABLE IF NOT EXISTS candidate_score (
    id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    candidate_id       TEXT NOT NULL REFERENCES content_candidate(id) ON DELETE CASCADE,
    guardrail_passed   BOOLEAN NOT NULL,
    guardrail_violations TEXT[] NOT NULL DEFAULT '{}',
    -- the eight value dimensions (0.0 - 1.0)
    trust              REAL NOT NULL DEFAULT 0,
    community_value    REAL NOT NULL DEFAULT 0,
    authenticity       REAL NOT NULL DEFAULT 0,
    awareness          REAL NOT NULL DEFAULT 0,
    education          REAL NOT NULL DEFAULT 0,
    humour             REAL NOT NULL DEFAULT 0,
    consistency        REAL NOT NULL DEFAULT 0,
    long_term_brand    REAL NOT NULL DEFAULT 0,
    weighted_total     REAL NOT NULL DEFAULT 0,
    improvement_passes INT NOT NULL DEFAULT 0,
    rationale          TEXT NOT NULL DEFAULT '',
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_score_candidate ON candidate_score (candidate_id);
CREATE INDEX IF NOT EXISTS idx_score_total ON candidate_score (weighted_total DESC);

-- --- Publishing decisions ----------------------------------------------------
CREATE TABLE IF NOT EXISTS publish_decision (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    candidate_id TEXT NOT NULL REFERENCES content_candidate(id) ON DELETE CASCADE,
    decision     TEXT NOT NULL CHECK (decision IN ('publish','hold','revise','reject')),
    platform     TEXT NOT NULL,
    scheduled_at TIMESTAMPTZ,
    published_at TIMESTAMPTZ,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- --- Performance signals (Algorithm Watchtower) -----------------------------
CREATE TABLE IF NOT EXISTS performance_signal (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    candidate_id    TEXT REFERENCES content_candidate(id) ON DELETE SET NULL,
    platform        TEXT NOT NULL,
    metric          TEXT NOT NULL,
    value           DOUBLE PRECISION NOT NULL,
    themes          TEXT[] NOT NULL DEFAULT '{}',
    founder_centred BOOLEAN NOT NULL DEFAULT FALSE,
    observed_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_signal_metric ON performance_signal (metric);
CREATE INDEX IF NOT EXISTS idx_signal_observed ON performance_signal (observed_at DESC);

-- --- Harvested intelligence (abstracted signals only — never copied content) -
CREATE TABLE IF NOT EXISTS trend_signal (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    topic       TEXT NOT NULL,
    signal_kind TEXT NOT NULL,
    summary     TEXT NOT NULL,         -- our own abstraction, not a copy
    source_type TEXT NOT NULL,
    score       REAL NOT NULL DEFAULT 0.5,
    abstracted  BOOLEAN NOT NULL DEFAULT TRUE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- --- Founder Recognition ledger ---------------------------------------------
CREATE TABLE IF NOT EXISTS founder_recognition (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    period      DATE NOT NULL,
    index_value REAL NOT NULL,
    breakdown   JSONB NOT NULL DEFAULT '{}',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_recognition_period ON founder_recognition (period);

-- --- A convenience view: published content founder share --------------------
CREATE OR REPLACE VIEW founder_presence AS
SELECT
    date_trunc('week', pd.published_at) AS week,
    count(*)                            AS total_published,
    count(*) FILTER (WHERE cc.founder_centred) AS founder_published,
    round(
        (count(*) FILTER (WHERE cc.founder_centred))::numeric
        / NULLIF(count(*), 0), 3
    )                                   AS founder_share
FROM publish_decision pd
JOIN content_candidate cc ON cc.id = pd.candidate_id
WHERE pd.decision = 'publish' AND pd.published_at IS NOT NULL
GROUP BY 1
ORDER BY 1 DESC;

-- ============================================================================
-- DEPARTMENTS — Intelligence, Relationship, Production, Growth, Knowledge,
-- Creative, PR, Governance. These turn the platform from a content factory into
-- a media organisation. (Added in the departments build.)
-- ============================================================================

-- --- Fixed Tag Network (opt-in; never tag outside this list) -----------------
CREATE TABLE IF NOT EXISTS tag_network_member (
    id              TEXT PRIMARY KEY,
    display_name    TEXT NOT NULL,
    tiktok_handle   TEXT,
    instagram_handle TEXT,
    category        TEXT NOT NULL DEFAULT 'network',
    relationship    TEXT NOT NULL DEFAULT '',
    approved        BOOLEAN NOT NULL DEFAULT TRUE,
    paused          BOOLEAN NOT NULL DEFAULT FALSE,
    do_not_tag      BOOLEAN NOT NULL DEFAULT FALSE,
    notes           TEXT NOT NULL DEFAULT '',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- --- People & consent (Production / Relationship) ---------------------------
CREATE TABLE IF NOT EXISTS person (
    id                 TEXT PRIMARY KEY,
    full_name          TEXT NOT NULL,
    public_display_name TEXT NOT NULL DEFAULT '',
    role               TEXT NOT NULL DEFAULT '',
    tiktok_handle      TEXT,
    instagram_handle   TEXT,
    consent_status     TEXT NOT NULL DEFAULT 'pending'
                         CHECK (consent_status IN ('pending','approved','declined','expired')),
    voice_permission   BOOLEAN NOT NULL DEFAULT FALSE,
    allowed_platforms  TEXT[] NOT NULL DEFAULT '{}',
    allowed_content_types TEXT[] NOT NULL DEFAULT '{}',
    consent_expiry     DATE,
    do_not_use_notes   TEXT NOT NULL DEFAULT '',
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- --- Media assets with consent linkage --------------------------------------
CREATE TABLE IF NOT EXISTS asset (
    id          TEXT PRIMARY KEY,
    kind        TEXT NOT NULL,                 -- photo | video | audio | voiceover | graphic
    path        TEXT NOT NULL,
    person_id   TEXT REFERENCES person(id) ON DELETE SET NULL,
    approved    BOOLEAN NOT NULL DEFAULT FALSE,
    tags        TEXT[] NOT NULL DEFAULT '{}',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- --- Partners & sponsors (Relationship) -------------------------------------
CREATE TABLE IF NOT EXISTS partner (
    id           TEXT PRIMARY KEY,
    name         TEXT NOT NULL,
    kind         TEXT NOT NULL DEFAULT 'partner',  -- partner | sponsor | prospect
    sector       TEXT NOT NULL DEFAULT '',
    status       TEXT NOT NULL DEFAULT 'active',
    last_contact DATE,
    interests    TEXT[] NOT NULL DEFAULT '{}',
    notes        TEXT NOT NULL DEFAULT '',
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- --- Relationship CRM log ----------------------------------------------------
CREATE TABLE IF NOT EXISTS relationship_touch (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    partner_id  TEXT REFERENCES partner(id) ON DELETE CASCADE,
    person_id   TEXT REFERENCES person(id) ON DELETE CASCADE,
    touched_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    summary     TEXT NOT NULL DEFAULT '',
    follow_up_at DATE
);

-- --- Competitor intelligence (learn structure, never copy) -------------------
CREATE TABLE IF NOT EXISTS competitor (
    id            TEXT PRIMARY KEY,
    handle        TEXT NOT NULL,
    category      TEXT NOT NULL DEFAULT '',
    growth_signal TEXT NOT NULL DEFAULT '',
    lessons       TEXT[] NOT NULL DEFAULT '{}',
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- --- Opportunities (podcasts, speaking, events, awards, sponsorship, grants) -
CREATE TABLE IF NOT EXISTS opportunity (
    id               TEXT PRIMARY KEY,
    kind             TEXT NOT NULL,
    title            TEXT NOT NULL,
    fit_score        REAL NOT NULL DEFAULT 0.5,
    why              TEXT NOT NULL DEFAULT '',
    suggested_action TEXT NOT NULL DEFAULT '',
    status           TEXT NOT NULL DEFAULT 'open',
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- --- PR: journalists / podcasts / media contacts ----------------------------
CREATE TABLE IF NOT EXISTS media_contact (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    outlet      TEXT NOT NULL DEFAULT '',
    beat        TEXT NOT NULL DEFAULT '',   -- health | construction | local | podcast
    handle      TEXT,
    email       TEXT,
    notes       TEXT NOT NULL DEFAULT '',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- --- Community Story Portal submissions (consent-gated) ---------------------
CREATE TABLE IF NOT EXISTS community_story (
    id                TEXT PRIMARY KEY,
    summary           TEXT NOT NULL,
    condition         TEXT NOT NULL DEFAULT '',
    wants_to_be_named BOOLEAN NOT NULL DEFAULT FALSE,
    allows_social_use BOOLEAN NOT NULL DEFAULT FALSE,
    consent_status    TEXT NOT NULL DEFAULT 'pending'
                        CHECK (consent_status IN ('pending','approved','declined','expired')),
    suggested_formats TEXT[] NOT NULL DEFAULT '{}',
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- --- Knowledge base (NHS/benefits, construction) ----------------------------
CREATE TABLE IF NOT EXISTS knowledge_item (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    domain      TEXT NOT NULL,                -- nhs_benefits | construction
    title       TEXT NOT NULL,
    plain_english TEXT NOT NULL DEFAULT '',
    source      TEXT NOT NULL DEFAULT '',
    needs_review BOOLEAN NOT NULL DEFAULT TRUE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- --- Growth: viral hook library + comment intelligence ----------------------
CREATE TABLE IF NOT EXISTS hook_library (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    hook        TEXT NOT NULL,
    performance REAL NOT NULL DEFAULT 0,
    themes      TEXT[] NOT NULL DEFAULT '{}',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- --- Mission scores per candidate (Governance) ------------------------------
CREATE TABLE IF NOT EXISTS mission_score (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    candidate_id            TEXT REFERENCES content_candidate(id) ON DELETE CASCADE,
    awareness_impact        REAL NOT NULL DEFAULT 0,
    community_impact        REAL NOT NULL DEFAULT 0,
    fundraising_impact      REAL NOT NULL DEFAULT 0,
    partner_impact          REAL NOT NULL DEFAULT 0,
    long_term_mission_impact REAL NOT NULL DEFAULT 0,
    total                   REAL NOT NULL DEFAULT 0,
    verdict                 TEXT NOT NULL DEFAULT 'hold',
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- --- Risk flags raised on content (Governance) ------------------------------
CREATE TABLE IF NOT EXISTS risk_flag (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    candidate_id TEXT REFERENCES content_candidate(id) ON DELETE CASCADE,
    category     TEXT NOT NULL,   -- medical_advice | benefits_advice | legal_advice | sponsor_claim | copyright
    resolved     BOOLEAN NOT NULL DEFAULT FALSE,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ============================================================================
-- Remix, Parody & Trend Intelligence department
--
-- The scanner indexes culture and trends; the rights system gates everything
-- that could become footage. CORE RULE: the system must never automatically
-- download and reupload other people's videos as-is. Only the usable rights
-- statuses (owned, licensed, public_domain, creative_commons,
-- user_submitted_consent, platform_duet_stitch) may enter video assembly;
-- reference_only and blocked never can.
-- ============================================================================

-- --- Scanner sources (feeds the scanner monitors) ---------------------------
CREATE TABLE IF NOT EXISTS scanner_sources (
    id             TEXT PRIMARY KEY,
    name           TEXT NOT NULL,
    type           TEXT NOT NULL DEFAULT 'rss',   -- rss | trends | forum | search | research
    url            TEXT NOT NULL DEFAULT '',
    topic_area     TEXT NOT NULL DEFAULT '',
    platform       TEXT NOT NULL DEFAULT '',
    scan_frequency TEXT NOT NULL DEFAULT 'daily',
    enabled        BOOLEAN NOT NULL DEFAULT TRUE,
    notes          TEXT NOT NULL DEFAULT '',
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_scanner_sources_topic ON scanner_sources (topic_area);

-- --- Scanned items / reference inbox (abstracted, never raw copies) ----------
CREATE TABLE IF NOT EXISTS scanned_items (
    id                       TEXT PRIMARY KEY,
    source_id                TEXT,
    url                      TEXT NOT NULL DEFAULT '',
    title                    TEXT NOT NULL,
    creator                  TEXT NOT NULL DEFAULT '',
    platform                 TEXT NOT NULL DEFAULT '',
    summary                  TEXT NOT NULL DEFAULT '',
    transcript               TEXT NOT NULL DEFAULT '',
    topic_tags               TEXT[] NOT NULL DEFAULT '{}',
    trend_score              REAL NOT NULL DEFAULT 0,
    humour_score             REAL NOT NULL DEFAULT 0,
    construction_score       REAL NOT NULL DEFAULT 0,
    invisible_illness_score  REAL NOT NULL DEFAULT 0,
    sponsor_score            REAL NOT NULL DEFAULT 0,
    risk_score               REAL NOT NULL DEFAULT 0,
    rights_status            TEXT NOT NULL DEFAULT 'reference_only'
                               CHECK (rights_status IN ('owned','licensed','public_domain',
                                 'creative_commons','user_submitted_consent',
                                 'platform_duet_stitch','reference_only','blocked')),
    status                   TEXT NOT NULL DEFAULT 'new',
    date_found               TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_scanned_items_status ON scanned_items (status);
CREATE INDEX IF NOT EXISTS idx_scanned_items_rights ON scanned_items (rights_status);

-- --- Media assets (rights manager) ------------------------------------------
CREATE TABLE IF NOT EXISTS media_assets (
    id                TEXT PRIMARY KEY,
    file_path         TEXT NOT NULL DEFAULT '',
    source_url        TEXT NOT NULL DEFAULT '',
    title             TEXT NOT NULL DEFAULT '',
    asset_type        TEXT NOT NULL DEFAULT 'video',  -- video | audio | image | voice | broll
    owner             TEXT NOT NULL DEFAULT '',
    rights_status     TEXT NOT NULL DEFAULT 'owned'
                        CHECK (rights_status IN ('owned','licensed','public_domain',
                          'creative_commons','user_submitted_consent',
                          'platform_duet_stitch','reference_only','blocked')),
    licence_notes     TEXT NOT NULL DEFAULT '',
    consent_id        TEXT NOT NULL DEFAULT '',
    expiry_date       TEXT,
    allowed_platforms TEXT[] NOT NULL DEFAULT '{}',
    allowed_uses      TEXT[] NOT NULL DEFAULT '{}',
    blocked_uses      TEXT[] NOT NULL DEFAULT '{}',
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_media_assets_rights ON media_assets (rights_status);

-- --- Pop-culture references (prefer paraphrase-safe over exact quotes) -------
CREATE TABLE IF NOT EXISTS pop_culture_references (
    id                        TEXT PRIMARY KEY,
    title                     TEXT NOT NULL,
    source_type               TEXT NOT NULL DEFAULT 'film',
    reference_description      TEXT NOT NULL DEFAULT '',
    exact_quote               TEXT NOT NULL DEFAULT '',
    paraphrase_safe_version   TEXT NOT NULL DEFAULT '',
    tone                      TEXT NOT NULL DEFAULT '',
    humour_style              TEXT NOT NULL DEFAULT '',
    copyright_risk            TEXT NOT NULL DEFAULT 'medium'
                                CHECK (copyright_risk IN ('none','low','medium','high')),
    use_allowed               BOOLEAN NOT NULL DEFAULT TRUE,
    suggested_invisable_angle TEXT NOT NULL DEFAULT '',
    platforms                 TEXT[] NOT NULL DEFAULT '{}',
    related_topics            TEXT[] NOT NULL DEFAULT '{}',
    created_at                TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- --- Meme formats (structure learned, content never copied) ------------------
CREATE TABLE IF NOT EXISTS meme_formats (
    id                   TEXT PRIMARY KEY,
    format_name          TEXT NOT NULL,
    description          TEXT NOT NULL DEFAULT '',
    structure            TEXT NOT NULL DEFAULT '',
    example_safe_version TEXT NOT NULL DEFAULT '',
    platform             TEXT NOT NULL DEFAULT '',
    humour_style         TEXT NOT NULL DEFAULT '',
    risk_score           REAL NOT NULL DEFAULT 0,
    related_topics       TEXT[] NOT NULL DEFAULT '{}',
    created_at           TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- --- Remix jobs (parody/reaction/voiceover moving toward approval) -----------
CREATE TABLE IF NOT EXISTS remix_jobs (
    id                  TEXT PRIMARY KEY,
    input_topic         TEXT NOT NULL DEFAULT '',
    reference_item_id   TEXT,
    asset_id            TEXT,
    output_type         TEXT NOT NULL DEFAULT 'parody',
    mode                TEXT NOT NULL DEFAULT 'create_parody',
    script              TEXT NOT NULL DEFAULT '',
    voiceover_script    TEXT NOT NULL DEFAULT '',
    caption             TEXT NOT NULL DEFAULT '',
    hashtags            TEXT[] NOT NULL DEFAULT '{}',
    tags                TEXT[] NOT NULL DEFAULT '{}',
    platform            TEXT NOT NULL DEFAULT '',
    rights_check_status TEXT NOT NULL DEFAULT 'pending',
    brand_check_status  TEXT NOT NULL DEFAULT 'pending',
    approval_status     TEXT NOT NULL DEFAULT 'pending_review',
    risk_score          REAL NOT NULL DEFAULT 0,
    pack                JSONB NOT NULL DEFAULT '{}',
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_remix_jobs_status ON remix_jobs (approval_status);

-- --- Extracted hooks (from transcripts; adapted to original INVISABLE® lines) -
CREATE TABLE IF NOT EXISTS extracted_hooks (
    id                        TEXT PRIMARY KEY,
    scanned_item_id           TEXT,
    hook_text                 TEXT NOT NULL DEFAULT '',
    hook_type                 TEXT NOT NULL DEFAULT '',
    platform                  TEXT NOT NULL DEFAULT '',
    strength_score            REAL NOT NULL DEFAULT 0,
    adapted_invisable_version TEXT NOT NULL DEFAULT '',
    created_at                TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- --- Subtitles (Whisper → auto-subtitle → FFmpeg burn-in) -------------------
CREATE TABLE IF NOT EXISTS subtitles (
    id                TEXT PRIMARY KEY,
    asset_id          TEXT,
    transcript        TEXT NOT NULL DEFAULT '',
    srt_path          TEXT NOT NULL DEFAULT '',
    burned_video_path TEXT NOT NULL DEFAULT '',
    language          TEXT NOT NULL DEFAULT 'en',
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ============================================================================
-- CONTENT WAR CHEST — the reserve of approved, ready-to-post assets.
--
-- "Always generate more than you publish." Approved queue items are stocked here
-- with a category, freshness and expiry; the Scheduler & War Chest bot draws the
-- best non-repetitive item per slot. Reserve health: min 500 · healthy 1,000 ·
-- elite 2,000+ (see core/invisable_os/services/war_chest.py).
-- ============================================================================
CREATE TABLE IF NOT EXISTS war_chest_item (
    id              TEXT PRIMARY KEY,
    queue_item_id   TEXT NOT NULL DEFAULT '',
    candidate_id    TEXT NOT NULL DEFAULT '',
    title           TEXT NOT NULL DEFAULT '',
    category        TEXT NOT NULL DEFAULT 'evergreen',
    platform        TEXT NOT NULL DEFAULT '',
    pillar          TEXT NOT NULL DEFAULT '',
    evergreen       BOOLEAN NOT NULL DEFAULT FALSE,
    reserve_status  TEXT NOT NULL DEFAULT 'ready'
                    CHECK (reserve_status IN ('ready','used','expired','retired')),
    quality_score   REAL NOT NULL DEFAULT 0,
    mission_score   REAL NOT NULL DEFAULT 0,
    humour_score    REAL NOT NULL DEFAULT 0,
    risk_score      REAL NOT NULL DEFAULT 0,
    freshness_score REAL NOT NULL DEFAULT 1,
    tags            TEXT[] NOT NULL DEFAULT '{}',
    payload         JSONB NOT NULL DEFAULT '{}',
    expiry_date     TIMESTAMPTZ,
    last_used_at    TIMESTAMPTZ,
    reuse_count     INT NOT NULL DEFAULT 0,
    notes           TEXT NOT NULL DEFAULT '',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_war_chest_category ON war_chest_item (category);
CREATE INDEX IF NOT EXISTS idx_war_chest_status   ON war_chest_item (reserve_status);
