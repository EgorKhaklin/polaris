#!/usr/bin/env bash
# ============================================================================
# polaris-ai-done-hook.sh — Claude Code PreToolUse hook for ship commits
#                          (v9.32 / hookify integration)
#
# Purpose: enforce the v9.31-freeze ship-gate discipline mechanically rather
# than relying on agent memory. When a ship commit (one that stages
# polaris_web/__version__.py) is about to fire, run ai-done.sh first.
# If NOT READY, exit non-zero — the harness blocks the tool call.
#
# Scope: ONLY ship commits. Hygiene commits, branch ops, and non-commit bash
# calls pass through unchanged. This is the post-freeze hardening that
# CLAUDE.md ship sequence step 12 mandates ("Pre-ship gate: bash
# scripts/ai-done.sh. Must report READY.") — converted from "operator
# must remember" to "harness enforces."
#
# Sanctum: 2026-05-17-plugin-installation-tier2.md (Option A) authorized
# the hookify integration as a follow-up ship; v9.32 is that ship.
# Sanctum: 2026-05-17-v9-31-prep.md (Option A) sequenced v9.32 as
# post-freeze hardening per MISSION.md §"From v9.32 forward (a) Hardening".
#
# Input: Claude Code passes the tool call as JSON on stdin. We parse the
# `tool_input.command` field; only act if it matches `git commit`.
#
# Output: stderr lines surface in the Claude session log. Exit non-zero
# blocks the tool call.
#
# Override: set POLARIS_HOOK_BYPASS=1 to skip the gate (audit-trail line
# is still emitted so the bypass is visible).
# ============================================================================

set -uo pipefail

# Read the stdin payload (Claude Code hook protocol)
PAYLOAD="$(cat || true)"

# Extract the bash command being attempted. Multi-line commands are
# preserved. If we can't parse, pass through (do not block on parser bugs).
COMMAND="$(printf '%s' "${PAYLOAD}" \
    | python3 -c '
import json, sys
try:
    d = json.loads(sys.stdin.read())
    print(d.get("tool_input", {}).get("command", ""))
except Exception:
    pass
' 2>/dev/null || true)"

# Pass through if not a git commit. We match on the substring `git commit`
# bounded by word boundaries (so `git commit-tree` and similar don't
# trigger; the realistic ship command is `git commit -m ...` or
# `git commit --amend`).
if ! printf '%s' "${COMMAND}" | grep -qE '(^|[[:space:]])git[[:space:]]+commit([[:space:]]|$)'; then
    exit 0
fi

# Pass through if no __version__.py in staged files (i.e., not a ship).
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"
POLARIS_ROOT="$(cd -- "${SCRIPT_DIR}/.." &> /dev/null && pwd)"
cd "${POLARIS_ROOT}" || { echo "polaris-ai-done-hook: cannot cd to ${POLARIS_ROOT}" >&2; exit 0; }

STAGED="$(git diff --cached --name-only 2>/dev/null || true)"
if ! printf '%s' "${STAGED}" | grep -qx 'polaris_web/__version__.py'; then
    # Hygiene / non-ship commit. Pass through silently.
    exit 0
fi

# Ship commit. Honor explicit bypass with audit-trail line.
if [[ "${POLARIS_HOOK_BYPASS:-0}" == "1" ]]; then
    echo "polaris-ai-done-hook: SHIP COMMIT BYPASS — POLARIS_HOOK_BYPASS=1 set (audit-trail visible)" >&2
    exit 0
fi

# Run ai-done.sh. Capture exit code; report verdict to stderr (visible
# in Claude session log).
echo "polaris-ai-done-hook: ship commit detected (polaris_web/__version__.py staged); running ai-done.sh pre-ship gate..." >&2

if bash "${POLARIS_ROOT}/scripts/ai-done.sh" >&2; then
    echo "polaris-ai-done-hook: ai-done READY — ship commit allowed to proceed." >&2
    exit 0
fi

echo "polaris-ai-done-hook: ai-done reported NOT READY — BLOCKING ship commit. Fix the failures + retry, or set POLARIS_HOOK_BYPASS=1 to override." >&2
exit 1
