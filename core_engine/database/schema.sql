-- Expert_Smart — PostgreSQL Schema
-- Phase 8: Database Migration (JSON → PostgreSQL)
-- ============================================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================
-- Table 1: Comparables (migrated from market_feed.json)
-- ============================================================
CREATE TABLE IF NOT EXISTS comparables (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Property details
    property_type       VARCHAR(50)     NOT NULL,
    area_sqm            NUMERIC(10, 2)  NOT NULL,
    age_years           INT,
    finishing_level     VARCHAR(50),
    quality_tier        VARCHAR(50),

    -- Location
    latitude            NUMERIC(10, 8),
    longitude           NUMERIC(11, 8),
    governorate         VARCHAR(100),
    location_description TEXT,

    -- Financial
    price_egp           NUMERIC(15, 2)  NOT NULL,
    price_per_sqm       NUMERIC(10, 2),

    -- Metadata
    source              VARCHAR(100),
    listed_date         DATE,
    data_quality_score  NUMERIC(3, 2),

    -- Timestamps
    created_at          TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_comp_governorate    ON comparables (governorate);
CREATE INDEX IF NOT EXISTS idx_comp_property_type  ON comparables (property_type);
CREATE INDEX IF NOT EXISTS idx_comp_location       ON comparables (latitude, longitude);
CREATE INDEX IF NOT EXISTS idx_comp_price          ON comparables (price_egp);

-- ============================================================
-- Table 2: Valuations (results from Phase 4-7 pipeline)
-- ============================================================
CREATE TABLE IF NOT EXISTS valuations (
    id                    UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Property + purpose
    asset_type            VARCHAR(50)    NOT NULL,
    primary_purpose       VARCHAR(50)    NOT NULL,

    -- Optional link to a primary comparable (nullable)
    comparable_id         UUID           REFERENCES comparables(id) ON DELETE SET NULL,

    -- Results
    primary_value         NUMERIC(15, 2),
    confidence            VARCHAR(20),

    -- Three-approach weights
    weight_comparable     NUMERIC(4, 3),
    weight_cost           NUMERIC(4, 3),
    weight_income         NUMERIC(4, 3),

    -- Phase 4 engine values
    comparable_value      NUMERIC(15, 2),
    cost_value            NUMERIC(15, 2),
    income_value          NUMERIC(15, 2),

    -- Comparable search metadata
    comparable_count      INT,
    top_similarity_score  NUMERIC(5, 2),

    -- Full result (flexible JSONB)
    result_json           JSONB,

    -- Report metadata
    appraiser_name        VARCHAR(100),
    property_address      TEXT,
    valuation_date        DATE,
    report_file_path      VARCHAR(255),

    -- Timestamps
    created_at            TIMESTAMP      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at            TIMESTAMP      NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_val_asset_type      ON valuations (asset_type);
CREATE INDEX IF NOT EXISTS idx_val_purpose         ON valuations (primary_purpose);
CREATE INDEX IF NOT EXISTS idx_val_date            ON valuations (valuation_date);
CREATE INDEX IF NOT EXISTS idx_val_confidence      ON valuations (confidence);
CREATE INDEX IF NOT EXISTS idx_val_comparable_id   ON valuations (comparable_id);

-- ============================================================
-- Table 3: Quality Audits (from ReportQualityAuditor)
-- ============================================================
CREATE TABLE IF NOT EXISTS quality_audits (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- FK to valuation (cascade delete keeps data clean)
    valuation_id        UUID            NOT NULL
                        REFERENCES valuations(id) ON DELETE CASCADE,

    -- Overall audit result
    quality_score       NUMERIC(5, 2),
    quality_grade       VARCHAR(1),
    passed              BOOLEAN,

    -- Per-category scores (reserved for future category-level scoring)
    completeness_score  NUMERIC(5, 2),
    methodology_score   NUMERIC(5, 2),
    compliance_score    NUMERIC(5, 2),
    data_quality_score  NUMERIC(5, 2),

    -- Full findings list (JSONB for flexibility)
    findings_json       JSONB,

    -- Timestamps
    created_at          TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_qa_valuation_id  ON quality_audits (valuation_id);
CREATE INDEX IF NOT EXISTS idx_qa_grade         ON quality_audits (quality_grade);
CREATE INDEX IF NOT EXISTS idx_qa_passed        ON quality_audits (passed);

-- ============================================================
-- Table 4: Audit Logs (request / activity tracking)
-- ============================================================
CREATE TABLE IF NOT EXISTS audit_logs (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- What happened
    action          VARCHAR(50)     NOT NULL,
    entity_type     VARCHAR(50),
    entity_id       UUID,

    -- Who did it
    actor           VARCHAR(100),

    -- Outcome
    success         BOOLEAN,
    error_message   TEXT,
    duration_ms     INT,

    -- Request / response detail
    details_json    JSONB,

    -- Timestamps
    created_at      TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_log_action      ON audit_logs (action);
CREATE INDEX IF NOT EXISTS idx_log_entity_type ON audit_logs (entity_type);
CREATE INDEX IF NOT EXISTS idx_log_created_at  ON audit_logs (created_at DESC);

-- ============================================================
-- View: Recent valuations with quality grade
-- ============================================================
CREATE OR REPLACE VIEW v_valuations_with_audit AS
SELECT
    v.id,
    v.asset_type,
    v.primary_purpose,
    v.primary_value,
    v.confidence,
    v.valuation_date,
    v.created_at,
    qa.quality_grade,
    qa.quality_score,
    qa.passed
FROM valuations v
LEFT JOIN quality_audits qa ON v.id = qa.valuation_id
ORDER BY v.created_at DESC;

-- ============================================================
-- View: Comparable market statistics by governorate + type
-- ============================================================
CREATE OR REPLACE VIEW v_comparable_stats AS
SELECT
    governorate,
    property_type,
    COUNT(*)                AS count,
    AVG(price_egp)          AS avg_price,
    AVG(price_per_sqm)      AS avg_price_sqm,
    MIN(price_egp)          AS min_price,
    MAX(price_egp)          AS max_price,
    STDDEV(price_egp)       AS stddev_price
FROM comparables
WHERE data_quality_score >= 0.7
  OR data_quality_score IS NULL
GROUP BY governorate, property_type;
