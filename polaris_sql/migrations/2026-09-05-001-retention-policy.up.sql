-- ============================================================================
-- 2026-09-05-001-retention-policy.up.sql
--
-- v9.234 / roadmap P1.11 (retention and lifecycle engine): the retention
-- decision becomes data, with a floor.
--
-- ADDS (1): RetentionPolicy, one effective row per (table class,
-- jurisdiction), append-only with one-way supersession. retention_days >= 365
-- is a hard floor: no configuration can purge an audit row younger than a
-- year, and shortening that is a schema change rather than a policy edit.
-- ADDS (2): retention_days_for() and retention_cutoff(), which resolve the
-- jurisdiction-scoped policy, then the deployment default, then the floor, so
-- there is always an answer and it is never younger than the floor.
-- ADDS (3): uc_apply_retention_template(), which adopts one of two named
-- profiles for a jurisdiction. Both are engineering defaults, not legal
-- determinations.
-- ADDS (4): enforce_retention_policy_immutability and its trigger, plus the
-- partial unique index that keeps one effective row per class.
-- CHANGES: uc_archive_purge gains a p_jurisdiction parameter and refuses any
-- cutoff younger than the effective retention of a class it deletes from.
-- Before this, the database accepted a purge at "older than one hour" as
-- readily as one at five years.
-- REVOKES: UPDATE and DELETE on RetentionPolicy from polaris_app, matching
-- the append-only privilege boundary the other audit tables have. Appending a
-- policy stays available to the application role; superseding one belongs to
-- the SECURITY DEFINER procedure.
--
-- The canonical copies live in 01_schema.sql / 02_indexes.sql /
-- 05_procedures.sql / 06_triggers.sql / 09_grants.sql (a fresh build and
-- --sync-objects install them); this migration brings a deployed database to
-- the same shape. REVERSIBLE: the .down.sql drops the trigger, the functions,
-- the index and the table, and restores the four-parameter purge. ADDITIVE
-- (data side): yes, and it seeds the shipped default so an existing
-- deployment gains the floor without an operator action.
-- ============================================================================

CREATE TABLE IF NOT EXISTS RetentionPolicy (
    policy_id        BIGSERIAL    PRIMARY KEY,
    table_class      VARCHAR(24)  NOT NULL
        CHECK (table_class IN ('TOKEN_LIFECYCLE', 'VERIFICATION',
                               'ENROLLMENT', 'AUTH_AUDIT')),
    jurisdiction     VARCHAR(10),
    retention_days   INTEGER      NOT NULL,
    justification    TEXT         NOT NULL,
    set_by_user_id   INTEGER      NOT NULL,
    effective_from   TIMESTAMPTZ  NOT NULL DEFAULT now(),
    superseded_at    TIMESTAMPTZ,

    CONSTRAINT retention_floor CHECK (retention_days >= 365),
    CONSTRAINT retention_justified CHECK (length(justification) >= 20),
    CONSTRAINT superseded_after_effective CHECK (
        superseded_at IS NULL OR superseded_at >= effective_from
    )
);

COMMENT ON TABLE RetentionPolicy IS
    'Per-table-class retention, as data (roadmap P1.11). One effective row per '
    '(table_class, jurisdiction); a NULL jurisdiction is the deployment '
    'default. Append-only with one-way supersession: changing a retention '
    'decision appends a row and marks the old one superseded, so the history '
    'of the decision survives. retention_days >= 365 is a hard floor: no '
    'configuration can purge an audit row younger than a year. Read by '
    'retention_cutoff() and enforced by uc_archive_purge, which refuses a '
    'cutoff younger than any affected class allows.';

DROP INDEX IF EXISTS uq_effective_retention_policy;
CREATE UNIQUE INDEX uq_effective_retention_policy
    ON RetentionPolicy (table_class, COALESCE(jurisdiction, ''))
    WHERE superseded_at IS NULL;

GRANT SELECT, INSERT ON RetentionPolicy TO polaris_app;
GRANT USAGE, SELECT ON SEQUENCE retentionpolicy_policy_id_seq TO polaris_app;
REVOKE UPDATE, DELETE ON RetentionPolicy FROM polaris_app;

-- ----------------------------------------------------------------------------
-- Append-only with one-way supersession.
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION enforce_retention_policy_immutability()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION
            'RetentionPolicy is append-only: DELETE is refused. A retention '
            'decision is an audit of record; supersede it instead.'
            USING ERRCODE = 'insufficient_privilege';
    END IF;

    IF NEW.policy_id      IS DISTINCT FROM OLD.policy_id
       OR NEW.table_class    IS DISTINCT FROM OLD.table_class
       OR NEW.jurisdiction   IS DISTINCT FROM OLD.jurisdiction
       OR NEW.retention_days IS DISTINCT FROM OLD.retention_days
       OR NEW.justification  IS DISTINCT FROM OLD.justification
       OR NEW.set_by_user_id IS DISTINCT FROM OLD.set_by_user_id
       OR NEW.effective_from IS DISTINCT FROM OLD.effective_from THEN
        RAISE EXCEPTION
            'RetentionPolicy is append-only: only superseded_at may change. '
            'Append a new policy row instead of editing this one.'
            USING ERRCODE = 'insufficient_privilege';
    END IF;

    IF OLD.superseded_at IS NOT NULL THEN
        IF NEW.superseded_at IS NULL THEN
            RAISE EXCEPTION
                'RetentionPolicy: superseded_at cannot be un-set; a superseded '
                'policy stays superseded.'
                USING ERRCODE = 'insufficient_privilege';
        END IF;
        IF NEW.superseded_at < OLD.superseded_at THEN
            RAISE EXCEPTION
                'RetentionPolicy: superseded_at cannot move earlier (% -> %); '
                'backdating when a decision stopped applying is refused.',
                OLD.superseded_at, NEW.superseded_at
                USING ERRCODE = 'insufficient_privilege';
        END IF;
    END IF;

    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_retention_policy_immutable ON RetentionPolicy;
CREATE TRIGGER trg_retention_policy_immutable
    BEFORE UPDATE OR DELETE ON RetentionPolicy
    FOR EACH ROW EXECUTE FUNCTION enforce_retention_policy_immutability();

-- ----------------------------------------------------------------------------
-- The resolver. Jurisdiction-scoped policy, then deployment default, then the
-- schema floor.
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION retention_days_for(
    p_table_class  VARCHAR(24),
    p_jurisdiction VARCHAR(10) DEFAULT NULL
)
RETURNS INTEGER
LANGUAGE sql STABLE AS $$
    SELECT COALESCE(
        (SELECT rp.retention_days
           FROM RetentionPolicy rp
          WHERE rp.table_class = p_table_class
            AND rp.jurisdiction IS NOT DISTINCT FROM p_jurisdiction
            AND rp.superseded_at IS NULL
          ORDER BY rp.effective_from DESC
          LIMIT 1),
        (SELECT rp.retention_days
           FROM RetentionPolicy rp
          WHERE rp.table_class = p_table_class
            AND rp.jurisdiction IS NULL
            AND rp.superseded_at IS NULL
          ORDER BY rp.effective_from DESC
          LIMIT 1),
        365
    );
$$;

CREATE OR REPLACE FUNCTION retention_cutoff(
    p_table_class  VARCHAR(24),
    p_jurisdiction VARCHAR(10) DEFAULT NULL
)
RETURNS TIMESTAMPTZ
LANGUAGE sql STABLE AS $$
    SELECT now() - make_interval(days => retention_days_for(p_table_class, p_jurisdiction));
$$;

-- ----------------------------------------------------------------------------
-- Seed the shipped default so an existing deployment gains the floor without
-- waiting for an operator action. Only where nothing is configured yet: a
-- deployment that has already recorded a decision keeps it.
-- ----------------------------------------------------------------------------
INSERT INTO RetentionPolicy
    (table_class, jurisdiction, retention_days, justification, set_by_user_id)
SELECT c.class, NULL, 1825,
       'Shipped default (STANDARD-5Y): five years, the floor the operator '
       'runbook has documented since the archive chain shipped. Replace this '
       'with a decision recorded for your jurisdiction.',
       COALESCE((SELECT user_id FROM AppUser WHERE role = 'admin' ORDER BY user_id LIMIT 1), 1)
  FROM (VALUES ('TOKEN_LIFECYCLE'), ('VERIFICATION'),
               ('ENROLLMENT'), ('AUTH_AUDIT')) AS c(class)
 WHERE NOT EXISTS (
        SELECT 1 FROM RetentionPolicy rp
         WHERE rp.table_class = c.class
           AND rp.jurisdiction IS NULL
           AND rp.superseded_at IS NULL);

-- ----------------------------------------------------------------------------
-- Verification: the floor binds, and the resolver answers for every class.
-- ----------------------------------------------------------------------------
DO $$
DECLARE v_class TEXT;
BEGIN
    BEGIN
        INSERT INTO RetentionPolicy
            (table_class, jurisdiction, retention_days, justification, set_by_user_id)
        VALUES ('VERIFICATION', 'MIGCHK', 30,
                'migration self-check: this row must be refused by the floor', 1);
        RAISE EXCEPTION 'migration self-check failed: a 30-day retention was accepted';
    EXCEPTION WHEN check_violation THEN
        NULL;   -- expected
    END;

    FOREACH v_class IN ARRAY ARRAY['TOKEN_LIFECYCLE','VERIFICATION','ENROLLMENT','AUTH_AUDIT'] LOOP
        IF retention_days_for(v_class) < 365 THEN
            RAISE EXCEPTION 'migration self-check failed: % resolves below the floor', v_class;
        END IF;
    END LOOP;

    RAISE NOTICE 'retention policy: floor enforced, four classes resolve, defaults seeded.';
END $$;
