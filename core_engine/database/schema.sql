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

-- ============================================================
-- P1 Migration: Mass Valuation Tables
-- ============================================================

-- Table 5: Mass Valuation Runs
CREATE TABLE IF NOT EXISTS mass_valuation_runs (
    run_id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    run_name                    VARCHAR(200)    NOT NULL,
    property_type               VARCHAR(50)     NOT NULL,
    jurisdiction                VARCHAR(20)     NOT NULL DEFAULT 'SA',
    status                      VARCHAR(50)     NOT NULL DEFAULT 'draft',
    method                      VARCHAR(50)     NOT NULL DEFAULT 'avm',
    standard_version_id         VARCHAR(50),
    n_input_records             INT             NOT NULL DEFAULT 0,
    n_rejected                  INT             NOT NULL DEFAULT 0,
    n_flagged                   INT             NOT NULL DEFAULT 0,
    n_training_records          INT             NOT NULL DEFAULT 0,
    n_predicted_properties      INT             NOT NULL DEFAULT 0,
    ood_property_count          INT             NOT NULL DEFAULT 0,
    manual_review_required_count INT            NOT NULL DEFAULT 0,
    dataset_hash                CHAR(64),
    random_seed                 INT,
    iaao_summary                JSONB,
    advisory_only               BOOLEAN         NOT NULL DEFAULT TRUE,
    certification_ready         BOOLEAN         NOT NULL DEFAULT FALSE,
    audit_trail_id              UUID,
    started_at                  TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at                TIMESTAMP,
    created_by                  VARCHAR(100),
    approved_by                 VARCHAR(100),
    approved_at                 TIMESTAMP,
    run_config                  JSONB,
    created_at                  TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_mvr_status         ON mass_valuation_runs (status);
CREATE INDEX IF NOT EXISTS idx_mvr_property_type  ON mass_valuation_runs (property_type);
CREATE INDEX IF NOT EXISTS idx_mvr_jurisdiction   ON mass_valuation_runs (jurisdiction);
CREATE INDEX IF NOT EXISTS idx_mvr_created_at     ON mass_valuation_runs (created_at DESC);

-- Table 6: Property Predictions
CREATE TABLE IF NOT EXISTS property_predictions (
    prediction_id               UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    run_id                      UUID            NOT NULL
                                REFERENCES mass_valuation_runs(run_id) ON DELETE CASCADE,
    property_id                 VARCHAR(100)    NOT NULL,
    estimated_value             NUMERIC(18, 2),
    unit_value                  NUMERIC(12, 2),
    prediction_interval_low     NUMERIC(18, 2),
    prediction_interval_high    NUMERIC(18, 2),
    confidence                  VARCHAR(20)     NOT NULL DEFAULT 'medium',
    distribution_status         VARCHAR(50)     NOT NULL DEFAULT 'in_distribution',
    review_status               VARCHAR(50)     NOT NULL DEFAULT 'manual_review_required',
    model_version               VARCHAR(50),
    quality_flags               JSONB,
    comparable_ids              JSONB,
    shap_values                 JSONB,
    limitations                 JSONB,
    advisory_only               BOOLEAN         NOT NULL DEFAULT TRUE,
    created_at                  TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_pp_run_id              ON property_predictions (run_id);
CREATE INDEX IF NOT EXISTS idx_pp_property_id         ON property_predictions (property_id);
CREATE INDEX IF NOT EXISTS idx_pp_distribution_status ON property_predictions (distribution_status);
CREATE INDEX IF NOT EXISTS idx_pp_review_status       ON property_predictions (review_status);

-- Table 7: Review Decisions
CREATE TABLE IF NOT EXISTS review_decisions (
    decision_id                 UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    prediction_id               UUID            NOT NULL
                                REFERENCES property_predictions(prediction_id) ON DELETE CASCADE,
    property_id                 VARCHAR(100)    NOT NULL,
    run_id                      UUID            NOT NULL
                                REFERENCES mass_valuation_runs(run_id) ON DELETE CASCADE,
    model_value                 NUMERIC(18, 2),
    reviewed_value              NUMERIC(18, 2),
    decision                    VARCHAR(20)     NOT NULL
                                CHECK (decision IN ('accepted', 'overridden', 'rejected')),
    reason                      TEXT            NOT NULL,
    evidence_ids                JSONB,
    quality_flags_reviewed      JSONB,
    reviewed_by                 VARCHAR(100)    NOT NULL,
    reviewed_at                 TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    approved_by                 VARCHAR(100),
    approved_at                 TIMESTAMP,
    advisory_only               BOOLEAN         NOT NULL DEFAULT TRUE,
    created_at                  TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_reviewed_by_not_system CHECK (reviewed_by <> 'system')
);

CREATE INDEX IF NOT EXISTS idx_rd_run_id        ON review_decisions (run_id);
CREATE INDEX IF NOT EXISTS idx_rd_prediction_id ON review_decisions (prediction_id);
CREATE INDEX IF NOT EXISTS idx_rd_reviewed_by   ON review_decisions (reviewed_by);
CREATE INDEX IF NOT EXISTS idx_rd_decision       ON review_decisions (decision);
