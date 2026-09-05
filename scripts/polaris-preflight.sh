#!/usr/bin/env bash
# ============================================================================
# scripts/polaris-preflight.sh — the pre-ship gate a contributor runs before
# committing.
#
# Two things, both fast and both offline: the C1-C10 invariant layer
# (`python3 -m polaris_checks.run`) and the cross-reference check. It then
# reminds you to run the database-backed suites, which need Postgres and so
# cannot run here.
#
#   bash scripts/polaris-preflight.sh            # run the gate
#   bash scripts/polaris-preflight.sh --strict   # exit non-zero on any failure
# ============================================================================

set -uo pipefail

HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"
ROOT="$(cd -- "${HERE}/.." &> /dev/null && pwd)"
STRICT=0; [ "${1:-}" = "--strict" ] && STRICT=1

fails=0
echo "═══ polaris-preflight — pre-ship gate ═══"
echo

# 1. polaris-checks — the C1-C10 invariant layer.
if python3 -m polaris_checks.run > /tmp/_polaris_checks.out 2>&1; then
  echo "  ✓ polaris-checks: all C1-C10 invariants pass"
else
  echo "  ✗ polaris-checks: failures —"
  grep '✗' /tmp/_polaris_checks.out | sed 's/^/    /'
  fails=$((fails+1))
fi

# 2. Cross-reference integrity.
if bash "${HERE}/polaris-link-check.sh" --ci > /tmp/_polaris_links.out 2>&1; then
  echo "  ✓ polaris-link-check: all references resolve"
else
  echo "  ! polaris-link-check: $(tail -1 /tmp/_polaris_links.out)"
  fails=$((fails+1))
fi

# 3. Reminder for the DB-backed product suites (need Postgres + the venv).
echo "  · DB suites: confirm via 'scripts/polaris-test.sh' (test_app,"
echo "    test_check_constraints, test_invariants_property, test_redaction_property);"
echo "    test_cli runs from polaris_cli/ and rides along in CI via polaris-coverage.sh"

echo
if [ "$fails" -eq 0 ]; then
  echo "── READY ──"
  exit 0
fi
echo "── ${fails} gate failure(s) ──"
[ "$STRICT" -eq 1 ] && exit 1
exit 0
