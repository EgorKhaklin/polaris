"""Fixture: C3 (one identity per person) violated at schema layer.

Setup creates two ACTIVE tokens for the same individual by
DROPPING the partial unique index first. This is a deliberately
broken schema state. The expected outcome is that ant_aor_immutability
fires (schema invariant broken) and ant_self_model_accuracy fires
(HYDRA's view of the system diverges from the now-broken schema).
"""

FIXTURE = {
    "name": "schema-c3-violated",
    "description": (
        "Partial unique index uq_one_active_token_per_individual "
        "dropped; two ACTIVE tokens created for individual_id=1. "
        "Schema invariant broken; expected firing ants surface "
        "this within one colony cycle."
    ),
    "setup": [
        "DROP INDEX IF EXISTS uq_one_active_token_per_individual",
        # Now insert a second ACTIVE token (assumes individual_id=1 has one)
        "INSERT INTO IdentityToken (individual_id, issuing_agency_id, "
        "    status, issued_at, expires_at, algorithm_id, token_value) "
        "SELECT individual_id, issuing_agency_id, 'ACTIVE', NOW(), "
        "       NOW() + INTERVAL '1 year', algorithm_id, "
        "       'fixture-c3-violation-' || NOW()::text "
        "  FROM IdentityToken "
        " WHERE status='ACTIVE' "
        " ORDER BY token_id LIMIT 1",
    ],
    "teardown": [
        "DELETE FROM IdentityToken WHERE token_value LIKE 'fixture-c3-violation-%'",
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_one_active_token_per_individual "
        "  ON IdentityToken (individual_id) WHERE status = 'ACTIVE'",
    ],
    "expected_firing_ants": [
        "ant_aor_immutability",      # the schema invariant
        "ant_self_model_accuracy",   # HYDRA's view diverges from actual
        "ant_fk_cascade_guard",      # may surface index change
    ],
    "expected_silent_ants": [
        "ant_csp_health",            # unrelated to schema
        "ant_changelog_gap",         # unrelated
        "ant_docs_structure",        # unrelated
    ],
    "test_type": "recall",  # this fixture tests recall (real-positive must fire)
}
