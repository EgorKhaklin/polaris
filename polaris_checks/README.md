# polaris_checks/: the invariant layer

**Reader:** a contributor about to change the schema, the application or a
runbook, and a reviewer asking what stops a guarantee from quietly becoming
false. **Job:** hold every machine-checkable claim this repository makes, as a
plain function that reads the tree and returns a pass or a failure.

```bash
python3 -m polaris_checks.run        # every check, no database needed
```

It gates CI on every push, runs in pre-commit, and is the first half of
`scripts/polaris-preflight.sh`. A failure prints the check name, what it
expected and where, and blocks the ship.

## What a check is

A `check_*(repo_root) -> list[Finding]` function in `checks.py`, registered in
the `CHECKS` list. It reads files: SQL, Python, templates, workflows,
Dockerfiles, Markdown. It never connects to a database and never starts the
application, so it runs in about a second and cannot flake.

Every check is paired with a detection test in `test_checks.py` that builds a
broken fixture in a temporary directory and asserts the check fails on it. A
check that cannot demonstrate its own failure is treated as broken, because a
check that always passes is indistinguishable from no check at all.

## The constitution, and what enforces it here

The ten constraints live in [MISSION.md](../MISSION.md); the database is where
they are enforced. These checks assert that the enforcement is still present.

| Constraint | Check |
|---|---|
| C1 append-only audit | `check_aor_append_only_triggers`, `check_aor_privilege_boundary` |
| C2 zero-knowledge stores no token | `check_c2_zk_token_null` |
| C3 one active token per person | `check_one_active_token_index` |
| C4 atomic failed-login counter | `check_c4_atomic_failed_login` |
| C5 no inline scripts | `check_csp_forbids_unsafe_inline` |
| C6 server-side disclosure | `check_c6_atlas_redacts_zk_location` |
| C7 cryptography is data | `check_crypto_algorithm_is_data` |
| C8 bounded result sets | `check_c8_atlas_caps` |
| C9 real concurrency tests | `check_c9_concurrency_threading` |
| C10 identity is not money | `check_c10_no_money_tables` |

The other checks cover production posture rather than the constitution: the
container and compose hardening, the backup and restore path, the alert rules
and their runbooks, the observability surfaces, the release and SBOM flow, the
documentation counts, and the presentation surface. `check_c1c10_objects_resolve`
closes the loop the other way, asserting that every SQL object name a document
cites as an enforcement point actually exists.

## Adding one

1. Write `check_<subject>(root)` in `checks.py`, returning `_ok(name, message)`
   or `_fail(name, message)`. The message is read by someone who did not write
   the check: name the file, the expectation and the reason.
2. Register it in `CHECKS`.
3. Write its detection test in `test_checks.py`: a fixture that passes, then
   one broken in each way that matters, asserting `FAIL` on each.
4. Run `python3 -m polaris_checks.run` and `pytest polaris_checks/test_checks.py`.
5. The count of checks is stated in several documents and recomputed by
   `check_stated_counts`, which will tell you which ones to restamp.

## Files

| File | What it holds |
|---|---|
| `checks.py` | Every check, and the `CHECKS` registry |
| `run.py` | The runner: `python3 -m polaris_checks.run`, exit 1 on any failure |
| `test_checks.py` | One detection test per check |
