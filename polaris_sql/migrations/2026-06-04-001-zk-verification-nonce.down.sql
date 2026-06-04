-- ============================================================================
-- 2026-06-04-001-zk-verification-nonce.down.sql
--
-- Reverses 2026-06-04-001-zk-verification-nonce.up.sql. Drops the single-use
-- nonce store. Reverting re-opens the ZK-verify replay window (T-T2), so this is
-- a true inverse only in the sense of restoring the pre-v9.89 schema — the
-- application code in that prior state did not consume nonces either.
-- ============================================================================

DROP TABLE IF EXISTS ZkVerificationNonce;
