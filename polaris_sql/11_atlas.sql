-- ============================================================================
-- AI-context: this file is performance-critical and the architecture decisions
--   in it are NON-OBVIOUS. Read these before editing:
--     ../docs/reference/SCALING.md                          ← architectural treatment
--     ../DEVNOTES/atlas-scaling.md           ← what NOT to change without measuring
-- ============================================================================

-- ============================================================================
-- POLARIS — IDENTITY TOKEN SYSTEM
-- 11_atlas.sql : Server-side spatial aggregation for /atlas at scale
--
-- The Atlas page renders potentially millions of verification and lifecycle
-- events on a globe. Sending every event to the browser is infeasible:
--
--   100 events:    ~30 KB JSON, renders in 50 ms          ← current sample
--   10,000:        ~3 MB JSON, renders in ~1 second
--   100,000:       ~30 MB JSON, renders in ~10 seconds
--   1,000,000:     ~300 MB JSON, browser hangs / OOMs
--   2,000,000:     completely impossible client-side
--
-- The fix is server-side spatial aggregation. The browser sends the visible
-- bounding box and a target grid resolution; the server returns at most a
-- few hundred CLUSTERS (centroid + summary stats) at low zoom, and switches
-- to individual reticles only when the user has zoomed close enough that
-- the cluster count drops below the cluster threshold.
--
-- CONTRACT
--   atlas_clusters_verifications(min_lat, min_lon, max_lat, max_lon, grid)
--     RETURNS TABLE (lat, lon, n_total, n_failure, n_pq, n_zk, n_full)
--   atlas_clusters_lifecycles(min_lat, min_lon, max_lat, max_lon, grid)
--     RETURNS TABLE (lat, lon, n_total, n_revoked, n_lost, n_issued, n_activated)
--
-- The grid argument is a granularity in DECIMAL DEGREES. Pick it to keep
-- the cluster count at the desired density (the API layer maps zoom level
-- to grid size).
--
-- ALL FUNCTIONS ARE STABLE: same args + same data → same result, no side
-- effects. PostgreSQL can therefore inline them and cache plans.
-- ============================================================================

-- ----------------------------------------------------------------------------
-- atlas_clusters_verifications
--
-- Bins verification events by (floor(lat / grid), floor(lon / grid)) and
-- returns the centroid + count + diagnostic flag counts per bin. Excludes
-- rows with NULL coordinates (legacy data without recorded location).
--
-- Filtering by event_type is done client-side via the kind=verification
-- filter chip; this function returns ALL verifications in the bbox so the
-- browser can drive its own filter chips without re-querying. (Filter-aware
-- variants would multiply API surface; the bbox alone reduces volume by 10⁵
-- in practice.)
-- ----------------------------------------------------------------------------

-- v8.3 (A+C): bin function gained four optional filters used by the v8.3
-- temporal/filter UI. Each is NULL = "no filter" so existing callers that
-- still pass 5 positional args work unchanged via DEFAULT NULL.
DROP FUNCTION IF EXISTS atlas_clusters_verifications(
    DOUBLE PRECISION, DOUBLE PRECISION, DOUBLE PRECISION, DOUBLE PRECISION,
    DOUBLE PRECISION);

CREATE OR REPLACE FUNCTION atlas_clusters_verifications(
    p_min_lat   DOUBLE PRECISION,
    p_min_lon   DOUBLE PRECISION,
    p_max_lat   DOUBLE PRECISION,
    p_max_lon   DOUBLE PRECISION,
    p_grid      DOUBLE PRECISION,
    p_since     TIMESTAMP DEFAULT NULL,        -- only events ≥ this time
    p_outcomes  TEXT      DEFAULT NULL,         -- CSV: 'FAILURE,UNAUTHORIZED'
    p_disclosure TEXT     DEFAULT NULL,         -- CSV: 'FULL'
    p_contexts  TEXT      DEFAULT NULL          -- CSV: 'BANKING,TRAVEL'
) RETURNS TABLE (
    lat        DOUBLE PRECISION,
    lon        DOUBLE PRECISION,
    n_total    BIGINT,
    n_failure  BIGINT,
    n_pq       BIGINT,
    n_zk       BIGINT,
    n_full     BIGINT
)
LANGUAGE sql
STABLE
AS $$
    SELECT
        avg(ve.latitude)                                   AS lat,
        avg(ve.longitude)                                  AS lon,
        count(*)                                           AS n_total,
        count(*) FILTER (WHERE ve.outcome = 'FAILURE')     AS n_failure,
        count(*) FILTER (WHERE ca.quantum_resistant)       AS n_pq,
        count(*) FILTER (WHERE ve.disclosure_level = 'ZERO_KNOWLEDGE') AS n_zk,
        count(*) FILTER (WHERE ve.disclosure_level = 'FULL')           AS n_full
    FROM      VerificationEvent ve
    LEFT JOIN IdentityToken          t  ON ve.token_id     = t.token_id
    LEFT JOIN CryptographicAlgorithm ca ON t.algorithm_id  = ca.algorithm_id
    LEFT JOIN VerificationContext    vc ON ve.context_id   = vc.context_id
    WHERE ve.latitude  IS NOT NULL
      AND ve.longitude IS NOT NULL
      -- C6: ZERO_KNOWLEDGE verifications must not appear on the spatial map at
      -- all. A grid cell containing a single ZK event would otherwise leak its
      -- exact location via avg(lat/lon), and the GROUP BY itself pins each ZK
      -- event to a cell. ZK activity is reported non-spatially by atlas_stats.
      -- (n_zk is therefore structurally 0 in this aggregate.)
      AND ve.disclosure_level <> 'ZERO_KNOWLEDGE'
      AND ve.latitude  BETWEEN p_min_lat AND p_max_lat
      AND (
            (p_min_lon <= p_max_lon AND ve.longitude BETWEEN p_min_lon AND p_max_lon)
         OR (p_min_lon  > p_max_lon AND (ve.longitude >= p_min_lon OR ve.longitude <= p_max_lon))
      )
      AND (p_since      IS NULL OR ve.event_timestamp >= p_since)
      AND (p_outcomes   IS NULL OR ve.outcome         = ANY(string_to_array(p_outcomes, ',')))
      AND (p_disclosure IS NULL OR ve.disclosure_level = ANY(string_to_array(p_disclosure, ',')))
      AND (p_contexts   IS NULL OR vc.context_type     = ANY(string_to_array(p_contexts, ',')))
    GROUP BY floor(ve.latitude  / p_grid),
             floor(ve.longitude / p_grid);
$$;

COMMENT ON FUNCTION atlas_clusters_verifications IS
  'Bins VerificationEvent rows in the bbox into a grid of size p_grid '
  '(decimal degrees). Returns centroid + total + diagnostic flag counts per '
  'bin. Used by GET /api/atlas/clusters when kind=verification.';


-- ----------------------------------------------------------------------------
-- atlas_clusters_lifecycles
--
-- Same idea for TokenLifecycleEvent. The flag counts surface terminal
-- transitions (REVOKED, LOST) which are operationally interesting at the
-- aggregate level — a cluster with high revocation rate tells the operator
-- to investigate that area.
-- ----------------------------------------------------------------------------

DROP FUNCTION IF EXISTS atlas_clusters_lifecycles(
    DOUBLE PRECISION, DOUBLE PRECISION, DOUBLE PRECISION, DOUBLE PRECISION,
    DOUBLE PRECISION);

CREATE OR REPLACE FUNCTION atlas_clusters_lifecycles(
    p_min_lat     DOUBLE PRECISION,
    p_min_lon     DOUBLE PRECISION,
    p_max_lat     DOUBLE PRECISION,
    p_max_lon     DOUBLE PRECISION,
    p_grid        DOUBLE PRECISION,
    p_since       TIMESTAMP DEFAULT NULL,
    p_event_types TEXT      DEFAULT NULL    -- CSV: 'REVOKED,LOST'
) RETURNS TABLE (
    lat          DOUBLE PRECISION,
    lon          DOUBLE PRECISION,
    n_total      BIGINT,
    n_revoked    BIGINT,
    n_lost       BIGINT,
    n_issued     BIGINT,
    n_activated  BIGINT
)
LANGUAGE sql
STABLE
AS $$
    SELECT
        avg(latitude)                                          AS lat,
        avg(longitude)                                         AS lon,
        count(*)                                               AS n_total,
        count(*) FILTER (WHERE event_type = 'REVOKED')         AS n_revoked,
        count(*) FILTER (WHERE event_type = 'LOST')            AS n_lost,
        count(*) FILTER (WHERE event_type = 'ISSUED')          AS n_issued,
        count(*) FILTER (WHERE event_type = 'ACTIVATED')       AS n_activated
    FROM TokenLifecycleEvent
    WHERE latitude  IS NOT NULL
      AND longitude IS NOT NULL
      AND latitude  BETWEEN p_min_lat AND p_max_lat
      AND (
            (p_min_lon <= p_max_lon AND longitude BETWEEN p_min_lon AND p_max_lon)
         OR (p_min_lon  > p_max_lon AND (longitude >= p_min_lon OR longitude <= p_max_lon))
      )
      AND (p_since       IS NULL OR event_timestamp >= p_since)
      AND (p_event_types IS NULL OR event_type      = ANY(string_to_array(p_event_types, ',')))
    GROUP BY floor(latitude  / p_grid),
             floor(longitude / p_grid);
$$;

COMMENT ON FUNCTION atlas_clusters_lifecycles IS
  'Bins TokenLifecycleEvent rows in the bbox into a grid of size p_grid '
  '(decimal degrees). Used by GET /api/atlas/clusters when kind=lifecycle.';


-- ----------------------------------------------------------------------------
-- atlas_points_verifications
--
-- Returns INDIVIDUAL verification events in a bbox, hard-capped at p_limit.
-- Used at high zoom (city / neighborhood) where the user wants every
-- reticle. The cap protects the wire and the renderer.
-- ----------------------------------------------------------------------------

DROP FUNCTION IF EXISTS atlas_points_verifications(
    DOUBLE PRECISION, DOUBLE PRECISION, DOUBLE PRECISION, DOUBLE PRECISION, INTEGER);

CREATE OR REPLACE FUNCTION atlas_points_verifications(
    p_min_lat   DOUBLE PRECISION,
    p_min_lon   DOUBLE PRECISION,
    p_max_lat   DOUBLE PRECISION,
    p_max_lon   DOUBLE PRECISION,
    p_limit     INTEGER,
    p_since     TIMESTAMP DEFAULT NULL,
    p_outcomes  TEXT      DEFAULT NULL,
    p_disclosure TEXT     DEFAULT NULL,
    p_contexts  TEXT      DEFAULT NULL
) RETURNS TABLE (
    event_id          INTEGER,
    lat               DOUBLE PRECISION,
    lon               DOUBLE PRECISION,
    event_timestamp   TIMESTAMP,
    token_id          INTEGER,
    holder_name       TEXT,
    agency_name       TEXT,
    context_type      TEXT,
    outcome           TEXT,
    disclosure_level  TEXT,
    algorithm_name    TEXT,
    pq                BOOLEAN,
    requestor_location TEXT
)
LANGUAGE sql
STABLE
AS $$
    SELECT
        ve.event_id,
        ve.latitude,
        ve.longitude,
        ve.event_timestamp,
        ve.token_id,
        i.legal_name::TEXT             AS holder_name,
        ag.name::TEXT                  AS agency_name,
        vc.context_type::TEXT          AS context_type,
        ve.outcome::TEXT               AS outcome,
        ve.disclosure_level::TEXT      AS disclosure_level,
        ca.name::TEXT        AS algorithm_name,
        COALESCE(ca.quantum_resistant, FALSE) AS pq,
        ve.requestor_location::TEXT    AS requestor_location
    FROM      VerificationEvent ve
    JOIN      Agency               ag ON ve.requesting_agency_id = ag.agency_id
    JOIN      VerificationContext  vc ON ve.context_id           = vc.context_id
    LEFT JOIN IdentityToken         t ON ve.token_id             = t.token_id
    LEFT JOIN Individual            i ON t.individual_id         = i.individual_id
    LEFT JOIN CryptographicAlgorithm ca ON t.algorithm_id        = ca.algorithm_id
    WHERE ve.latitude  IS NOT NULL
      AND ve.longitude IS NOT NULL
      -- C6: a ZERO_KNOWLEDGE verification proves validity without revealing the
      -- holder; its precise location is exactly the spatial side-channel that
      -- would de-anonymize it (especially co-located with a SELECTIVE/FULL
      -- event). uc7_warrant_audit redacts requestor_location for ZK rows; the
      -- precise-points layer must not plot them at all. Aggregate/count layers
      -- may still include ZK without a precise location.
      AND ve.disclosure_level <> 'ZERO_KNOWLEDGE'
      AND ve.latitude  BETWEEN p_min_lat AND p_max_lat
      AND (
            (p_min_lon <= p_max_lon AND ve.longitude BETWEEN p_min_lon AND p_max_lon)
         OR (p_min_lon  > p_max_lon AND (ve.longitude >= p_min_lon OR ve.longitude <= p_max_lon))
      )
      AND (p_since      IS NULL OR ve.event_timestamp >= p_since)
      AND (p_outcomes   IS NULL OR ve.outcome         = ANY(string_to_array(p_outcomes, ',')))
      AND (p_disclosure IS NULL OR ve.disclosure_level = ANY(string_to_array(p_disclosure, ',')))
      AND (p_contexts   IS NULL OR vc.context_type     = ANY(string_to_array(p_contexts, ',')))
    ORDER BY ve.event_timestamp DESC
    LIMIT p_limit;
$$;


-- ----------------------------------------------------------------------------
-- atlas_points_lifecycles
-- ----------------------------------------------------------------------------

DROP FUNCTION IF EXISTS atlas_points_lifecycles(
    DOUBLE PRECISION, DOUBLE PRECISION, DOUBLE PRECISION, DOUBLE PRECISION, INTEGER);

CREATE OR REPLACE FUNCTION atlas_points_lifecycles(
    p_min_lat     DOUBLE PRECISION,
    p_min_lon     DOUBLE PRECISION,
    p_max_lat     DOUBLE PRECISION,
    p_max_lon     DOUBLE PRECISION,
    p_limit       INTEGER,
    p_since       TIMESTAMP DEFAULT NULL,
    p_event_types TEXT      DEFAULT NULL
) RETURNS TABLE (
    event_id        INTEGER,
    lat             DOUBLE PRECISION,
    lon             DOUBLE PRECISION,
    event_timestamp TIMESTAMP,
    token_id        INTEGER,
    event_type      TEXT,
    reason_code     TEXT,
    holder_name     TEXT,
    agency_name     TEXT,
    algorithm_name  TEXT,
    pq              BOOLEAN
)
LANGUAGE sql
STABLE
AS $$
    SELECT
        le.event_id,
        le.latitude,
        le.longitude,
        le.event_timestamp,
        le.token_id,
        le.event_type::TEXT,
        le.reason_code::TEXT,
        i.legal_name::TEXT,
        ag.name::TEXT,
        ca.name::TEXT,
        COALESCE(ca.quantum_resistant, FALSE) AS pq
    FROM      TokenLifecycleEvent le
    LEFT JOIN Agency               ag ON le.actor_agency_id = ag.agency_id
    JOIN      IdentityToken         t ON le.token_id        = t.token_id
    JOIN      Individual            i ON t.individual_id    = i.individual_id
    JOIN      CryptographicAlgorithm ca ON t.algorithm_id    = ca.algorithm_id
    WHERE le.latitude  IS NOT NULL
      AND le.longitude IS NOT NULL
      AND le.latitude  BETWEEN p_min_lat AND p_max_lat
      AND (
            (p_min_lon <= p_max_lon AND le.longitude BETWEEN p_min_lon AND p_max_lon)
         OR (p_min_lon  > p_max_lon AND (le.longitude >= p_min_lon OR le.longitude <= p_max_lon))
      )
      AND (p_since       IS NULL OR le.event_timestamp >= p_since)
      AND (p_event_types IS NULL OR le.event_type      = ANY(string_to_array(p_event_types, ',')))
    ORDER BY le.event_timestamp DESC
    LIMIT p_limit;
$$;


-- ----------------------------------------------------------------------------
-- atlas_stats — bbox-scoped HUD signals
--
-- Computes the four operational ratios shown in the Atlas HUD scoped to the
-- visible bounding box. So as the user pans / zooms, the numbers update to
-- reflect what they're actually looking at — not the global aggregates.
-- ----------------------------------------------------------------------------

DROP FUNCTION IF EXISTS atlas_stats(
    DOUBLE PRECISION, DOUBLE PRECISION, DOUBLE PRECISION, DOUBLE PRECISION);

CREATE OR REPLACE FUNCTION atlas_stats(
    p_min_lat DOUBLE PRECISION,
    p_min_lon DOUBLE PRECISION,
    p_max_lat DOUBLE PRECISION,
    p_max_lon DOUBLE PRECISION,
    p_since   TIMESTAMP DEFAULT NULL
) RETURNS TABLE (
    n_active_tokens BIGINT,
    n_anomalies     BIGINT,
    n_failures      BIGINT,
    n_full          BIGINT,
    pq_pct          NUMERIC,
    zk_pct          NUMERIC,
    n_verifs        BIGINT,
    n_lifecycles    BIGINT
)
LANGUAGE sql
STABLE
AS $$
    -- Single-pass aggregation. The previous version had a CTE referenced 8
    -- times; PostgreSQL re-scanned it on each reference (~70ms × 8). The
    -- rewritten version joins once and computes everything via FILTER
    -- aggregates in a single SELECT. At 2M rows this takes ~250ms instead
    -- of ~1400ms.
    WITH
    v_agg AS (
        SELECT
            count(*)                                                   AS total,
            count(*) FILTER (WHERE ve.outcome = 'FAILURE')             AS failures,
            count(*) FILTER (WHERE ve.disclosure_level = 'FULL')       AS fulls,
            count(*) FILTER (WHERE ve.disclosure_level = 'ZERO_KNOWLEDGE') AS zks,
            count(*) FILTER (WHERE ve.token_id IS NOT NULL)            AS with_token,
            count(*) FILTER (WHERE ve.token_id IS NOT NULL AND ca.quantum_resistant) AS pq_count
        FROM      VerificationEvent ve
        LEFT JOIN IdentityToken          t  ON ve.token_id    = t.token_id
        LEFT JOIN CryptographicAlgorithm ca ON t.algorithm_id = ca.algorithm_id
        WHERE ve.latitude  IS NOT NULL
          AND ve.longitude IS NOT NULL
          AND ve.latitude  BETWEEN p_min_lat AND p_max_lat
          AND (
            (p_min_lon <= p_max_lon AND ve.longitude BETWEEN p_min_lon AND p_max_lon)
         OR (p_min_lon  > p_max_lon AND (ve.longitude >= p_min_lon OR ve.longitude <= p_max_lon))
      )
          AND (p_since IS NULL OR ve.event_timestamp >= p_since)
    ),
    l_agg AS (
        SELECT count(*) AS total
        FROM TokenLifecycleEvent
        WHERE latitude  IS NOT NULL
          AND longitude IS NOT NULL
          AND latitude  BETWEEN p_min_lat AND p_max_lat
          AND (
            (p_min_lon <= p_max_lon AND longitude BETWEEN p_min_lon AND p_max_lon)
         OR (p_min_lon  > p_max_lon AND (longitude >= p_min_lon OR longitude <= p_max_lon))
      )
          AND (p_since IS NULL OR event_timestamp >= p_since)
    )
    SELECT
        (SELECT count(*) FROM IdentityToken WHERE status = 'ACTIVE')::BIGINT AS n_active_tokens,
        (v.failures + v.fulls)::BIGINT                              AS n_anomalies,
        v.failures::BIGINT                                          AS n_failures,
        v.fulls::BIGINT                                             AS n_full,
        CASE WHEN v.with_token > 0
             THEN ROUND(100.0 * v.pq_count / v.with_token, 0)
             ELSE 0 END::NUMERIC                                     AS pq_pct,
        CASE WHEN v.total > 0
             THEN ROUND(100.0 * v.zks / v.total, 0)
             ELSE 0 END::NUMERIC                                     AS zk_pct,
        v.total::BIGINT                                              AS n_verifs,
        l.total::BIGINT                                              AS n_lifecycles
    FROM v_agg v, l_agg l;
$$;

COMMENT ON FUNCTION atlas_stats IS
  'Returns the four operational ratios in the Atlas HUD, scoped to the '
  'currently visible bounding box. Active Tokens is global (system-wide '
  'authoritative count); Anomalies, PQ %, ZK % are bbox-scoped so they '
  'change as the user pans and zooms.';


-- ----------------------------------------------------------------------------
-- atlas_recent_events — paginated event feed for the Atlas right rail
--
-- Cursor pagination by (event_timestamp DESC, event_id DESC). The cursor
-- format is ISO-8601 timestamp + event_id, both ascending or both
-- descending. Passing NULL for the cursor returns the first page.
--
-- Returns up to p_limit events, mixing verifications and lifecycle events
-- in time order with a discriminator column so the client can render each
-- with the appropriate visual treatment.
-- ----------------------------------------------------------------------------

CREATE OR REPLACE FUNCTION atlas_recent_events(
    p_cursor_ts TIMESTAMP DEFAULT NULL,
    p_cursor_id INTEGER   DEFAULT NULL,
    p_limit     INTEGER   DEFAULT 50
) RETURNS TABLE (
    kind            TEXT,    -- 'verification' or 'lifecycle'
    event_id        INTEGER,
    event_timestamp TIMESTAMP,
    token_id        INTEGER,
    holder_name     TEXT,
    agency_name     TEXT,
    label           TEXT,    -- e.g. "BANKING verification" or "REVOKED"
    detail          TEXT,    -- subtitle: location or reason
    tone            TEXT,    -- 'alert' | 'full' | 'zk' | 'selective' | etc.
    lat             DOUBLE PRECISION,
    lon             DOUBLE PRECISION
)
LANGUAGE sql
STABLE
AS $$
    -- Two-stage top-N + late join. The previous version did UNION ALL of
    -- both tables INCLUDING JOINs to Agency/Context/Token/Individual, then
    -- top-N sorted the result. At 2M rows this materialized 2M joined rows
    -- (~2.4 seconds) just to take 50.
    --
    -- The rewrite: first pull top-N IDs from each table using the
    -- (event_timestamp DESC, event_id DESC) indexes — that's O(N log N)
    -- with N being the limit, not the table size. Each side returns ≤
    -- p_limit rows. Then UNION ALL gives at most 2*p_limit rows; JOIN
    -- metadata only for THOSE rows. At 2M rows this drops to <30ms.
    WITH
    top_v AS (
        SELECT event_id, event_timestamp, token_id, requesting_agency_id,
               context_id, outcome, disclosure_level, requestor_location,
               latitude, longitude
        FROM VerificationEvent
        WHERE p_cursor_ts IS NULL
           OR (event_timestamp, event_id) < (p_cursor_ts, COALESCE(p_cursor_id, 2147483647))
        ORDER BY event_timestamp DESC, event_id DESC
        LIMIT p_limit
    ),
    top_l AS (
        SELECT event_id, event_timestamp, token_id, actor_agency_id,
               event_type, reason_code, latitude, longitude
        FROM TokenLifecycleEvent
        WHERE p_cursor_ts IS NULL
           OR (event_timestamp, event_id) < (p_cursor_ts, COALESCE(p_cursor_id, 2147483647))
        ORDER BY event_timestamp DESC, event_id DESC
        LIMIT p_limit
    ),
    merged AS (
        SELECT
            'verification'::TEXT AS kind,
            tv.event_id,
            tv.event_timestamp,
            tv.token_id,
            COALESCE(i.legal_name::TEXT, '(zero-knowledge)') AS holder_name,
            ag.name::TEXT                                    AS agency_name,
            (vc.context_type || ' verification')::TEXT       AS label,
            -- C6: redact the location of ZERO_KNOWLEDGE verifications in the
            -- feed — no subtitle location and no map coordinates — so a ZK
            -- event appears as activity but never reveals where it happened.
            CASE WHEN tv.disclosure_level = 'ZERO_KNOWLEDGE'
                 THEN NULL ELSE tv.requestor_location::TEXT END AS detail,
            CASE
                WHEN tv.outcome = 'FAILURE'                 THEN 'alert'
                WHEN tv.disclosure_level = 'FULL'           THEN 'full'
                WHEN tv.disclosure_level = 'ZERO_KNOWLEDGE' THEN 'zk'
                                                            ELSE 'selective'
            END::TEXT                                        AS tone,
            CASE WHEN tv.disclosure_level = 'ZERO_KNOWLEDGE'
                 THEN NULL ELSE tv.latitude END              AS lat,
            CASE WHEN tv.disclosure_level = 'ZERO_KNOWLEDGE'
                 THEN NULL ELSE tv.longitude END             AS lon
        FROM      top_v tv
        JOIN      Agency             ag ON tv.requesting_agency_id = ag.agency_id
        JOIN      VerificationContext vc ON tv.context_id          = vc.context_id
        LEFT JOIN IdentityToken      t  ON tv.token_id             = t.token_id
        LEFT JOIN Individual         i  ON t.individual_id         = i.individual_id

        UNION ALL

        SELECT
            'lifecycle'::TEXT AS kind,
            tl.event_id,
            tl.event_timestamp,
            tl.token_id,
            i.legal_name::TEXT                              AS holder_name,
            COALESCE(ag.name::TEXT, '—')                    AS agency_name,
            tl.event_type::TEXT                             AS label,
            COALESCE(tl.reason_code::TEXT, '')              AS detail,
            CASE
                WHEN tl.event_type IN ('REVOKED', 'LOST') THEN 'alert'
                WHEN tl.event_type = 'ACTIVATED'          THEN 'zk'
                                                          ELSE 'full'
            END::TEXT                                        AS tone,
            tl.latitude                                      AS lat,
            tl.longitude                                     AS lon
        FROM      top_l tl
        LEFT JOIN Agency        ag ON tl.actor_agency_id = ag.agency_id
        JOIN      IdentityToken  t ON tl.token_id        = t.token_id
        JOIN      Individual     i ON t.individual_id    = i.individual_id
    )
    SELECT *
    FROM merged
    ORDER BY event_timestamp DESC, event_id DESC
    LIMIT p_limit;
$$;

COMMENT ON FUNCTION atlas_recent_events IS
  'Paginated unified feed of verifications + lifecycle events. Cursor is '
  '(event_timestamp, event_id) descending. Pass NULL cursor for first page.';


-- ----------------------------------------------------------------------------
-- atlas_timeline (v8.3 / A) — bucket counts for the histogram strip
--
-- Buckets the events in [p_since, NOW()] into p_buckets equal time slices
-- and returns one row per bucket: bucket_ts (start of slice), n_total, and
-- n_anomaly (FAILURE outcomes + FULL disclosures + REVOKED/LOST lifecycle).
--
-- Used by GET /api/atlas/timeline to render the small density strip below
-- the toolbar. The strip lets the operator see at a glance whether the
-- selected time window contains a spike — a brief 100x bar in an
-- otherwise flat 24h is much louder than scrubbing through 24h of
-- individual reticles. This is the temporal-lens half of v8.3 V3 plan A.
--
-- Filters mirror the cluster functions so the timeline reflects whatever
-- the operator has selected up-toolbar (e.g., "anomalies-only, last 7d"
-- shows the histogram of just anomalies).
-- ----------------------------------------------------------------------------

DROP FUNCTION IF EXISTS atlas_timeline(
    DOUBLE PRECISION, DOUBLE PRECISION, DOUBLE PRECISION, DOUBLE PRECISION,
    TIMESTAMP, INTEGER, TEXT, TEXT, TEXT, TEXT);

CREATE OR REPLACE FUNCTION atlas_timeline(
    p_min_lat   DOUBLE PRECISION,
    p_min_lon   DOUBLE PRECISION,
    p_max_lat   DOUBLE PRECISION,
    p_max_lon   DOUBLE PRECISION,
    p_since     TIMESTAMP,
    p_buckets   INTEGER,
    p_kind      TEXT      DEFAULT 'verification',  -- or 'lifecycle'
    p_outcomes  TEXT      DEFAULT NULL,
    p_disclosure TEXT     DEFAULT NULL,
    p_contexts  TEXT      DEFAULT NULL
) RETURNS TABLE (
    bucket_ts   TIMESTAMP,
    n_total     BIGINT,
    n_anomaly   BIGINT
)
LANGUAGE sql
STABLE
AS $$
    WITH params AS (
        SELECT
            p_since                                  AS t_start,
            CURRENT_TIMESTAMP                        AS t_end,
            GREATEST(p_buckets, 1)                   AS buckets,
            (extract(epoch FROM (CURRENT_TIMESTAMP - p_since))
             / GREATEST(p_buckets, 1))::DOUBLE PRECISION AS bucket_secs
    ),
    bucketed_v AS (
        SELECT
            (params.t_start
                + (floor(extract(epoch FROM (ve.event_timestamp - params.t_start))
                         / params.bucket_secs) * params.bucket_secs
                  ) * INTERVAL '1 second'
            )::TIMESTAMP                                            AS bucket_ts,
            count(*)                                                AS n_total,
            count(*) FILTER (WHERE
                ve.outcome = 'FAILURE'
             OR ve.disclosure_level = 'FULL'
            )                                                       AS n_anomaly
        FROM VerificationEvent ve
        LEFT JOIN VerificationContext vc ON ve.context_id = vc.context_id,
             params
        WHERE p_kind = 'verification'
          AND ve.latitude  IS NOT NULL
          AND ve.longitude IS NOT NULL
          AND ve.latitude  BETWEEN p_min_lat AND p_max_lat
          AND (
            (p_min_lon <= p_max_lon AND ve.longitude BETWEEN p_min_lon AND p_max_lon)
         OR (p_min_lon  > p_max_lon AND (ve.longitude >= p_min_lon OR ve.longitude <= p_max_lon))
          )
          AND ve.event_timestamp >= params.t_start
          AND ve.event_timestamp <  params.t_end
          AND (p_outcomes   IS NULL OR ve.outcome         = ANY(string_to_array(p_outcomes, ',')))
          AND (p_disclosure IS NULL OR ve.disclosure_level = ANY(string_to_array(p_disclosure, ',')))
          AND (p_contexts   IS NULL OR vc.context_type     = ANY(string_to_array(p_contexts, ',')))
        GROUP BY 1
    ),
    bucketed_l AS (
        SELECT
            (params.t_start
                + (floor(extract(epoch FROM (le.event_timestamp - params.t_start))
                         / params.bucket_secs) * params.bucket_secs
                  ) * INTERVAL '1 second'
            )::TIMESTAMP                                            AS bucket_ts,
            count(*)                                                AS n_total,
            count(*) FILTER (WHERE le.event_type IN ('REVOKED', 'LOST'))
                                                                    AS n_anomaly
        FROM TokenLifecycleEvent le, params
        WHERE p_kind = 'lifecycle'
          AND le.latitude  IS NOT NULL
          AND le.longitude IS NOT NULL
          AND le.latitude  BETWEEN p_min_lat AND p_max_lat
          AND (
            (p_min_lon <= p_max_lon AND le.longitude BETWEEN p_min_lon AND p_max_lon)
         OR (p_min_lon  > p_max_lon AND (le.longitude >= p_min_lon OR le.longitude <= p_max_lon))
          )
          AND le.event_timestamp >= params.t_start
          AND le.event_timestamp <  params.t_end
        GROUP BY 1
    )
    SELECT bucket_ts, n_total, n_anomaly FROM bucketed_v
    UNION ALL
    SELECT bucket_ts, n_total, n_anomaly FROM bucketed_l
    ORDER BY bucket_ts;
$$;

COMMENT ON FUNCTION atlas_timeline IS
  'Bucket counts for the Atlas histogram strip. Slices [p_since, NOW()] '
  'into p_buckets equal time bins and counts events per bin. Returns '
  'sparse rows (no row for empty buckets — the client zero-fills).';
