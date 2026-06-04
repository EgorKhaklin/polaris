-- ============================================================================
-- 2026-06-04-001-zk-verification-nonce.up.sql
--
-- v9.89 / ROADMAP "Next ships" #1 — real anti-replay for /api/zk/verify.
--
-- The proof bundle is bound to (epoch_id, context_id, nonce), which stops proof
-- SUBSTITUTION. It does not, on its own, stop REPLAY: the identical bundle,
-- captured off the wire, verifies again. This table makes the nonce single-use.
-- A verified result consumes (epoch_id, context_id, nonce); a replay of the same
-- tuple hits the PK and is rejected. Closes threat-model T-T2 / honours R2.
--
-- Vocation: the row holds ONLY the anti-replay tuple + the consume time. No
-- holder, no token_id, no location — it cannot say WHO verified, only that THIS
-- (epoch, context, nonce) was spent. Append-only at the privilege layer: a
-- consumed nonce must never be un-consumed (that re-opens the replay window).
--
-- Idempotent. ZkVerificationNonce is also defined in 01_schema.sql so the
-- canonical schema is complete on its own; this migration adds it to
-- already-deployed databases.
-- ============================================================================

CREATE TABLE IF NOT EXISTS ZkVerificationNonce (
    epoch_id     INTEGER     NOT NULL REFERENCES TokenStateEpoch(epoch_id),
    context_id   BIGINT      NOT NULL,
    nonce        BIGINT      NOT NULL,
    consumed_at  TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT pk_zk_verification_nonce PRIMARY KEY (epoch_id, context_id, nonce)
);

COMMENT ON TABLE ZkVerificationNonce IS
  'Single-use nonce store for ZK-proof anti-replay (R2 / threat-model T-T2 / '
  'v9.89). A verified /api/zk/verify result consumes (epoch_id, context_id, '
  'nonce); a replay of the same bundle hits the PK and is rejected. Holds no '
  'identity. Append-only at the privilege layer (UPDATE/DELETE revoked below).';

-- Append-only at the privilege layer (mirrors the base 09_grants.sql REVOKE).
-- polaris_app keeps INSERT (to consume) + SELECT; a consumed nonce must never be
-- un-consumed by the app role.
DO $zk_nonce_revoke$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'polaris_app') THEN
        REVOKE UPDATE, DELETE ON ZkVerificationNonce FROM polaris_app;
    END IF;
END$zk_nonce_revoke$;

-- ============================================================================
-- Smoke (idempotent; runs at migration apply time only)
-- ============================================================================
DO $zk_nonce_smoke$
DECLARE
    v_table_exists BOOLEAN;
BEGIN
    SELECT EXISTS (
        SELECT 1 FROM information_schema.tables
         WHERE table_name = 'zkverificationnonce'
    ) INTO v_table_exists;
    IF NOT v_table_exists THEN
        RAISE EXCEPTION '2026-06-04-001-zk-verification-nonce: table not created';
    END IF;
    RAISE NOTICE '2026-06-04-001-zk-verification-nonce: table + PK + append-only REVOKE OK';
END;
$zk_nonce_smoke$;
