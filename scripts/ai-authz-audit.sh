#!/bin/bash
# =============================================================================
# scripts/ai-authz-audit.sh — authorization-as-code review (v9.19)
#
# Walks all four authorization surfaces (app.py decorators + 09_grants.sql +
# AppUser.role CHECK enum + IssuerDiscretionPolicy) and emits a unified
# "who can do what" report. Surfaces drift between the decorator-declared
# roles in app.py and the role enum in AppUser, plus tables in the schema
# that lack any GRANT statement.
#
# Pure static analysis; no DB required for §§I-IV (the IssuerDiscretionPolicy
# rows are optional DB context if reachable).
#
# Usage:
#     scripts/ai-authz-audit.sh                    # full report
#     scripts/ai-authz-audit.sh --json             # JSON (audit trail)
#     scripts/ai-authz-audit.sh --role admin       # filter to one role
# =============================================================================
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"

# Find a working Python 3
PY=""
for cand in \
    "$ROOT/polaris_web/venv/bin/python" \
    "$(command -v python3)"; do
    if [ -n "$cand" ] && [ -x "$cand" ]; then
        PY="$cand"
        break
    fi
done
[ -z "$PY" ] && { echo "ai-authz-audit: no python3" >&2; exit 1; }

for arg in "$@"; do
    case "$arg" in
        --help|-h)
            sed -n '2,18p' "$0" | sed 's/^# \?//'
            exit 0
            ;;
    esac
done

exec "$PY" "$HERE/ai_authz_audit.py" "$@"
