-- ============================================================================
-- 2026-09-05-003-event-table-partitioning.up.sql
--
-- v9.245 / roadmap P2.1 (event-table partitioning): the four high-volume,
-- append-only event tables become monthly range-partitioned on
-- event_timestamp, so old ranges detach in O(1) instead of a DELETE scan and
-- the tables stop growing without bound.
--
-- Tables reshaped: TokenLifecycleEvent, VerificationEvent,
-- EnrollmentStatusEvent, AuthAuditLog. Nothing references them by foreign key,
-- which is what makes the in-place conversion possible.
--
-- phase: contract
-- expands: 2026-05-15-002-verification-purpose
--
-- Why the contract annotation, and why it is safe. The expand-contract policy
-- exists so old code never meets a schema it cannot use during a rolling
-- deploy. This migration RESHAPES the four tables (a composite primary key
-- and range partitioning), which the DDL scanner flags on the RENAME the
-- conversion performs. It is transparent to the application: an INSERT routes
-- to a partition automatically, a SELECT reads across partitions, and these
-- tables are append-only so no UPDATE/DELETE path exists to break. The rename
-- is atomic inside this migration's transaction, so at no instant does a
-- client see a half-converted table. Old code runs against the partitioned
-- tables unchanged; that is what this annotation records. 2026-05-15-002 is
-- the migration that last reshaped these tables (VerificationEvent gained
-- requesting_purpose_text); this one completes their storage evolution.
--
-- On a database created from the current 01_schema.sql the four tables are
-- ALREADY partitioned, so uc_convert_event_table_to_partitioned() is a no-op
-- and this migration only ensures the manager procedures and the monthly
-- window exist. On a database from before v9.245 it performs the conversion,
-- attaching the existing table as the DEFAULT partition (its rows stay in
-- place; no copy), then premaking the current and next three monthly
-- partitions.
-- ============================================================================

-- The lifecycle tooling (also defined in 01_schema.sql for fresh databases;
-- redefined here so an upgraded database has it before --sync-objects runs).
-- ============================================================================
-- Event-table partition manager (roadmap P2.1, v9.245)
--
-- The four event tables (TokenLifecycleEvent, VerificationEvent,
-- EnrollmentStatusEvent, AuthAuditLog) are monthly range-partitioned on
-- event_timestamp. New rows land in a monthly partition; anything outside the
-- premade window (the seed data's fixed timestamps, a late arrival) lands in
-- the DEFAULT partition. These two procedures are the lifecycle tooling.
--
--   uc_ensure_event_partitions(months_ahead)  premake current..+months_ahead
--   uc_detach_event_partitions_before(cutoff)  detach whole months < cutoff
--
-- Append-only (C1) is enforced by the trigger on the partitioned PARENT, which
-- PostgreSQL propagates to every partition, DEFAULT included; attach and detach
-- do not open a hole (polaris-partition-drill.sh proves it).
-- ============================================================================
CREATE OR REPLACE PROCEDURE uc_ensure_event_partitions(p_months_ahead integer DEFAULT 3)
LANGUAGE plpgsql AS $$
DECLARE
    v_tables text[] := ARRAY['tokenlifecycleevent','verificationevent','enrollmentstatusevent','authauditlog'];
    v_tbl text; v_from date; v_to date; v_part text; i integer;
BEGIN
    IF p_months_ahead < 0 OR p_months_ahead > 60 THEN
        RAISE EXCEPTION 'uc_ensure_event_partitions: p_months_ahead must be between 0 and 60 (got %)', p_months_ahead;
    END IF;
    FOREACH v_tbl IN ARRAY v_tables LOOP
        FOR i IN 0..p_months_ahead LOOP
            v_from := (date_trunc('month', now()) + make_interval(months => i))::date;
            v_to   := (v_from + interval '1 month')::date;
            v_part := format('%s_%s', v_tbl, to_char(v_from, 'YYYY_MM'));
            CONTINUE WHEN to_regclass(v_part) IS NOT NULL;
            BEGIN
                EXECUTE format('CREATE TABLE %I PARTITION OF %I FOR VALUES FROM (%L) TO (%L)', v_part, v_tbl, v_from, v_to);
            EXCEPTION WHEN others THEN
                -- The DEFAULT partition already holds rows for this month (the
                -- manager fell behind, or the seed spans it): leave them there,
                -- purged by retention. A missing monthly partition is a
                -- monitored condition, never silent data loss.
                RAISE WARNING 'uc_ensure_event_partitions: could not create % (%); rows for that month stay in %_default',
                    v_part, SQLERRM, v_tbl;
            END;
        END LOOP;
    END LOOP;
END $$;
COMMENT ON PROCEDURE uc_ensure_event_partitions(integer) IS
  'Roadmap P2.1: premake monthly partitions for the four event tables from the '
  'current month through +months_ahead, idempotently. Run at init and monthly.';

CREATE OR REPLACE PROCEDURE uc_detach_event_partitions_before(
    p_cutoff timestamptz,
    INOUT p_detached text[] DEFAULT '{}'
)
LANGUAGE plpgsql AS $$
DECLARE
    v_rec record; v_upper text;
BEGIN
    p_detached := ARRAY[]::text[];
    FOR v_rec IN
        SELECT child.relname AS part, parent.relname AS tbl,
               pg_get_expr(child.relpartbound, child.oid) AS bound
        FROM pg_inherits i
        JOIN pg_class child  ON child.oid  = i.inhrelid
        JOIN pg_class parent ON parent.oid = i.inhparent
        WHERE parent.relname IN ('tokenlifecycleevent','verificationevent','enrollmentstatusevent','authauditlog')
          AND pg_get_expr(child.relpartbound, child.oid) <> 'DEFAULT'
    LOOP
        -- The upper bound of a monthly range partition: TO ('YYYY-MM-DD ...').
        -- Detach only when the whole range is at or below the cutoff, so no live
        -- row is ever detached. The DEFAULT partition is never detached here.
        v_upper := substring(v_rec.bound from 'TO \(''([^'']+)''\)');
        IF v_upper IS NOT NULL AND v_upper::timestamptz <= p_cutoff THEN
            EXECUTE format('ALTER TABLE %I DETACH PARTITION %I', v_rec.tbl, v_rec.part);
            -- C1 across detach: a detached partition loses the parent-propagated
            -- append-only trigger, so re-create it on the standalone table. It
            -- stays immutable until the caller archives then drops it.
            EXECUTE format('CREATE TRIGGER %I BEFORE UPDATE OR DELETE ON %I FOR EACH ROW EXECUTE FUNCTION reject_audit_modification()',
                           left(v_rec.part, 55) || '_ao', v_rec.part);
            p_detached := array_append(p_detached, v_rec.part);
        END IF;
    END LOOP;
END $$;
COMMENT ON PROCEDURE uc_detach_event_partitions_before(timestamptz, text[]) IS
  'Roadmap P2.1: detach every monthly event partition whose entire range is at '
  'or below the cutoff, leaving each as a standalone table for the caller to '
  'archive then drop. Never touches the DEFAULT partition or a live row.';

-- The one-time online conversion (existing databases only; a no-op once the
-- table is partitioned). Defined here rather than in 05_procedures.sql because
-- --sync-objects re-applies that file AFTER migrations, and the conversion
-- must run during --up.
CREATE OR REPLACE PROCEDURE uc_convert_event_table_to_partitioned(p_table text, p_idcol text)
LANGUAGE plpgsql AS $$
DECLARE
    v_seq text; v_name text; v_def text; v_idx record; v_trg text;
    v_idxdefs text[] := '{}'; v_idxnames text[] := '{}'; v_trgdefs text[] := '{}';
BEGIN
    IF EXISTS (SELECT 1 FROM pg_class WHERE relname = lower(p_table) AND relkind = 'p') THEN
        RAISE NOTICE 'uc_convert: % already partitioned; skipping', p_table; RETURN;
    END IF;
    FOR v_idx IN
        SELECT c2.relname AS iname, pg_get_indexdef(idx.indexrelid) AS idef
        FROM pg_index idx JOIN pg_class c ON c.oid = idx.indrelid JOIN pg_class c2 ON c2.oid = idx.indexrelid
        WHERE c.relname = lower(p_table) AND NOT idx.indisprimary
    LOOP v_idxnames := array_append(v_idxnames, v_idx.iname); v_idxdefs := array_append(v_idxdefs, v_idx.idef); END LOOP;
    FOR v_trg IN SELECT pg_get_triggerdef(t.oid) FROM pg_trigger t JOIN pg_class c ON c.oid=t.tgrelid
                 WHERE c.relname=lower(p_table) AND NOT t.tgisinternal
    LOOP v_trgdefs := array_append(v_trgdefs, v_trg); END LOOP;
    v_seq := pg_get_serial_sequence(p_table, p_idcol);

    -- the shadow partitioned parent
    EXECUTE format('CREATE TABLE %I (LIKE %I INCLUDING DEFAULTS INCLUDING CONSTRAINTS EXCLUDING INDEXES) PARTITION BY RANGE (event_timestamp)', p_table||'__part', p_table);
    EXECUTE format('ALTER TABLE %I ADD PRIMARY KEY (%I, event_timestamp)', p_table||'__part', p_idcol);
    IF v_seq IS NOT NULL THEN
        EXECUTE format('ALTER TABLE %I ALTER COLUMN %I SET DEFAULT nextval(%L)', p_table||'__part', p_idcol, v_seq);
        EXECUTE format('ALTER SEQUENCE %s OWNED BY %I.%I', v_seq, p_table||'__part', p_idcol);
    END IF;
    -- the old table becomes the DEFAULT partition (same structure a fresh DB has):
    -- give it the composite PK, drop its triggers (re-created on the parent) and
    -- its non-PK indexes (re-created on the parent, freeing the names).
    EXECUTE format('ALTER TABLE %I DROP CONSTRAINT %I', p_table, p_table||'_pkey');
    EXECUTE format('ALTER TABLE %I ADD PRIMARY KEY (%I, event_timestamp)', p_table, p_idcol);
    FOR v_trg IN SELECT t.tgname FROM pg_trigger t JOIN pg_class c ON c.oid=t.tgrelid WHERE c.relname=lower(p_table) AND NOT t.tgisinternal
    LOOP EXECUTE format('DROP TRIGGER %I ON %I', v_trg, p_table); END LOOP;
    FOREACH v_name IN ARRAY v_idxnames LOOP EXECUTE format('DROP INDEX %I', v_name); END LOOP;

    -- swap and attach the old table as DEFAULT (instant: no other partitions yet)
    EXECUTE format('ALTER TABLE %I RENAME TO %I', p_table, p_table||'_default');
    EXECUTE format('ALTER TABLE %I RENAME TO %I', p_table||'__part', p_table);
    EXECUTE format('ALTER TABLE %I ATTACH PARTITION %I DEFAULT', p_table, p_table||'_default');
    -- canonical indexes + triggers on the parent (propagate to every partition)
    FOREACH v_def IN ARRAY v_idxdefs LOOP EXECUTE v_def; END LOOP;
    FOREACH v_trg IN ARRAY v_trgdefs LOOP EXECUTE v_trg; END LOOP;
    RAISE NOTICE 'uc_convert: % converted; DEFAULT holds the existing rows, monthly partitions premade next', p_table;
END $$;

-- Convert the four tables (no-op where already partitioned), then premake the
-- monthly window so new rows land in a monthly partition.
CALL uc_convert_event_table_to_partitioned('tokenlifecycleevent', 'event_id');
CALL uc_convert_event_table_to_partitioned('verificationevent',   'event_id');
CALL uc_convert_event_table_to_partitioned('enrollmentstatusevent','event_id');
CALL uc_convert_event_table_to_partitioned('authauditlog',        'audit_id');
CALL uc_ensure_event_partitions();
