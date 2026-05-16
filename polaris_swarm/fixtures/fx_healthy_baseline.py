"""Fixture: healthy baseline.

The system is in a known-good state — no DB tampering, schema
intact, version pinned, CHANGELOG matches. The expected outcome is
that ZERO ALERT-level findings fire. Any ant that fires here is
producing a false positive.
"""

FIXTURE = {
    "name": "healthy-baseline",
    "description": (
        "System is in known-good state: schema loaded clean, "
        "version pinned, CHANGELOG header matches POLARIS_VERSION, "
        "no debug markers, all referenced files exist. "
        "Zero ALERT-level findings expected."
    ),
    "setup": [],  # no-op; healthy state is the live repo
    "teardown": [],
    "expected_firing_ants": [],  # no ants should fire ALERT on healthy state
    "expected_silent_ants": [
        # All 33 commander ants should be silent (or emit only INFO/DRIFT).
        # This is the precision test: if any ant fires ALERT here it's a FP.
    ],
    "test_type": "precision",  # this fixture tests precision (no false positives)
}
