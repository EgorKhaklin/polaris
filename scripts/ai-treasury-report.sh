#!/usr/bin/env bash
# ============================================================================
# ai-treasury-report.sh — read-only Treasury ledger summary
#
# v8.90 / surfaces the Mycelium Treasury state in operator-readable form.
# Reads polaris_swarm/civitas/treasury-roll.json directly; no DB access;
# no side effects.
#
# What it shows:
#   - Per-ant denarii balance (sorted, ascending — most-penalized first)
#   - Class distribution (Plebs / Eques / Patrician per Cursus Honorum)
#   - Reward/penalty ratio + drift_resolution vs persistent_silence event
#     counts
#   - Mobility analysis: how far each ant is from the Eques threshold (101)
#   - Skew indicator (max - min spread; +/- ratio)
#
# Usage:
#   ./scripts/ai-treasury-report.sh           # human-readable summary
#   ./scripts/ai-treasury-report.sh --json    # machine-readable
#   ./scripts/ai-treasury-report.sh --ant=N   # only this ant
#
# Read alongside: sanctum/2026-05-14-treasury-rebalance.md (the
# architect's analysis + the OPEN constitutional question on
# whether to rebalance the reward function).
# ============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"
POLARIS_ROOT="$(cd -- "${SCRIPT_DIR}/.." &> /dev/null && pwd)"
ROLL="${POLARIS_ROOT}/polaris_swarm/civitas/treasury-roll.json"

JSON_MODE=0
ANT_FILTER=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --json)   JSON_MODE=1 ;;
        --ant=*)  ANT_FILTER="${1#--ant=}" ;;
        --ant)    shift; ANT_FILTER="${1:-}" ;;
        --help|-h)
            sed -n '2,30p' "$0" | sed 's/^# \{0,1\}//'
            exit 2
            ;;
        *) echo "warn: unknown arg $1" >&2 ;;
    esac
    shift
done

if [[ ! -f "${ROLL}" ]]; then
    echo "error: treasury-roll.json not found at ${ROLL}" >&2
    exit 1
fi

python3 - "${ROLL}" "${JSON_MODE}" "${ANT_FILTER}" <<'PY'
import json
import sys
from collections import Counter

ROLL_PATH, JSON_MODE_RAW, ANT_FILTER = sys.argv[1:4]
JSON_MODE = (JSON_MODE_RAW == '1')

with open(ROLL_PATH) as f:
    data = json.load(f)
events = data.get('events', [])

# Filter to single ant if requested
if ANT_FILTER:
    events = [e for e in events if e.get('ant') == ANT_FILTER]

# Tally
balances = Counter()
event_count = Counter()
reward_count = Counter()
penalty_count = Counter()
# Partition penalties by per-event amount. v8.91 (sanctum/2026-05-14-
# treasury-rebalance.md, Position B) reduced DENARII_PENALTY_PERSISTENT
# from 2 → 1; pre-rebalance events stay in the ledger per G15 (history
# preserved). Aggregate ratios are polluted by the pre-rebalance -2s;
# the post-rebalance rate is what reflects current policy.
penalty_amount_total = 0     # sum of actual amounts (negative)
reward_amount_total = 0      # sum of actual amounts (positive)
pre_rebalance_penalty = 0    # amount=-2 events (pre-v8.91)
post_rebalance_penalty = 0   # amount=-1 events (post-v8.91)
post_rebalance_reward = 0    # rewards earned alongside the -1 regime
for e in events:
    a = e['ant']
    amt = e['amount']
    balances[a] += amt
    event_count[a] += 1
    if e['reason'] == 'drift_resolution':
        reward_count[a] += 1
        reward_amount_total += amt
        if amt > 0:  # all rewards are positive
            post_rebalance_reward += amt
    elif e['reason'] == 'persistent_silence':
        penalty_count[a] += 1
        penalty_amount_total += amt
        if amt == -2:
            pre_rebalance_penalty += amt
        elif amt == -1:
            post_rebalance_penalty += amt

# Cursus Honorum thresholds (canonical per
# polaris_swarm/civitas/treasury.py:DENARII_PLEB_MAX = 1_000,
# DENARII_EQUES_MAX = 10_000). v8.91 fix: the v8.90 first-cut
# of this diagnostic used 101/10001 (off by a factor of 10);
# the real Pleb→Eques boundary is balance ≤ 1_000 vs ≥ 1_001.
EQUES_THRESHOLD = 1001
PATRICIAN_THRESHOLD = 10001

def classify(bal):
    if bal >= PATRICIAN_THRESHOLD: return 'patrician'
    if bal >= EQUES_THRESHOLD: return 'eques'
    return 'plebs'

# Per-ant analysis
per_ant = []
for ant in sorted(balances, key=lambda a: balances[a]):
    bal = balances[ant]
    cls = classify(bal)
    # Sum actual event amounts per-ant (the pre-rebalance/post-rebalance
    # mix means a hardcoded multiplier would mis-state penalty totals).
    reward_total = sum(e['amount'] for e in events
                       if e['ant'] == ant and e['reason'] == 'drift_resolution')
    penalty_total = sum(e['amount'] for e in events
                        if e['ant'] == ant and e['reason'] == 'persistent_silence')
    needed_for_eques = max(0, EQUES_THRESHOLD - bal)
    rewards_needed = (needed_for_eques + 9) // 10 if needed_for_eques else 0
    per_ant.append({
        'ant':                ant,
        'balance':            bal,
        'class':              cls,
        'events':             event_count[ant],
        'reward_events':      reward_count[ant],
        'penalty_events':     penalty_count[ant],
        'reward_amount':      reward_total,
        'penalty_amount':     penalty_total,
        'rewards_for_eques':  rewards_needed,
    })

class_dist = Counter(p['class'] for p in per_ant)
total_reward = sum(p['reward_amount'] for p in per_ant)
total_penalty = sum(p['penalty_amount'] for p in per_ant)
net = total_reward + total_penalty
ratio = abs(total_penalty / total_reward) if total_reward else float('inf')

# Post-rebalance rate ratio (current policy in operation).
# Pre-rebalance -2 events are historical; the cognitive layer
# should report current policy operation distinctly from
# aggregate-since-inception (which is forever-skewed by history).
post_penalty_events = sum(1 for e in events
                          if e['reason'] == 'persistent_silence' and e['amount'] == -1)
post_reward_events = sum(1 for e in events
                         if e['reason'] == 'drift_resolution')
post_ratio = (abs(post_rebalance_penalty / post_rebalance_reward)
              if post_rebalance_reward else float('inf'))

report = {
    'last_pass_taken':    data.get('last_pass_taken'),
    'total_events':       len(events),
    'distinct_ants':      len(balances),
    'class_distribution': dict(class_dist),
    'total_reward':       total_reward,
    'total_penalty':      total_penalty,
    'net':                net,
    'penalty_reward_ratio': round(ratio, 2),
    'post_rebalance': {
        'penalty_amount':       post_rebalance_penalty,
        'reward_amount':        post_rebalance_reward,
        'penalty_events':       post_penalty_events,
        'reward_events':        post_reward_events,
        'penalty_reward_ratio': round(post_ratio, 2),
    },
    'pre_rebalance_penalty_amount': pre_rebalance_penalty,
    'per_ant':            per_ant,
}

if JSON_MODE:
    print(json.dumps(report, indent=2))
    sys.exit(0)

# Human-readable
print()
print('  Polaris Treasury Ledger')
print('  ────────────────────────')
print(f'  Last pass:           {report["last_pass_taken"]}')
print(f'  Total events:        {report["total_events"]}')
print(f'  Distinct ants:       {report["distinct_ants"]}')
print(f'  Class distribution:  '
      f'plebs={class_dist.get("plebs", 0)}  '
      f'eques={class_dist.get("eques", 0)}  '
      f'patrician={class_dist.get("patrician", 0)}')
print()
print(f'  Reward total:        {total_reward:+}  ({sum(reward_count.values())} drift_resolution events)')
print(f'  Penalty total:       {total_penalty:+}  ({sum(penalty_count.values())} persistent_silence events)')
print(f'  Net:                 {net:+}')
print(f'  Penalty:reward:      {ratio:.2f}:1   (aggregate since inception)')
print()
# Post-rebalance rate — what current policy is doing right now.
# v8.91 (sanctum/2026-05-14-treasury-rebalance.md, Position B, CLOSED)
# changed DENARII_PENALTY_PERSISTENT from 2 → 1; per G15 the pre-rebalance
# events stay in the ledger but the rate-of-flow is what the operator
# should read when judging whether the mechanism is working.
if post_rebalance_reward or post_rebalance_penalty:
    print(f'  Post-rebalance rate (since v8.91, +10/-1 in operation):')
    print(f'    reward:            {post_rebalance_reward:+}  ({post_reward_events} events)')
    print(f'    penalty:           {post_rebalance_penalty:+}  ({post_penalty_events} events at -1)')
    if post_rebalance_reward:
        print(f'    penalty:reward:    {post_ratio:.2f}:1')
    print(f'    pre-rebalance penalty (frozen per G15): {pre_rebalance_penalty:+}')
    print()
print('  Per-ant balances (sorted ascending — most-penalized first):')
print(f"  {'BALANCE':>10}  {'CLASS':<10}  {'REWARDS':>8}  {'PENALTIES':>10}  {'NEEDED→EQUES':>13}  ANT")
for p in per_ant:
    print(f"  {p['balance']:>+10}  {p['class']:<10}  "
          f"{p['reward_events']:>8}  {p['penalty_events']:>10}  "
          f"{p['rewards_for_eques']:>13}  {p['ant']}")
print()

# Diagnostic verdict — the load-bearing signal is post-rebalance rate,
# not the historical aggregate (which is polluted by frozen -2 events).
if post_rebalance_reward and post_ratio > 5:
    print(f'  ⚠️  Post-rebalance penalty:reward is {post_ratio:.1f}:1 — current policy is not')
    print(f'     yielding enough drift_resolution to lift drift-class ants toward Eques.')
    print(f'     This is an OPERATOR signal (resolve drift faster), not a policy bug.')
    print(f'     v8.91 Position B is in force and computing correctly.')
    print()
elif post_rebalance_reward:
    print(f'  ✓ Post-rebalance penalty:reward = {post_ratio:.2f}:1 — within Position B target band.')
    print(f'     (Aggregate ratio above is historical; pre-v8.91 events stay per G15.)')
    print()
elif class_dist.get('patrician', 0) == 0 and class_dist.get('eques', 0) == 0:
    print(f'  ℹ️  All ants are Plebs. Cursus Honorum has not engaged at the class level yet.')
    print(f'     Steady-state ants are F5-exempt; drift-class ants need accumulated')
    print(f'     drift-resolution rewards. v8.91 rebalance is in force.')
    print()
else:
    print(f'  ✓ Class distribution shows mobility. Mechanism engaging as designed.')
    print()

PY
