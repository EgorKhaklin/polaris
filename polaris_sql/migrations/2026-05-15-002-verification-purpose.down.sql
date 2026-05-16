-- ============================================================================
-- 2026-05-15-002-verification-purpose.down.sql
--
-- Revert: drop the GIN index, the CHECK constraint, and the column.
-- Note: this irrecoverably loses any operator-supplied purpose text
-- stored in the column. The Architect's caution: down-migrations on
-- audit-table columns destroy historical purpose data that may have
-- evidentiary value. Operator should consider whether this revert is
-- actually what they want.
-- ============================================================================

DROP INDEX IF EXISTS idx_verification_purpose_text_gin;

ALTER TABLE VerificationEvent
    DROP CONSTRAINT IF EXISTS chk_purpose_text_length;

ALTER TABLE VerificationEvent
    DROP COLUMN IF EXISTS requesting_purpose_text;
