-- ============================================================================
-- 2026-05-15-002-verification-purpose.up.sql
--
-- v9.20 / item 3 of the architecture-study joint recommendation.
-- per a recorded decision
-- Position A.
--
-- Adds VerificationEvent.requesting_purpose_text — operator-supplied
-- free-text reason for THIS SPECIFIC verification (max 280 chars).
-- Anti-coercion-direct: a coerced verification leaves a stated-purpose
-- trail. The coercer's stated context becomes part of the
-- evidentiary chain.
--
-- Design:
--   - NULLABLE for backwards compatibility (legacy paths don't break)
--   - Append-only via existing reject_audit_modification trigger
--     on VerificationEvent (no separate trigger needed; the table-level
--     append-only invariant covers the new column automatically)
--   - 280-char CHECK (matches a tweet's worth of context; enough for
--     "border crossing JFK T4 2026-05-15" without enabling abusive
--     free-form data smuggling)
--   - NO LLM-based classification or validation (per Sanctum §IV.3)
-- ============================================================================

-- Idempotent. requesting_purpose_text (+ its CHECK) is also defined in
-- 01_schema.sql so the canonical schema is complete on its own; on a fresh
-- 00_load_all build the column + constraint already exist and these statements
-- are no-ops, while on an older deployed database they add them. (CI applies
-- migrations after the schema load.)
ALTER TABLE VerificationEvent
    ADD COLUMN IF NOT EXISTS requesting_purpose_text VARCHAR(280);

COMMENT ON COLUMN VerificationEvent.requesting_purpose_text IS
    'v9.20 / a recorded decision (verification-purpose-and-audit-access). '
    'Operator-supplied free-text reason for THIS verification. NULL for '
    'legacy rows + cases where no purpose was supplied. Append-only via '
    'the table-level VerificationEvent trigger.';

-- Length CHECK: 280 chars is the cap; zero-length is disallowed (a NULL is the
-- legitimate "no purpose supplied" path; empty string is operator error).
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'chk_purpose_text_length'
    ) THEN
        ALTER TABLE VerificationEvent
            ADD CONSTRAINT chk_purpose_text_length CHECK (
                requesting_purpose_text IS NULL
                OR char_length(TRIM(BOTH FROM requesting_purpose_text)) BETWEEN 1 AND 280
            );
    END IF;
END $$;

-- Optional: an index for purpose-text search (not strictly needed but
-- helpful when investigating "what verifications mentioned X")
CREATE INDEX IF NOT EXISTS idx_verification_purpose_text_gin
    ON VerificationEvent USING GIN (to_tsvector('english', requesting_purpose_text))
    WHERE requesting_purpose_text IS NOT NULL;

-- ============================================================================
-- Smoke (idempotent; runs at migration apply time only)
-- ============================================================================
DO $verify_purpose_smoke$
DECLARE
    v_col_exists BOOLEAN;
BEGIN
    SELECT EXISTS (
        SELECT 1 FROM information_schema.columns
         WHERE table_name = 'verificationevent'
           AND column_name = 'requesting_purpose_text'
    ) INTO v_col_exists;
    IF NOT v_col_exists THEN
        RAISE EXCEPTION '2026-05-15-002-verification-purpose: column not created';
    END IF;
    RAISE NOTICE '2026-05-15-002-verification-purpose: column added + CHECK + GIN index';
END;
$verify_purpose_smoke$;
