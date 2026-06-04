"""
test_check_constraints.py
============================================================================

Schema CHECK-constraint regression suite (v8.80 / ARCH-004).

The Polaris schema declares 50+ named CHECK constraints across ~20 tables.
Each one names an invariant that the database enforces at write time:
status enums, lat/lon ranges, hex-format validation, multi-column
consistency rules, etc.

For most of v8 these constraints went untested — an earlier coherence
check flagged the gap as a long-standing one (41 CHECKs in schema, ~16
in tests). This file closes that gap.

Pattern: each test tries an INSERT that should violate the named
constraint, expects ``psycopg2.errors.CheckViolation``, and rolls back.
A few constraints also have positive boundary-case tests where the
positive case is non-obvious.

This file is independent of the Flask app. It connects directly to
``polaris_test`` as the operator user, uses one transaction per test,
and rolls back. No DB state survives.

Run:
    python3 test_check_constraints.py
    python3 -m unittest test_check_constraints -v

Coverage map: see the class docstrings. Each class is one schema table.
"""

import os
import sys
import unittest

import psycopg2
from psycopg2 import errors as pg_errors
from psycopg2.extras import RealDictCursor

# Import the Flask app's DB_CONFIG so tests stay aligned with app config.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import app as flask_app

DB_CONFIG = flask_app.DB_CONFIG


# ----------------------------------------------------------------------------
# Base case: open a transaction; assertions roll it back
# ----------------------------------------------------------------------------

class _CheckBase(unittest.TestCase):
    """Shared connection-per-test helper.

    Each test opens a fresh connection, runs its INSERT inside a
    transaction, and unconditionally rolls back at tearDown.
    """

    def setUp(self):
        self.conn = psycopg2.connect(cursor_factory=RealDictCursor, **DB_CONFIG)

    def tearDown(self):
        try:
            self.conn.rollback()
        finally:
            self.conn.close()

    def _expect_check_violation(self, sql, params=None, constraint_name=None):
        """Run ``sql`` and assert it raises CheckViolation, optionally
        on a specific constraint."""
        with self.assertRaises(pg_errors.CheckViolation) as ctx:
            with self.conn.cursor() as cur:
                cur.execute(sql, params or ())
        if constraint_name:
            self.assertIn(
                constraint_name,
                str(ctx.exception),
                f"expected CheckViolation on '{constraint_name}'; "
                f"got: {ctx.exception}",
            )


# ============================================================================
# Agency
# ============================================================================

class TestAgencyChecks(_CheckBase):
    """agency_type enum + authorization_level 1..5 range."""

    def test_agency_type_enum_rejects_unknown(self):
        self._expect_check_violation(
            "INSERT INTO Agency (name, agency_type, jurisdiction, authorization_level) "
            "VALUES ('Test', 'INVALID', 'Nowhere', 3)",
            constraint_name='agency_type_check',
        )

    def test_agency_authorization_level_above_ceiling(self):
        self._expect_check_violation(
            "INSERT INTO Agency (name, agency_type, jurisdiction, authorization_level) "
            "VALUES ('Test', 'FEDERAL', 'Nowhere', 6)",
            constraint_name='authorization_level',
        )

    def test_agency_authorization_level_zero_rejected(self):
        self._expect_check_violation(
            "INSERT INTO Agency (name, agency_type, jurisdiction, authorization_level) "
            "VALUES ('Test', 'FEDERAL', 'Nowhere', 0)",
            constraint_name='authorization_level',
        )


# ============================================================================
# AgencyAlgorithmAuth
# ============================================================================

class TestAgencyAlgorithmAuthChecks(_CheckBase):
    """authorization_type enum: ISSUE / VERIFY / BOTH."""

    def test_authorization_type_enum(self):
        self._expect_check_violation(
            "INSERT INTO AgencyAlgorithmAuth (agency_id, algorithm_id, authorization_type) "
            "VALUES (1, 1, 'NEVER')",
            constraint_name='authorization_type_check',
        )


# ============================================================================
# AgencyTrustAttestation (R11-3 / M2-8)
# ============================================================================

class TestAgencyTrustAttestationChecks(_CheckBase):

    def test_no_self_attestation(self):
        self._expect_check_violation(
            "INSERT INTO AgencyTrustAttestation "
            "(attesting_agency_id, attested_agency_id, context_id, "
            "valid_until, signed_by) "
            "VALUES (1, 1, 1, CURRENT_DATE + interval '90 days', 1)",
            constraint_name='no_self_attestation',
        )

    def test_validity_floor_zero_duration_rejected(self):
        """valid_until > attested_date. Default attested_date is today."""
        self._expect_check_violation(
            "INSERT INTO AgencyTrustAttestation "
            "(attesting_agency_id, attested_agency_id, context_id, "
            "attested_date, valid_until, signed_by) "
            "VALUES (1, 2, 1, CURRENT_DATE, CURRENT_DATE, 1)",
            constraint_name='validity_floor',
        )

    def test_revocation_consistency_partial_revocation_rejected(self):
        """If revocation_date is set, revocation_reason must also be set
        (and >= 8 chars)."""
        self._expect_check_violation(
            "INSERT INTO AgencyTrustAttestation "
            "(attesting_agency_id, attested_agency_id, context_id, "
            "valid_until, signed_by, revocation_date) "
            "VALUES (1, 2, 1, CURRENT_DATE + interval '90 days', 1, CURRENT_DATE)",
            constraint_name='revocation_consistency',
        )

    def test_revocation_reason_too_short_rejected(self):
        """revocation_reason floor is 8 chars."""
        self._expect_check_violation(
            "INSERT INTO AgencyTrustAttestation "
            "(attesting_agency_id, attested_agency_id, context_id, "
            "valid_until, signed_by, revocation_date, revocation_reason) "
            "VALUES (1, 2, 1, CURRENT_DATE + interval '90 days', 1, "
            "CURRENT_DATE, 'short')",
            constraint_name='revocation_consistency',
        )


# ============================================================================
# AnchorBatch (R10-2 / M2-2)
# ============================================================================

class TestAnchorBatchChecks(_CheckBase):

    def test_batch_size_must_be_positive(self):
        self._expect_check_violation(
            "INSERT INTO AnchorBatch (algorithm_id, merkle_root, batch_size) "
            "VALUES (1, 'deadbeef', 0)",
            constraint_name='batch_size',
        )

    def test_external_chain_enum_rejects_unknown(self):
        self._expect_check_violation(
            "INSERT INTO AnchorBatch "
            "(algorithm_id, merkle_root, batch_size, external_chain) "
            "VALUES (1, 'deadbeef', 1, 'BITCOIN')",
            constraint_name='external_chain_check',
        )

    def test_chain_consistency_committed_requires_chain(self):
        """committed_to_chain=true requires external_chain IS NOT NULL."""
        self._expect_check_violation(
            "INSERT INTO AnchorBatch "
            "(algorithm_id, merkle_root, batch_size, committed_to_chain) "
            "VALUES (1, 'deadbeef', 1, true)",
            constraint_name='batch_chain_consistency',
        )

    def test_batch_root_must_be_hex(self):
        self._expect_check_violation(
            "INSERT INTO AnchorBatch (algorithm_id, merkle_root, batch_size) "
            "VALUES (1, 'NOT-HEX!', 1)",
            constraint_name='batch_root_is_hex',
        )


# ============================================================================
# AppUser (auth)
# ============================================================================

class TestAppUserChecks(_CheckBase):

    def test_role_enum(self):
        self._expect_check_violation(
            "INSERT INTO AppUser (username, password_hash, role) "
            "VALUES ('xtest', 'argon2id$dummy', 'godmode')",
            constraint_name='chk_appuser_role',
        )

    def test_username_format_lowercase_only(self):
        """chk_appuser_username_format: ^[a-z0-9._-]{3,50}$"""
        self._expect_check_violation(
            "INSERT INTO AppUser (username, password_hash, role) "
            "VALUES ('UPPER', 'argon2id$dummy', 'operator')",
            constraint_name='chk_appuser_username_format',
        )

    def test_username_too_short_rejected(self):
        self._expect_check_violation(
            "INSERT INTO AppUser (username, password_hash, role) "
            "VALUES ('xy', 'argon2id$dummy', 'operator')",
            constraint_name='chk_appuser_username_format',
        )

    def test_failed_count_nonneg(self):
        self._expect_check_violation(
            "INSERT INTO AppUser (username, password_hash, role, failed_login_count) "
            "VALUES ('xtest', 'argon2id$dummy', 'operator', -1)",
            constraint_name='chk_appuser_failed_count_nonneg',
        )


# ============================================================================
# AuthAuditLog
# ============================================================================

class TestAuthAuditLogChecks(_CheckBase):

    def test_event_type_enum(self):
        self._expect_check_violation(
            "INSERT INTO AuthAuditLog (event_type, username, ip_address) "
            "VALUES ('TIME_TRAVEL', 'admin', '127.0.0.1')",
            constraint_name='chk_authaudit_event_type',
        )


# ============================================================================
# BlockchainAnchor
# ============================================================================

class TestBlockchainAnchorChecks(_CheckBase):

    def test_status_enum(self):
        self._expect_check_violation(
            "INSERT INTO BlockchainAnchor "
            "(token_id, did, commitment_hash, ledger_network, status) "
            "VALUES (1, 'did:polaris:test', 'deadbeef', 'ALGORAND_PQ', 'INVALID')",
            constraint_name='blockchainanchor_status_check',
        )

    def test_ledger_network_enum(self):
        self._expect_check_violation(
            "INSERT INTO BlockchainAnchor "
            "(token_id, did, commitment_hash, ledger_network) "
            "VALUES (1, 'did:polaris:test', 'deadbeef', 'BITCOIN')",
            constraint_name='ledger_network_check',
        )

    def test_anchor_proof_with_batch_partial_is_rejected(self):
        """If batch_id is set, merkle_proof must also be set."""
        self._expect_check_violation(
            "INSERT INTO BlockchainAnchor "
            "(token_id, did, commitment_hash, ledger_network, batch_id) "
            "VALUES (1, 'did:polaris:test', 'hash', 'ALGORAND_PQ', 1)",
            constraint_name='anchor_proof_with_batch',
        )


# ============================================================================
# CryptographicAlgorithm
# ============================================================================

class TestCryptographicAlgorithmChecks(_CheckBase):

    def test_security_level_bits_floor(self):
        """80-bit floor; 64 must reject."""
        self._expect_check_violation(
            "INSERT INTO CryptographicAlgorithm "
            "(name, family, quantum_resistant, security_level_bits) "
            "VALUES ('weak-test', 'TEST', false, 64)",
            constraint_name='security_level_bits',
        )

    def test_security_level_bits_ceiling(self):
        self._expect_check_violation(
            "INSERT INTO CryptographicAlgorithm "
            "(name, family, quantum_resistant, security_level_bits) "
            "VALUES ('xstrong', 'TEST', true, 257)",
            constraint_name='security_level_bits',
        )


# ============================================================================
# DeviceBinding
# ============================================================================

class TestDeviceBindingChecks(_CheckBase):

    def test_device_type_enum(self):
        self._expect_check_violation(
            "INSERT INTO DeviceBinding "
            "(token_id, device_type, device_fingerprint, binding_method) "
            "VALUES (1, 'LAPTOP', 'fp', 'SECURE_ENCLAVE')",
            constraint_name='device_type_check',
        )

    def test_binding_method_enum(self):
        self._expect_check_violation(
            "INSERT INTO DeviceBinding "
            "(token_id, device_type, device_fingerprint, binding_method) "
            "VALUES (1, 'PHONE', 'fp', 'CUSTOM_METHOD')",
            constraint_name='binding_method_check',
        )


# ============================================================================
# EnrollmentStatusEvent (R11-4 / M2-9)
# ============================================================================

class TestEnrollmentStatusEventChecks(_CheckBase):

    def test_status_enum(self):
        self._expect_check_violation(
            "INSERT INTO EnrollmentStatusEvent "
            "(individual_id, status, transition_reason) "
            "VALUES (1, 'UNKNOWN', 'Test')",
            constraint_name='enrollmentstatusevent_status_check',
        )


# ============================================================================
# GenomicAnchor (R10-4 / M2-4)
# ============================================================================

class TestGenomicAnchorChecks(_CheckBase):

    # NOTE: GenomicAnchor.anchor_hash has multiple stacked constraints:
    #   genomic_anchor_refuses_plaintext: must contain at least one
    #     non-ACGT char (so it can't be a raw genomic sequence)
    #   genomic_hash_is_hex: must match /^[0-9a-fA-F]+$/
    #   genomic_hash_length_matches_algorithm: length must match algorithm
    # To exercise each in isolation we use 'f' as the fill character —
    # 'f' is hex but NOT in ACGT, so the plaintext-refusal CHECK is
    # already satisfied; subsequent CHECKs fire deterministically.

    def test_hash_must_be_hex(self):
        self._expect_check_violation(
            "INSERT INTO GenomicAnchor "
            "(token_id, hash_algorithm, anchor_hash, enrollment_date, witness_agency_id) "
            "VALUES (1, 'SHA3-256', 'fnot-hex!fnot-hex!fnot-hex!fnot-hex!fnot-hex!fnot-hex!fnot-hex!', CURRENT_DATE, 1)",
            constraint_name='genomic_hash_is_hex',
        )

    def test_hash_length_must_match_algorithm(self):
        """SHA3-256 → 64 hex chars. 60-char hex is rejected."""
        self._expect_check_violation(
            "INSERT INTO GenomicAnchor "
            "(token_id, hash_algorithm, anchor_hash, enrollment_date, witness_agency_id) "
            "VALUES (1, 'SHA3-256', '" + 'f' * 60 + "', CURRENT_DATE, 1)",
            constraint_name='genomic_hash_length_matches_algorithm',
        )

    def test_hash_algorithm_enum(self):
        """hash_algorithm must be in the enum.

        MD5 triggers both `genomicanchor_hash_algorithm_check` AND
        `genomic_hash_length_matches_algorithm` (the latter because
        no WHEN branch matches MD5). Either constraint firing means
        the bad value was rejected — accept either.
        """
        with self.assertRaises(pg_errors.CheckViolation):
            with self.conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO GenomicAnchor "
                    "(token_id, hash_algorithm, anchor_hash, enrollment_date, "
                    "witness_agency_id) "
                    "VALUES (1, 'MD5', '" + 'f' * 32 + "', CURRENT_DATE, 1)"
                )


# ============================================================================
# IdentityToken
# ============================================================================

class TestIdentityTokenChecks(_CheckBase):

    def test_status_enum(self):
        self._expect_check_violation(
            "INSERT INTO IdentityToken "
            "(individual_id, token_value, physical_serial, status, "
            "algorithm_id, issuing_agency_id, biometric_binding_type) "
            "VALUES (2, 'X-TEST-1', 'PSV-1', 'INVALID', 1, 1, 'FINGERPRINT')",
            constraint_name='identitytoken_status_check',
        )

    def test_biometric_binding_type_enum(self):
        self._expect_check_violation(
            "INSERT INTO IdentityToken "
            "(individual_id, token_value, physical_serial, status, "
            "algorithm_id, issuing_agency_id, biometric_binding_type) "
            "VALUES (2, 'X-TEST-2', 'PSV-2', 'RESERVE', 1, 1, 'DNA')",
            constraint_name='biometric_binding_type_check',
        )

    def test_liveness_check_type_enum(self):
        self._expect_check_violation(
            "INSERT INTO IdentityToken "
            "(individual_id, token_value, physical_serial, status, "
            "algorithm_id, issuing_agency_id, biometric_binding_type, "
            "liveness_check_type) "
            "VALUES (2, 'X-TEST-3', 'PSV-3', 'RESERVE', 1, 1, 'FINGERPRINT', 'NONE')",
            constraint_name='liveness_check_type_check',
        )

    def test_activation_sequence_must_be_positive(self):
        self._expect_check_violation(
            "INSERT INTO IdentityToken "
            "(individual_id, token_value, physical_serial, status, "
            "algorithm_id, issuing_agency_id, biometric_binding_type, "
            "activation_sequence) "
            "VALUES (2, 'X-TEST-4', 'PSV-4', 'RESERVE', 1, 1, 'FINGERPRINT', 0)",
            constraint_name='activation_sequence_check',
        )

    def test_duress_hash_well_formed(self):
        """duress_code_hash, when present, must be >= 20 chars."""
        self._expect_check_violation(
            "INSERT INTO IdentityToken "
            "(individual_id, token_value, physical_serial, status, "
            "algorithm_id, issuing_agency_id, biometric_binding_type, "
            "duress_code_hash) "
            "VALUES (2, 'X-TEST-5', 'PSV-5', 'RESERVE', 1, 1, 'FINGERPRINT', 'short')",
            constraint_name='chk_duress_hash_well_formed',
        )

    def test_token_time_order_activated_before_issued_rejected(self):
        """chk_token_time_order: activated_date >= issued_date."""
        self._expect_check_violation(
            "INSERT INTO IdentityToken "
            "(individual_id, token_value, physical_serial, status, "
            "algorithm_id, issuing_agency_id, biometric_binding_type, "
            "issued_date, activated_date) "
            "VALUES (2, 'X-TEST-6', 'PSV-6', 'ACTIVE', 1, 1, 'FINGERPRINT', "
            "'2026-05-14 12:00:00', '2026-05-13 12:00:00')",
            constraint_name='chk_token_time_order',
        )


# ============================================================================
# IssuerDiscretionPolicy (R11-6 / M2-11)
# ============================================================================

class TestIssuerDiscretionPolicyChecks(_CheckBase):

    def test_window_days_floor(self):
        self._expect_check_violation(
            "INSERT INTO IssuerDiscretionPolicy "
            "(agency_id, max_revoke_percent, window_days, set_by_admin, justification) "
            "VALUES (1, 5.0, 0, 1, 'A reasonable justification for the policy')",
            constraint_name='window_days_check',
        )

    def test_window_days_ceiling(self):
        self._expect_check_violation(
            "INSERT INTO IssuerDiscretionPolicy "
            "(agency_id, max_revoke_percent, window_days, set_by_admin, justification) "
            "VALUES (1, 5.0, 366, 1, 'A reasonable justification for the policy')",
            constraint_name='window_days_check',
        )

    def test_max_revoke_percent_zero_rejected(self):
        self._expect_check_violation(
            "INSERT INTO IssuerDiscretionPolicy "
            "(agency_id, max_revoke_percent, window_days, set_by_admin, justification) "
            "VALUES (1, 0.0, 30, 1, 'A reasonable justification for the policy')",
            constraint_name='max_revoke_percent',
        )

    def test_justification_minimum_length(self):
        """justification must be >= 20 chars."""
        self._expect_check_violation(
            "INSERT INTO IssuerDiscretionPolicy "
            "(agency_id, max_revoke_percent, window_days, set_by_admin, justification) "
            "VALUES (1, 5.0, 30, 1, 'too short')",
            constraint_name='justification_check',
        )


# ============================================================================
# RecoveryRequest (R11-2 / M2-7)
# ============================================================================

class TestRecoveryRequestChecks(_CheckBase):

    def test_cooldown_window_minimum(self):
        """48-hour cooldown floor."""
        self._expect_check_violation(
            "INSERT INTO RecoveryRequest "
            "(claimed_individual_id, requesting_agency_id, requesting_user_id, "
            "requested_at, cooldown_expires_at) "
            "VALUES (1, 1, 1, '2026-05-14 12:00:00', '2026-05-15 12:00:00')",
            constraint_name='cooldown_window_minimum',
        )

    def test_status_enum(self):
        self._expect_check_violation(
            "INSERT INTO RecoveryRequest "
            "(claimed_individual_id, requesting_agency_id, requesting_user_id, "
            "requested_at, cooldown_expires_at, status) "
            "VALUES (1, 1, 1, '2026-05-14 12:00:00', '2026-05-17 12:00:00', 'INVALID')",
            constraint_name='recoveryrequest_status_check',
        )

    def test_approver_differs_from_requester(self):
        self._expect_check_violation(
            "INSERT INTO RecoveryRequest "
            "(claimed_individual_id, requesting_agency_id, requesting_user_id, "
            "requested_at, cooldown_expires_at, decided_by_user_id) "
            "VALUES (1, 1, 1, '2026-05-14 12:00:00', '2026-05-17 12:00:00', 1)",
            constraint_name='approver_differs_from_requester',
        )


# ============================================================================
# RevocationList
# ============================================================================

class TestRevocationListChecks(_CheckBase):
    """RevocationList's `reason_code_check` enum is layered behind
    multiple safety triggers:

      * `enforce_revocation_status` (token must be REVOKED/LOST/EXPIRED
        before an entry can be added)
      * `enforce_revocation_velocity_bound` (direct UPDATE to
        ``status='REVOKED'`` is forbidden; must go through
        ``uc8_revoke_token()``)

    Exercising the reason_code CHECK in isolation requires bypassing
    these safety layers, which contradicts the defensive design they
    embody. The CHECK is structurally present in the schema (verified
    via the pg_constraint catalog ); the operational path through
    ``uc8_revoke_token`` is exercised by the existing UC test suite
    (see test_app.py). Leaving this class as a documentation anchor
    for the constraint without an isolated unit test.
    """

    def test_constraint_documented(self):
        """Documentation-only: the reason_code_check exists in the
        live schema and is exercised via the safety-trigger-protected
        operational path."""
        with self.conn.cursor() as cur:
            cur.execute("""
                SELECT con.conname
                FROM pg_constraint con
                JOIN pg_class cl ON con.conrelid = cl.oid
                WHERE cl.relname = 'revocationlist'
                  AND con.contype = 'c'
                  AND con.conname = 'revocationlist_reason_code_check'
            """)
            row = cur.fetchone()
            self.assertIsNotNone(row,
                "revocationlist_reason_code_check must exist in pg_constraint.")


# ============================================================================
# TokenLifecycleEvent
# ============================================================================

class TestTokenLifecycleEventChecks(_CheckBase):

    def test_event_type_enum(self):
        self._expect_check_violation(
            "INSERT INTO TokenLifecycleEvent (token_id, event_type) "
            "VALUES (1, 'DISAPPEARED')",
            constraint_name='event_type_check',
        )

    def test_latitude_above_ceiling(self):
        self._expect_check_violation(
            "INSERT INTO TokenLifecycleEvent "
            "(token_id, event_type, latitude, longitude) "
            "VALUES (1, 'ISSUED', 91.0, 0.0)",
            constraint_name='latitude_check',
        )

    def test_longitude_above_ceiling(self):
        self._expect_check_violation(
            "INSERT INTO TokenLifecycleEvent "
            "(token_id, event_type, latitude, longitude) "
            "VALUES (1, 'ISSUED', 0.0, 181.0)",
            constraint_name='longitude_check',
        )

    def test_latitude_below_floor(self):
        self._expect_check_violation(
            "INSERT INTO TokenLifecycleEvent "
            "(token_id, event_type, latitude, longitude) "
            "VALUES (1, 'ISSUED', -90.5, 0.0)",
            constraint_name='latitude_check',
        )


# ============================================================================
# TokenPermission
# ============================================================================

class TestTokenPermissionChecks(_CheckBase):

    def test_permission_level_enum(self):
        self._expect_check_violation(
            "INSERT INTO TokenPermission "
            "(token_id, context_id, permission_level) "
            "VALUES (1, 1, 'ROOT')",
            constraint_name='permission_level_check',
        )


# ============================================================================
# TokenSignature (R11-1 / M2-6)
# ============================================================================

class TestTokenSignatureChecks(_CheckBase):

    def test_deprecation_after_signed(self):
        """deprecation_date, if set, must be strictly after signed_at."""
        self._expect_check_violation(
            "INSERT INTO TokenSignature "
            "(token_id, algorithm_id, signature_bytes, signed_at, deprecation_date) "
            "VALUES (1, 1, decode('deadbeef', 'hex'), "
            "'2026-05-14 12:00:00', '2026-05-14 11:00:00')",
            constraint_name='deprecation_after_signed',
        )


# ============================================================================
# TokenStateEpoch + Leaves (R10-1 / M2-1)
# ============================================================================

class TestTokenStateEpochChecks(_CheckBase):

    def test_root_must_be_hex(self):
        self._expect_check_violation(
            "INSERT INTO TokenStateEpoch "
            "(merkle_root, valid_until, committed_count, closed_by_user_id) "
            "VALUES ('not-hex!', now() + interval '1 day', 1, 1)",
            constraint_name='epoch_root_is_hex',
        )

    def test_committed_count_cap(self):
        """committed_count cap is 10000."""
        self._expect_check_violation(
            "INSERT INTO TokenStateEpoch "
            "(merkle_root, valid_until, committed_count, closed_by_user_id) "
            "VALUES ('deadbeef', now() + interval '1 day', 10001, 1)",
            constraint_name='committed_count_cap',
        )

    def test_committed_count_must_be_positive(self):
        self._expect_check_violation(
            "INSERT INTO TokenStateEpoch "
            "(merkle_root, valid_until, committed_count, closed_by_user_id) "
            "VALUES ('deadbeef', now() + interval '1 day', 0, 1)",
            constraint_name='committed_count_check',
        )

    def test_validity_floor(self):
        """valid_until must exceed valid_from."""
        self._expect_check_violation(
            "INSERT INTO TokenStateEpoch "
            "(merkle_root, valid_from, valid_until, committed_count, closed_by_user_id) "
            "VALUES ('deadbeef', '2026-05-14 12:00:00', '2026-05-14 11:00:00', 1, 1)",
            constraint_name='epoch_validity_floor',
        )


# ============================================================================
# VerificationContext
# ============================================================================

class TestVerificationContextChecks(_CheckBase):

    def test_context_type_enum(self):
        self._expect_check_violation(
            "INSERT INTO VerificationContext "
            "(context_type, min_security_level) "
            "VALUES ('GAMBLING', 192)",
            constraint_name='context_type_check',
        )

    def test_min_security_level_floor(self):
        """128-bit floor for verification contexts."""
        self._expect_check_violation(
            "INSERT INTO VerificationContext "
            "(context_type, min_security_level) "
            "VALUES ('HEALTHCARE', 80)",
            constraint_name='min_security_level_check',
        )


# ============================================================================
# VerificationEvent — THE most-important checks: C2 enforcement
# ============================================================================

class TestVerificationEventChecks(_CheckBase):
    """The verification-event CHECKs include ``chk_disclosure_token_consistency``
    — the column-level half of C2 (ZK → token_id IS NULL). This is the
    most-important CHECK in the schema for the project's privacy claim."""

    def test_disclosure_level_enum(self):
        """The disclosure_level column-level enum CHECK fires on any
        value outside {ZERO_KNOWLEDGE, SELECTIVE, FULL}.

        Note: a non-enum value also fails ``chk_disclosure_token_consistency``
        (the multi-column CHECK) because no token_id/disclosure_level
        pair matches the consistency rule. PostgreSQL's CHECK evaluation
        order is implementation-defined; we accept either constraint
        firing.
        """
        # Try with token_id NULL so chk_disclosure_token_consistency
        # is satisfied only in the ZK case; PUBLIC isn't ZK, so the
        # consistency CHECK still fires but the enum CHECK is the
        # natural target. Either constraint firing means the bad
        # value was rejected — verify CheckViolation without binding
        # to a specific name.
        with self.assertRaises(pg_errors.CheckViolation):
            with self.conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO VerificationEvent "
                    "(token_id, requesting_agency_id, context_id, outcome, "
                    "disclosure_level) "
                    "VALUES (NULL, 1, 1, 'SUCCESS', 'PUBLIC')"
                )

    def test_C2_zk_with_nonnull_token_id_rejected(self):
        """chk_disclosure_token_consistency — C2 enforcement at column level.

        ZERO_KNOWLEDGE events MUST have token_id IS NULL. This is the
        privacy invariant; if it lapses, the verification graph becomes
        reconstructable from ZK events alone.
        """
        self._expect_check_violation(
            "INSERT INTO VerificationEvent "
            "(token_id, requesting_agency_id, context_id, outcome, disclosure_level) "
            "VALUES (1, 1, 1, 'SUCCESS', 'ZERO_KNOWLEDGE')",
            constraint_name='chk_disclosure_token_consistency',
        )

    def test_C2_full_with_null_token_id_rejected(self):
        """FULL events MUST have token_id IS NOT NULL — the other half
        of chk_disclosure_token_consistency."""
        self._expect_check_violation(
            "INSERT INTO VerificationEvent "
            "(token_id, requesting_agency_id, context_id, outcome, disclosure_level) "
            "VALUES (NULL, 1, 1, 'SUCCESS', 'FULL')",
            constraint_name='chk_disclosure_token_consistency',
        )

    def test_latitude_above_ceiling(self):
        self._expect_check_violation(
            "INSERT INTO VerificationEvent "
            "(token_id, requesting_agency_id, context_id, outcome, "
            "disclosure_level, latitude, longitude) "
            "VALUES (1, 1, 1, 'SUCCESS', 'FULL', 91.0, 0.0)",
            constraint_name='latitude_check',
        )


# ============================================================================
# DuressEvent (R11-5 / M2-10)
# ============================================================================

class TestDuressEventChecks(_CheckBase):

    def test_oob_channel_enum(self):
        self._expect_check_violation(
            "INSERT INTO DuressEvent "
            "(token_id, context_id, requesting_agency_id, oob_channel) "
            "VALUES (1, 1, 1, 'TELEGRAM')",
            constraint_name='oob_channel_check',
        )


# ============================================================================
# QuantumObserverBinding (M2-5 — scaffold)
# ============================================================================

class TestQuantumObserverBindingChecks(_CheckBase):

    def test_binding_status_enum(self):
        self._expect_check_violation(
            "INSERT INTO QuantumObserverBinding "
            "(token_id, registered_agency_id, binding_status) "
            "VALUES (1, 1, 'QUANTUM_LOL')",
            constraint_name='binding_status_check',
        )

    def test_scaffold_must_defer_functional_fields(self):
        """SCAFFOLD rows MUST have observer_protocol IS NULL."""
        self._expect_check_violation(
            "INSERT INTO QuantumObserverBinding "
            "(token_id, registered_agency_id, binding_status, observer_protocol) "
            "VALUES (1, 1, 'SCAFFOLD', 'BB84')",
            constraint_name='qob_scaffold_defers_functional',
        )

    def test_operational_requires_functional_fields(self):
        """OPERATIONAL rows MUST have observer_protocol IS NOT NULL."""
        self._expect_check_violation(
            "INSERT INTO QuantumObserverBinding "
            "(token_id, registered_agency_id, binding_status) "
            "VALUES (1, 1, 'OPERATIONAL')",
            constraint_name='qob_operational_requires_functional',
        )


# ============================================================================
# uc4_activate_reserve x velocity-bound trigger (procedure regression)
# ============================================================================

class TestUC4ReserveActivation(_CheckBase):
    """uc4_activate_reserve must succeed for every reason code it offers.

    COMPROMISED / SUPERSEDED / ADMINISTRATIVE map the lost token to terminal
    status REVOKED, which trips enforce_revocation_velocity_bound() unless the
    procedure opts out of the bound (the way uc8_revoke_token does). Until uc4
    set polaris.revoke_check_done on its REVOKED branch, three of the five
    reason codes the UI offers aborted the whole procedure with
    'Direct UPDATE to status=REVOKED is not allowed'. LOST / STOLEN map to
    terminal LOST and never tripped the trigger, which is why nothing caught it.
    Each test runs inside the per-test transaction and rolls back.
    """

    def _run_uc4(self, reason_code):
        """Stage an ACTIVE holder + a fresh RESERVE for them, run uc4 with
        ``reason_code``, and return (promoted_token_id, reserve_token_id,
        lost_token_status). Propagates any procedure exception."""
        with self.conn.cursor() as cur:
            cur.execute(
                "SELECT individual_id, token_id FROM IdentityToken "
                "WHERE status = 'ACTIVE' LIMIT 1")
            row = cur.fetchone()
            self.assertIsNotNone(
                row, "sample data has no ACTIVE token to test uc4 against")
            individual_id, active_token = row['individual_id'], row['token_id']

            cur.execute(
                "INSERT INTO IdentityToken "
                "(token_value, physical_serial, biometric_binding_type, "
                " individual_id, issuing_agency_id, algorithm_id, status) "
                "VALUES (%s, %s, 'FINGERPRINT', %s, 3, 1, 'RESERVE') "
                "RETURNING token_id",
                (f'UC4TEST-{reason_code}-{active_token}',
                 f'UC4SER-{reason_code}-{active_token}', individual_id))
            reserve_token = cur.fetchone()['token_id']

            cur.execute(
                "SELECT uc4_activate_reserve(%s, 3, %s, %s, %s) AS promoted",
                (active_token, reason_code, reserve_token,
                 f'https://crl.idtoken.gov/test/{reason_code}.crl'))
            promoted = cur.fetchone()['promoted']

            cur.execute(
                "SELECT status FROM IdentityToken WHERE token_id = %s",
                (active_token,))
            lost_status = cur.fetchone()['status']
            return promoted, reserve_token, lost_status

    def test_lost_positive_control(self):
        promoted, reserve, lost_status = self._run_uc4('LOST')
        self.assertEqual(promoted, reserve)
        self.assertEqual(lost_status, 'LOST')

    def test_compromised_maps_to_revoked_and_succeeds(self):
        promoted, reserve, lost_status = self._run_uc4('COMPROMISED')
        self.assertEqual(promoted, reserve)
        self.assertEqual(lost_status, 'REVOKED')

    def test_superseded_maps_to_revoked_and_succeeds(self):
        promoted, reserve, lost_status = self._run_uc4('SUPERSEDED')
        self.assertEqual(promoted, reserve)
        self.assertEqual(lost_status, 'REVOKED')

    def test_administrative_maps_to_revoked_and_succeeds(self):
        promoted, reserve, lost_status = self._run_uc4('ADMINISTRATIVE')
        self.assertEqual(promoted, reserve)
        self.assertEqual(lost_status, 'REVOKED')


class TestUC1Issuance(_CheckBase):
    """uc1_issue_and_activate must refuse to mint a token under a DEPRECATED
    algorithm — uc6_migrate_algorithm already refuses to migrate a token TO a
    deprecated algorithm, and uc1 must not create one under it either (a live
    token signed with a retired/weakened algorithm). Runs in the per-test
    transaction and rolls back (the deprecation UPDATE is discarded)."""

    def test_uc1_refuses_deprecated_algorithm(self):
        with self.conn.cursor() as cur:
            cur.execute(
                "SELECT algorithm_id FROM AgencyAlgorithmAuth "
                "WHERE agency_id = 1 AND authorization_type IN ('ISSUE','BOTH') LIMIT 1")
            alg = cur.fetchone()['algorithm_id']
            cur.execute(
                "UPDATE CryptographicAlgorithm "
                "SET deprecation_date = CURRENT_TIMESTAMP - INTERVAL '1 day' "
                "WHERE algorithm_id = %s", (alg,))
            with self.assertRaises(pg_errors.InvalidParameterValue):
                cur.execute(
                    "SELECT uc1_issue_and_activate('Dep Test','1990-01-01','US-CA',1,%s,"
                    "'FINGERPRINT',1,'MULTI_MODAL','TKN-DEPTEST','SN-DEPTEST',NULL,"
                    "ARRAY[1])", (alg,))

    def test_uc1_succeeds_under_a_live_algorithm(self):
        # Control: a non-deprecated algorithm issues normally.
        with self.conn.cursor() as cur:
            cur.execute(
                "SELECT a.algorithm_id FROM AgencyAlgorithmAuth a "
                "JOIN CryptographicAlgorithm c ON c.algorithm_id = a.algorithm_id "
                "WHERE a.agency_id = 1 AND a.authorization_type IN ('ISSUE','BOTH') "
                "  AND (c.deprecation_date IS NULL OR c.deprecation_date > CURRENT_TIMESTAMP) "
                "LIMIT 1")
            alg = cur.fetchone()['algorithm_id']
            cur.execute(
                "SELECT uc1_issue_and_activate('Live Test','1990-01-01','US-CA',1,%s,"
                "'FINGERPRINT',1,'MULTI_MODAL','TKN-LIVETEST','SN-LIVETEST',NULL,"
                "ARRAY[1]) AS token_id", (alg,))
            self.assertIsNotNone(cur.fetchone()['token_id'])


class TestC1PrivilegeBoundary(unittest.TestCase):
    """C1 append-only is a PRIVILEGE boundary, not only a trigger.

    The reject_audit_modification trigger has a carve-out: it permits
    UPDATE/DELETE when the custom GUC polaris.purge_in_progress = 'TRUE'. Any
    role can SET a custom GUC, so the trigger alone did NOT stop the
    application role from deleting an audit row — it could set the GUC and
    delete. v9.85 revokes UPDATE/DELETE on every append-only table from
    polaris_app (keeping SELECT + INSERT), so the carve-out is unreachable from
    the app role; the one legitimate DELETE path, uc_archive_purge, is
    SECURITY DEFINER and runs the purge with the owner's rights.

    These tests open an EXPLICIT polaris_app connection so the boundary is
    exercised even when the suite itself connects as a superuser (locally the
    suite runs as `vanta`, which bypasses the ACL; in CI it is already
    polaris_app). They skip cleanly if the polaris_app role is unreachable.
    """

    APPEND_ONLY_TABLES = (
        "TokenLifecycleEvent", "VerificationEvent", "EnrollmentStatusEvent",
        "AnchorBatch", "TokenStateEpochLeaf", "DuressEvent", "AuthAuditLog",
        "AuditAccessLog",
    )

    def _app_conn(self):
        """A connection authenticated as the application role polaris_app.

        Skips the test if that role cannot be reached (e.g. a deployment that
        renamed it or set a non-default password without exporting it)."""
        cfg = dict(DB_CONFIG)
        cfg["user"] = "polaris_app"
        cfg["password"] = os.environ.get(
            "POLARIS_APP_TEST_PASSWORD",
            DB_CONFIG.get("password") or "polaris_dev_password")
        try:
            conn = psycopg2.connect(cursor_factory=RealDictCursor, **cfg)
        except psycopg2.OperationalError as exc:
            self.skipTest(f"polaris_app role unreachable: {exc}")
        self.addCleanup(conn.close)
        return conn

    def test_app_role_cannot_delete_audit_even_with_purge_guc(self):
        conn = self._app_conn()
        with conn.cursor() as cur:
            # Reproduce the original bypass: set the carve-out GUC, then delete.
            cur.execute("SET LOCAL polaris.purge_in_progress = 'TRUE'")
            with self.assertRaises(pg_errors.InsufficientPrivilege):
                cur.execute(
                    "DELETE FROM TokenLifecycleEvent "
                    "WHERE event_id = (SELECT min(event_id) FROM TokenLifecycleEvent)")
        conn.rollback()

    def test_app_role_cannot_update_or_delete_any_append_only_table(self):
        conn = self._app_conn()
        for tbl in self.APPEND_ONLY_TABLES:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT has_table_privilege('polaris_app', %s, 'UPDATE') AS upd, "
                    "       has_table_privilege('polaris_app', %s, 'DELETE') AS del, "
                    "       has_table_privilege('polaris_app', %s, 'INSERT') AS ins",
                    (tbl, tbl, tbl))
                row = cur.fetchone()
            self.assertFalse(row["upd"], f"polaris_app must not hold UPDATE on {tbl}")
            self.assertFalse(row["del"], f"polaris_app must not hold DELETE on {tbl}")
            self.assertTrue(row["ins"], f"append-only is insert-allowed: polaris_app needs INSERT on {tbl}")
            conn.rollback()

    def test_app_role_can_still_append_audit_rows(self):
        conn = self._app_conn()
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO TokenLifecycleEvent (token_id, event_type, event_timestamp, reason_code) "
                "VALUES (1, 'ISSUED', now(), 'BOUNDARY_TEST') RETURNING event_id")
            self.assertIsNotNone(cur.fetchone()["event_id"],
                                 "append-only must still permit INSERT by polaris_app")
        conn.rollback()

    def test_archive_purge_still_deletes_via_security_definer(self):
        """The legitimate purge path still works for polaris_app: uc_archive_purge
        is SECURITY DEFINER, so it deletes with the owner's rights despite the
        REVOKE. The whole exercise rolls back."""
        conn = self._app_conn()
        with conn.cursor() as cur:
            cur.execute("SELECT user_id FROM AppUser WHERE role = 'admin' LIMIT 1")
            admin = cur.fetchone()
            if admin is None:
                self.skipTest("no admin user to authorize the purge")
            admin_id = admin["user_id"]
            cur.execute(
                "INSERT INTO TokenLifecycleEvent (token_id, event_type, event_timestamp, reason_code) "
                "VALUES (1, 'ISSUED', now() - INTERVAL '400 days', 'PURGE_DEFINER_TEST')")
            cutoff = "now() - INTERVAL '365 days'"
            cur.execute(
                f"SELECT count(*) AS n FROM TokenLifecycleEvent WHERE event_timestamp < {cutoff}")
            before = cur.fetchone()["n"]
            self.assertGreaterEqual(before, 1)
            cur.execute(
                "CALL uc_archive_purge((now() - INTERVAL '365 days')::timestamptz, "
                "%s, %s, %s, NULL)",
                ("s3://polaris-archive/definer-test.tar.zst", "a" * 64, admin_id))
            cur.execute(
                f"SELECT count(*) AS n FROM TokenLifecycleEvent WHERE event_timestamp < {cutoff}")
            after = cur.fetchone()["n"]
            self.assertEqual(after, 0,
                             "uc_archive_purge (SECURITY DEFINER) must still purge old audit rows")
        conn.rollback()


if __name__ == '__main__':
    unittest.main(verbosity=2)
