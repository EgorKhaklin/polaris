#!/usr/bin/env bash
# ============================================================================
# ai-done — pre-ship gate.
#
# v9.55: the cognitive apparatus (the findings-gate, the swarm scorecard,
# the meta and coherence checks, the CM gate) was removed and replaced by
# polaris_checks.
# The gate is now thin and honest: run the flat C1-C10 check layer + the link
# checker, and remind to run the DB-backed product suites (which need Postgres).
#
#   bash scripts/ai-done.sh            # run the gate
#   bash scripts/ai-done.sh --strict   # exit non-zero on any failure
# ============================================================================

set -uo pipefail

HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"
ROOT="$(cd -- "${HERE}/.." &> /dev/null && pwd)"
STRICT=0; [ "${1:-}" = "--strict" ] && STRICT=1

fails=0
echo "═══ ai-done — pre-ship gate ═══"
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
if bash "${HERE}/ai-link-check.sh" --ci > /tmp/_polaris_links.out 2>&1; then
  echo "  ✓ ai-link-check: all references resolve"
else
  echo "  ! ai-link-check: $(tail -1 /tmp/_polaris_links.out)"
  fails=$((fails+1))
fi

# 3. Reminder for the DB-backed product suites (need Postgres + the venv).
echo "  · DB suites: confirm via 'scripts/ai-test.sh' (test_check_constraints,"
echo "    test_invariants_property, test_redaction_property, test_app, test_cli)"

echo
if [ "$fails" -eq 0 ]; then
  echo "── READY ──"
  exit 0
fi
echo "── ${fails} gate failure(s) ──"
[ "$STRICT" -eq 1 ] && exit 1
exit 0
