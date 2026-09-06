-- ============================================================================
-- 2026-09-06-001-bulk-enrollment.up.sql
--
-- v9.247 / roadmap P2.4 (bulk enrollment pipeline): the staging + batch tables
-- for COPY-based batch issuance. ADDS ONLY (two tables + an index); the
-- procedure uc_bulk_issue is in 05_procedures.sql and reaches an upgraded
-- database through --sync-objects after this runs. No existing object changes.
-- ============================================================================
-- ============================================================================
-- Bulk enrollment pipeline (roadmap P2.4, v9.247)
--
-- Onboarding an authority's existing population is millions of one-at-a-time
-- issuances through uc1_issue_and_activate. The bulk path stages the records
-- with COPY, then issues them SET-BASED in one transaction: every row still
-- runs through the full constraint set (the C3 partial unique index, the M:N
-- signature invariant, the append-only lifecycle events, the state machine,
-- the FKs and CHECKs), and a single violating row rolls back the whole batch
-- (all rows are issued, or none are). One batch is one authority under one
-- algorithm, the shape of a real migration.
-- ============================================================================
CREATE TABLE IF NOT EXISTS BulkEnrollmentBatch (
    batch_id          SERIAL PRIMARY KEY,
    issuing_agency_id INTEGER NOT NULL REFERENCES Agency(agency_id),
    algorithm_id      INTEGER NOT NULL REFERENCES CryptographicAlgorithm(algorithm_id),
    note              VARCHAR(200),
    created_at        TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    issued_at         TIMESTAMP,
    rows_issued       INTEGER
);

CREATE TABLE IF NOT EXISTS BulkEnrollmentStaging (
    staging_id             BIGSERIAL PRIMARY KEY,
    batch_id               INTEGER NOT NULL REFERENCES BulkEnrollmentBatch(batch_id),  -- no cascade (audit rule); clean staging explicitly
    legal_name             VARCHAR(200) NOT NULL,
    date_of_birth          DATE NOT NULL,
    jurisdiction           VARCHAR(10) NOT NULL,
    biometric_binding_type VARCHAR(20) NOT NULL,
    witness_agency_id      INTEGER,
    liveness_check_type    VARCHAR(20),
    token_value            VARCHAR(128) NOT NULL,
    physical_serial        VARCHAR(64) NOT NULL,
    hardware_model         VARCHAR(50),
    permitted_contexts     INTEGER[] NOT NULL DEFAULT '{}',
    individual_id          INTEGER,   -- COPY leaves NULL = new person; set it to correlate a re-card to an existing individual
    token_id               INTEGER
);
CREATE INDEX IF NOT EXISTS idx_bulkstaging_batch ON BulkEnrollmentStaging(batch_id);
