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
