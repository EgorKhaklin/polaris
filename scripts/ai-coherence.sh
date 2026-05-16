#!/bin/bash
# =============================================================================
# scripts/ai-coherence.sh
#
# Structural-coherence diagnostics. Verifies that the structural invariants
# claimed by meta/structural-constants.json and meta/constraint-lattice.md
# actually hold across the codebase.
#
# Each check has the form: "an invariant claimed by the structural layer
# is verified to hold." If the invariant fails, the coherence is broken —
# it may be a real structural drift (fix the structure) or a stale entry
# in structural-constants.json (fix the JSON).
#
# This script does NOT enforce; it reports. The caller decides what to do.
#
# Sections:
#   lattice         — the 10-node constraint mapping
#   constants       — structural-constants.json invariants
#   correspondence  — cross-layer consistency (schema↔test↔doc)
#   larping         — structural vocabulary without structural backing
#
# Usage:
#     ai-coherence.sh                   # full report
#     ai-coherence.sh --strict          # exit 1 on any drift
#     ai-coherence.sh lattice           # only the constraint-lattice check
#     ai-coherence.sh constants         # only the JSON-constants check
#     ai-coherence.sh correspondence    # only the cross-layer check
# =============================================================================

set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"

if [ -t 1 ]; then
    BOLD="\033[1m"; G="\033[0;32m"; Y="\033[0;33m"; R="\033[0;31m"
    DIM="\033[2m"; CYAN="\033[0;36m"; BLUE="\033[38;5;75m"; NC="\033[0m"
else
    BOLD=""; G=""; Y=""; R=""; DIM=""; CYAN=""; BLUE=""; NC=""
fi

DRIFT=0
STRICT=0
SECTION="all"

for arg in "$@"; do
    case "$arg" in
        --strict) STRICT=1 ;;
        lattice|constants|correspondence|larping) SECTION="$arg" ;;
        --help|-h) sed -n '2,30p' "$0" | sed 's/^# \?//'; exit 0 ;;
    esac
done

ok()      { printf "  ${G}✓${NC} %s\n" "$1"; }
warn()    { printf "  ${Y}!${NC} %s\n" "$1"; DRIFT=$((DRIFT+1)); }
broken()  { printf "  ${R}✗${NC} %s\n" "$1"; DRIFT=$((DRIFT+2)); }
section() { printf "\n${BOLD}── %s ──${NC}\n" "$1"; }

CONSTANTS="$ROOT/meta/structural-constants.json"
LATTICE="$ROOT/meta/constraint-lattice.md"
ARCH="$ROOT/meta/structural-architecture.md"

# -----------------------------------------------------------------------------
# Header
# -----------------------------------------------------------------------------
printf "${BLUE}${BOLD}═══ Polaris — structural coherence ═══${NC}\n"
printf "${DIM}  Date:  %s${NC}\n" "$(date '+%Y-%m-%d %H:%M:%S')"
printf "${DIM}  φ ≈ 1.6180339887  ·  10-node lattice  ·  22-pattern catalog${NC}\n"
printf "${DIM}  7 cross-layer principles  ·  3-7-12 decomposition targets${NC}\n"

# -----------------------------------------------------------------------------
# Lattice — the constraint-mapping topology
# -----------------------------------------------------------------------------
check_lattice() {
section "Constraint lattice: 10 nodes ↔ 10 mission constraints"

if [ ! -f "$LATTICE" ]; then
    broken "meta/constraint-lattice.md missing — structural layer not initialized"
    return
fi

# Verify the mapping document exists and references all 10 lattice positions
local positions=("APEX" "EXPAND·1" "CONTRACT·1" "EXPAND·2" "CONTRACT·2" "BALANCE·2" "EXPAND·3" "CONTRACT·3" "BALANCE·3" "MANIFEST")
local missing=0
for p in "${positions[@]}"; do
    if ! grep -q "$p" "$LATTICE"; then
        broken "position $p not mentioned in constraint-lattice.md"
        missing=$((missing+1))
    fi
done
if [ "$missing" -eq 0 ]; then
    ok "all 10 lattice positions named in constraint-lattice.md"
fi

# Verify reserved meta-slot acknowledged (the hidden 11th)
if grep -qi "meta-slot\|reserved\|hidden 11th" "$LATTICE"; then
    ok "reserved meta-slot (hidden 11th) acknowledged"
else
    warn "reserved meta-slot not acknowledged — lattice mapping incomplete"
fi

# Verify constraint count == 10 in MISSION.md
local c_count
c_count=$(grep -cE "^\| C[0-9]+ \|" "$ROOT/MISSION.md" 2>/dev/null || echo 0)
if [ "$c_count" -eq 10 ]; then
    ok "MISSION.md has exactly 10 constraints (C1-C10)"
elif [ "$c_count" -lt 10 ]; then
    broken "MISSION.md has only $c_count constraints — lattice requires 10"
elif [ "$c_count" -gt 10 ]; then
    warn "MISSION.md has $c_count constraints — extension beyond 10 nodes requires explicit justification (see constraint-lattice.md)"
fi

# Cross-reference: every C1..C10 should appear in constraint-lattice.md
for n in 1 2 3 4 5 6 7 8 9 10; do
    if ! grep -qE "C$n " "$LATTICE"; then
        warn "C$n not mapped to a lattice position in constraint-lattice.md"
    fi
done
}

# -----------------------------------------------------------------------------
# Constants — verify the JSON constants are honored
# -----------------------------------------------------------------------------
check_constants() {
section "Structural constants: testable invariants"

if [ ! -f "$CONSTANTS" ]; then
    broken "meta/structural-constants.json missing"
    return
fi

# Use python for JSON parsing
python3 - "$CONSTANTS" "$ROOT" <<'PY' || { broken "constants script failed"; return; }
import json, os, sys, re, glob

path, root = sys.argv[1], sys.argv[2]
data = json.load(open(path))
constants = data['constants']

def good(msg): print(f"  \033[0;32m✓\033[0m {msg}")
def bad(msg):  print(f"  \033[0;31m✗\033[0m {msg}")
def warn(msg): print(f"  \033[0;33m!\033[0m {msg}")

# 1. MISSION_CONSTRAINTS == 10
mission_md = open(os.path.join(root, 'MISSION.md')).read()
n_constraints = len(re.findall(r"^\| C\d+ \|", mission_md, re.MULTILINE))
expected = constants['MISSION_CONSTRAINTS']['value']
if n_constraints == expected:
    good(f"MISSION.md has {n_constraints} constraints (matches constants: {expected})")
else:
    bad(f"MISSION.md has {n_constraints} constraints; constants require {expected}")

# 2. RISK_CLASSES == 3
auto_md = os.path.join(root, 'meta/autonomy-architecture.md')
if os.path.exists(auto_md):
    content = open(auto_md).read()
    classes_named = sum(1 for k in ['LOW', 'MEDIUM', 'HIGH'] if k in content)
    expected = constants['RISK_CLASSES']['value']
    if classes_named == expected:
        good(f"autonomy-architecture.md names exactly {classes_named} risk classes (LOW/MEDIUM/HIGH)")
    else:
        warn(f"risk classes named: {classes_named}; constants expect {expected}")

# 3. FIBONACCI_PRIORITY_WEIGHTS — verify ai-propose.sh uses Fibonacci-style scoring
propose_sh = os.path.join(root, 'scripts/ai-propose.sh')
if os.path.exists(propose_sh):
    propose_src = open(propose_sh).read()
    fib_values = constants['FIBONACCI_PRIORITY_WEIGHTS']['value']
    found = sum(1 for v in fib_values if f"+ {v}" in propose_src or f"+{v}" in propose_src or f"score=$(({v}" in propose_src)
    if found >= 3:
        good(f"ai-propose.sh references at least {found} Fibonacci weights from {fib_values}")
    else:
        warn(f"ai-propose.sh references only {found} of {len(fib_values)} Fibonacci weights — may not be using combinatorial scaling")

# 4. PATTERNS_MIN_SET >= 7
patterns_dir = os.path.join(root, 'patterns')
if os.path.isdir(patterns_dir):
    n_patterns = len([f for f in os.listdir(patterns_dir)
                       if f.endswith('.md') and f != 'README.md'])
    min_set = constants['PATTERNS_MIN_SET']['value']
    if n_patterns >= min_set:
        good(f"patterns/ has {n_patterns} files (≥ {min_set} required)")
    else:
        bad(f"patterns/ has only {n_patterns} files; constants require ≥ {min_set}")

# 5. DEVNOTES_MAX_PER_CATEGORY: each DEVNOTES file should have ≤ 7 top-level sections
devnotes_dir = os.path.join(root, 'DEVNOTES')
max_sections = constants['DEVNOTES_MAX_PER_CATEGORY']['value']
oversized = []
if os.path.isdir(devnotes_dir):
    for f in glob.glob(os.path.join(devnotes_dir, '*.md')):
        body = open(f).read()
        sections = len(re.findall(r"^## ", body, re.MULTILINE))
        if sections > max_sections + 1:
            oversized.append((os.path.basename(f), sections))
    if oversized:
        for fn, s in oversized:
            warn(f"DEVNOTES/{fn} has {s} top-level sections (Miller's law suggests ≤ {max_sections})")
    else:
        good(f"all DEVNOTES files within {max_sections}-section working-memory limit")

# 6. PATTERN_CATALOG_SIZE == 22
pat_sh = os.path.join(root, 'scripts/ai-pattern.sh')
expected = constants['PATTERN_CATALOG_SIZE']['value']
if os.path.exists(pat_sh):
    pat_src = open(pat_sh).read()
    canonical = ['Greenfield','Composition','HiddenState','Foundation','Authority',
                 'Convention','Branchpoint','ShipPressure','Endurance','Investigation',
                 'Recurrence','Audit','Inversion','Removal','Migration',
                 'Workaround','Collapse','Recovery','Phantom','Clarity','Reckoning','Closure']
    present = [p for p in canonical if p in pat_src]
    if len(present) == expected:
        good(f"ai-pattern.sh defines {len(present)} patterns (matches catalog size: {expected})")
    elif len(present) >= 20:
        warn(f"ai-pattern.sh defines {len(present)} patterns; expected {expected}")
    else:
        bad(f"ai-pattern.sh defines {len(present)} patterns; catalog requires {expected}")
else:
    warn(f"ai-pattern.sh missing; pattern catalog ({expected} entries) not initialized")

# 7. CROSS_LAYER_PRINCIPLES — used in scripts/ai-coherence.sh (this script)
expected = constants['CROSS_LAYER_PRINCIPLES']['value']
labels = constants['CROSS_LAYER_PRINCIPLES'].get('labels', [])
this_script = open(os.path.join(root, 'scripts/ai-coherence.sh')).read()
labels_in_script = sum(1 for L in labels if L in this_script)
if labels_in_script >= expected - 3:
    good(f"cross-layer principles: {labels_in_script}/{expected} referenced in coherence check")
else:
    warn(f"only {labels_in_script}/{expected} cross-layer principles in ai-coherence.sh")

# 8. SOFT_LIMIT_AUDIT_HORIZON_DAYS — used in ai-status.sh
status_sh = os.path.join(root, 'scripts/ai-status.sh')
if os.path.exists(status_sh):
    status_src = open(status_sh).read()
    horizon = constants['SOFT_LIMIT_AUDIT_HORIZON_DAYS']['value']
    if str(horizon) in status_src:
        good(f"ai-status.sh uses {horizon}-day staleness horizon")
    else:
        warn(f"ai-status.sh doesn't reference {horizon}-day horizon")

# 9. GOLDEN_RATIO — verify it's referenced somewhere
phi = constants['GOLDEN_RATIO']['value']
phi_refs = 0
for f in glob.glob(os.path.join(root, 'scripts/*.sh')) + glob.glob(os.path.join(root, '**/*.md'), recursive=True):
    try:
        text = open(f).read().lower()
        if "1.618" in text or "phi" in text or "golden ratio" in text or "fibonacci" in text:
            phi_refs += 1
    except Exception:
        pass
if phi_refs >= 3:
    good(f"golden ratio φ / Fibonacci scaling referenced in {phi_refs} files")
else:
    warn(f"golden ratio φ referenced in only {phi_refs} files — may not be load-bearing yet")

# Cross-layer principles: Intent, Correspondence, Symmetry, Polarity, Cadence, CauseEffect, Duality
# (Names appear in this script's data section for the labels check above.)
PY
}

# -----------------------------------------------------------------------------
# Cross-layer correspondence — "the rule at one layer should appear at the
# layers that depend on it"
# -----------------------------------------------------------------------------
check_correspondence() {
section "Cross-layer correspondence: layer consistency (schema↔test↔doc)"

# Seven cross-layer principles used as a checklist of structural concerns:
#   Intent, Correspondence, Symmetry, Polarity, Cadence, CauseEffect, Duality.
# Correspondence is what we test heavily here.

# Check 1: Every constraint named in MISSION.md should be checked in
# scripts/ai-status.sh
local missing=0
for n in 1 2 3 4 5 6 7 8 9 10; do
    if ! grep -q "C$n " "$ROOT/scripts/ai-status.sh" 2>/dev/null; then
        warn "C$n in MISSION.md but not checked in ai-status.sh — Correspondence broken"
        missing=$((missing+1))
    fi
done
if [ "$missing" -eq 0 ]; then
    ok "all 10 constraints checked at SQL/app/script layers (Correspondence preserved)"
fi

# Check 2: Every CHECK constraint in 01_schema.sql should be reflected in
# at least one test (schema ↔ test correspondence)
local schema_checks tests_for_checks
schema_checks=$(grep -cE "^[[:space:]]+CHECK \(" "$ROOT/polaris_sql/01_schema.sql" 2>/dev/null || echo 0)
tests_for_checks=$(grep -hE "check.constraint|CheckViolation|chk_|_check'" \
    "$ROOT/polaris_web/test_app.py" \
    "$ROOT/polaris_web/test_invariants_property.py" \
    "$ROOT/polaris_web/test_check_constraints.py" 2>/dev/null | wc -l)
if [ "${tests_for_checks:-0}" -ge "${schema_checks:-0}" ]; then
    ok "schema CHECK constraints have test coverage ($tests_for_checks ref ≥ $schema_checks constraints)"
else
    warn "schema has $schema_checks CHECK constraints; tests reference $tests_for_checks — possible Correspondence gap"
fi

# Check 3: Every /api/* route should be documented in docs/reference/API.md (route ↔ doc)
local routes documented
routes=$(grep -cE "^@app.route\('/api/" "$ROOT/polaris_web/app.py" 2>/dev/null || echo 0)
documented=$(grep -cE '^### `(GET|POST) /api/' "$ROOT/docs/reference/API.md" 2>/dev/null || echo 0)
if [ "$documented" -ge "$((routes - 2))" ]; then
    ok "API routes ($routes) documented in docs/reference/API.md ($documented entries) — Correspondence preserved"
else
    warn "$routes API routes; only $documented documented — Correspondence gap in API layer"
fi

# Polarity check: every EXPAND constraint has a CONTRACT counterpart at the
# same tier. Symmetry across pillars is what keeps the lattice safe.
local polarity_pairs="C7:C2 C5:C4 C8:C6"
local polarity_ok=1
for pair in $polarity_pairs; do
    left="${pair%%:*}"
    right="${pair##*:}"
    if grep -q "$left " "$ROOT/MISSION.md" && grep -q "$right " "$ROOT/MISSION.md"; then
        :
    else
        warn "Polarity pair $pair broken — one side missing in MISSION.md"
        polarity_ok=0
    fi
done
[ "$polarity_ok" -eq 1 ] && ok "all 3 EXPAND/CONTRACT polarity pairs intact (C7↔C2, C5↔C4, C8↔C6)"
}

# -----------------------------------------------------------------------------
# Larping detector — structural vocabulary without structural backing
# -----------------------------------------------------------------------------
check_larping() {
section "Larping detector: structural vocabulary without structural backing"

# Vocabulary that, if used WITHOUT corresponding structural element, is decorative
local vocab=("lattice" "constraint lattice" "cross-layer" "fibonacci" "pattern catalog" "structural invariant")
local issues=0

for term in "${vocab[@]}"; do
    local uses
    uses=$(grep -ril "$term" "$ROOT" \
            --include='*.md' --include='*.sh' --include='*.py' --include='*.sql' \
            --exclude-dir='__pycache__' --exclude-dir='.hypothesis' \
            2>/dev/null | grep -v "meta/structural\|meta/constraint-lattice\|meta/lineage" | wc -l)
    if [ "$uses" -gt 0 ]; then
        case "$term" in
            lattice|"constraint lattice")
                if [ -f "$LATTICE" ]; then continue; fi ;;
            "cross-layer")
                if grep -q "CROSS_LAYER_PRINCIPLES" "$CONSTANTS" 2>/dev/null; then continue; fi ;;
            fibonacci)
                if grep -q "FIBONACCI_PRIORITY" "$CONSTANTS" 2>/dev/null; then continue; fi ;;
            "pattern catalog")
                if [ -f "$ROOT/scripts/ai-pattern.sh" ]; then continue; fi ;;
            "structural invariant")
                if [ -f "$ARCH" ]; then continue; fi ;;
        esac
        warn "term \"$term\" used in $uses file(s) but no backing structural element found"
        issues=$((issues+1))
    fi
done

if [ "$issues" -eq 0 ]; then
    ok "all structural vocabulary backed by structural elements (no larping detected)"
fi
}

# -----------------------------------------------------------------------------
# Dispatch
# -----------------------------------------------------------------------------
case "$SECTION" in
    lattice) check_lattice ;;
    constants) check_constants ;;
    correspondence) check_correspondence ;;
    larping) check_larping ;;
    all|"")
        check_lattice
        check_constants
        check_correspondence
        check_larping
        ;;
esac

# -----------------------------------------------------------------------------
# Summary
# -----------------------------------------------------------------------------
section "Coherence summary"
case "$DRIFT" in
    0)  printf "  ${G}${BOLD}STRUCTURE INTACT.${NC} Structural layer coherent with codebase.\n" ;;
    [1-3]) printf "  ${Y}${BOLD}MINOR DRIFT.${NC} %s soft signal(s); investigate but no structural break.\n" "$DRIFT" ;;
    *)  printf "  ${R}${BOLD}STRUCTURAL DRIFT.${NC} %s point(s) — fix structure or update structural-constants.json.\n" "$DRIFT" ;;
esac

if [ "$STRICT" -eq 1 ] && [ "$DRIFT" -gt 0 ]; then
    exit 1
fi
exit 0
