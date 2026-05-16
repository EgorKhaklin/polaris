"""Fixture: CHANGELOG drifts from POLARIS_VERSION.

Bumps __version__.py to a value not present in CHANGELOG.md.
Expected outcome: ant_unbumped_version fires (its predicate is
exactly "POLARIS_VERSION matches the most-recent ## v entry in
CHANGELOG"). ant_changelog_gap may also fire (recent version with
no entry).
"""

FIXTURE = {
    "name": "changelog-version-drift",
    "description": (
        "__version__.py bumped to a synthetic v99.99 value that "
        "doesn't exist in CHANGELOG.md. Predicate-falsifying state "
        "for ant_unbumped_version."
    ),
    "setup": [
        # No SQL; this fixture is filesystem-level.
        # The validator handles file-level fixtures via a 'fs_setup' key.
    ],
    "fs_setup": {
        "polaris_web/__version__.py": (
            'POLARIS_VERSION = "99.99"\n__version__ = "99.99"\n'
        ),
    },
    "teardown": [],
    "fs_restore": ["polaris_web/__version__.py"],  # validator restores from git
    "expected_firing_ants": [
        "ant_unbumped_version",
        "ant_changelog_gap",
    ],
    "expected_silent_ants": [
        "ant_csp_health",
        "ant_aor_immutability",
        "ant_atlas_endpoint_health",
    ],
    "test_type": "recall",
}
