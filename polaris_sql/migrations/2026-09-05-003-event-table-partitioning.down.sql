-- ============================================================================
-- 2026-09-05-003-event-table-partitioning.down.sql
--
-- Revert of 2026-09-05-003 (v9.245 / P2.1). Converts the four event tables
-- back to plain (non-partitioned) tables, preserving every row, then drops the
-- partition tooling. A reverting database keeps its data and its append-only
-- invariant; it loses O(1) detach-based purge (the DELETE path in
-- uc_archive_purge still works).
--
-- Reverts are exempt from the expand-contract policy; the RENAME here is the
-- reverse of the up migration's swap. Dropping the partitioned parent
-- cascades to any view built on it (e.g. IndividualCurrentEnrollment); the
-- deploy's `polaris-migrate.sh --sync-objects` re-applies the view files, so a
-- revert is completed by a sync, exactly as the retention revert is.
-- ============================================================================
CREATE OR REPLACE PROCEDURE uc_departition_event_table(p_table text, p_idcol text)
LANGUAGE plpgsql AS $$
DECLARE
    v_seq text; v_name text; v_def text; v_idx record; v_trg text;
    v_idxdefs text[] := '{}'; v_trgdefs text[] := '{}';
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_class WHERE relname = lower(p_table) AND relkind = 'p') THEN
        RAISE NOTICE 'uc_departition: % is not partitioned; skipping', p_table; RETURN;
    END IF;
    FOR v_idx IN SELECT pg_get_indexdef(idx.indexrelid) AS idef FROM pg_index idx JOIN pg_class c ON c.oid=idx.indrelid
                 WHERE c.relname=lower(p_table) AND NOT idx.indisprimary
    LOOP v_idxdefs := array_append(v_idxdefs, v_idx.idef); END LOOP;
    FOR v_trg IN SELECT pg_get_triggerdef(t.oid) FROM pg_trigger t JOIN pg_class c ON c.oid=t.tgrelid
                 WHERE c.relname=lower(p_table) AND NOT t.tgisinternal
    LOOP v_trgdefs := array_append(v_trgdefs, v_trg); END LOOP;
    v_seq := pg_get_serial_sequence(p_table, p_idcol);

    -- a plain shadow, copy the rows across every partition into it (no PK yet:
    -- the parent still owns the <table>_pkey name until it is dropped below)
    EXECUTE format('CREATE TABLE %I (LIKE %I INCLUDING DEFAULTS INCLUDING CONSTRAINTS EXCLUDING INDEXES)', p_table||'__plain', p_table);
    EXECUTE format('INSERT INTO %I SELECT * FROM %I', p_table||'__plain', p_table);
    IF v_seq IS NOT NULL THEN
        EXECUTE format('ALTER SEQUENCE %s OWNED BY %I.%I', v_seq, p_table||'__plain', p_idcol);  -- the sequence survives the DROP
        EXECUTE format('ALTER TABLE %I ALTER COLUMN %I SET DEFAULT nextval(%L)', p_table||'__plain', p_idcol, v_seq);
    END IF;
    EXECUTE format('DROP TABLE %I CASCADE', p_table);           -- drops the parent + partitions, frees the pkey name
    EXECUTE format('ALTER TABLE %I RENAME TO %I', p_table||'__plain', p_table);
    -- now the plain table owns the canonical name; give it the plain PK a re-apply of the up expects
    EXECUTE format('ALTER TABLE %I ADD CONSTRAINT %I PRIMARY KEY (%I)', p_table, p_table||'_pkey', p_idcol);
    FOREACH v_def IN ARRAY v_idxdefs LOOP EXECUTE v_def; END LOOP;
    FOREACH v_trg IN ARRAY v_trgdefs LOOP EXECUTE v_trg; END LOOP;
    RAISE NOTICE 'uc_departition: % reverted to a plain table', p_table;
END $$;

CALL uc_departition_event_table('tokenlifecycleevent', 'event_id');
CALL uc_departition_event_table('verificationevent',   'event_id');
CALL uc_departition_event_table('enrollmentstatusevent','event_id');
CALL uc_departition_event_table('authauditlog',        'audit_id');

DROP PROCEDURE IF EXISTS uc_departition_event_table(text, text);
DROP PROCEDURE IF EXISTS uc_convert_event_table_to_partitioned(text, text);
DROP PROCEDURE IF EXISTS uc_detach_event_partitions_before(timestamptz, text[]);
DROP PROCEDURE IF EXISTS uc_ensure_event_partitions(integer);
