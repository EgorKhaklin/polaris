-- ============================================================================
-- 2026-06-05-002-individual-erasure.down.sql
--
-- Revert v9.125: drop the pseudonymization procedure and the erasure log.
-- Dropping IndividualErasureEvent discards the record of which holders were
-- pseudonymized (the pseudonymized legal_name values themselves remain on the
-- Individual rows; reverting the schema does not un-erase a name). Reverting
-- removes only the mechanism and its audit table, not the effects already
-- applied.
-- ============================================================================

DROP PROCEDURE IF EXISTS uc_pseudonymize_individual(INTEGER, INTEGER, VARCHAR);

DROP TRIGGER IF EXISTS trg_erasure_append_only ON IndividualErasureEvent;

DROP TABLE IF EXISTS IndividualErasureEvent;
