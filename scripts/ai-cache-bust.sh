#!/bin/bash
# =============================================================================
# scripts/ai-cache-bust.sh — auto cache-bust query strings on CSS/JS (v8.6)
#
# Browsers cache /static/*.css and /static/*.js aggressively. Pre-v8.5 the
# template tag was `<script src="/static/atlas-globe.js">` — the URL never
# changed, so dev iterations served stale JS until the user did a hard
# reload. v8.2 added manual `?v=v8.2` query strings. v8.3, v8.4, v8.5 each
# required hand-bumping those strings — error-prone and easy to forget.
#
# This script computes a SHA-256 prefix of each tracked static file and
# rewrites the corresponding `?v=...` in the templates. Run before
# committing a visual change. The "version" is just a content fingerprint
# — same content produces same URL, browser cache stays useful when
# nothing changed.
#
# What's tracked:
#   polaris_web/static/polaris.css       → ?v=<hash> in base.html
#   polaris_web/static/atlas-globe.js    → ?v=<hash> in atlas.html
#
# Usage:
#     scripts/ai-cache-bust.sh           # report only
#     scripts/ai-cache-bust.sh --apply   # rewrite the templates
# =============================================================================

set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"

if [ -t 1 ]; then
    BOLD="\033[1m"; G="\033[0;32m"; Y="\033[0;33m"
    DIM="\033[2m"; NC="\033[0m"
else
    BOLD=""; G=""; Y=""; DIM=""; NC=""
fi

APPLY=0
[ "${1:-}" = "--apply" ] && APPLY=1

# -----------------------------------------------------------------------------
# Tracked file → template pairs. Add new entries here when the surface grows.
# -----------------------------------------------------------------------------
TRACKED=(
    "polaris_web/static/polaris.css|polaris_web/templates/base.html|polaris.css"
    "polaris_web/static/polaris-scifi.css|polaris_web/templates/base.html|polaris-scifi.css"
    "polaris_web/static/atlas-globe.js|polaris_web/templates/atlas.html|atlas-globe.js"
)

# -----------------------------------------------------------------------------
# SHA-256 short hash — first 8 hex chars of the digest. Same content →
# same hash; different content → different hash with overwhelming probability.
# Prefix with 'h' so it's always alphanumeric and never starts with a digit
# (some templating systems get confused otherwise).
# -----------------------------------------------------------------------------
content_hash() {
    if command -v shasum >/dev/null 2>&1; then
        shasum -a 256 "$1" | awk '{print "h"substr($1,1,8)}'
    else
        sha256sum "$1" | awk '{print "h"substr($1,1,8)}'
    fi
}

printf "${BOLD}Cache-bust analysis${NC}\n\n"

drift=0
for entry in "${TRACKED[@]}"; do
    IFS='|' read -r src tmpl name <<< "$entry"
    src_full="$ROOT/$src"
    tmpl_full="$ROOT/$tmpl"
    if [ ! -f "$src_full" ] || [ ! -f "$tmpl_full" ]; then
        printf "  ${Y}skip${NC} %s (file missing)\n" "$src"
        continue
    fi
    fresh=$(content_hash "$src_full")
    # Pull current version from the template. The Jinja form
    #     {{ url_for('static', filename='polaris.css') }}?v=v8.3
    # puts the filename and the `?v=` on the same line but separated by the
    # closing }}. We anchor on the line containing `filename='<name>'` and
    # extract the trailing `?v=...` from that same line.
    current=$(grep -E "filename='${name}'" "$tmpl_full" \
               | grep -oE '\?v=[A-Za-z0-9._-]+' \
               | head -1 \
               | sed 's/^?v=//')
    current="${current:-(none)}"
    if [ "$current" = "$fresh" ]; then
        printf "  ${G}OK${NC}   %s  ?v=%s (in sync)\n" "$src" "$fresh"
    else
        printf "  ${Y}DRIFT${NC} %s\n" "$src"
        printf "         template:  ${Y}?v=%s${NC}\n" "$current"
        printf "         content:   ${G}?v=%s${NC}\n" "$fresh"
        drift=1
    fi
done

if [ "$drift" -eq 0 ]; then
    printf "\n${G}All tracked files are in sync.${NC}\n"
    exit 0
fi

if [ "$APPLY" -ne 1 ]; then
    printf "\n${DIM}Pass --apply to rewrite the templates with fresh content hashes.${NC}\n"
    exit 0
fi

# -----------------------------------------------------------------------------
# Apply mode — rewrite each `<filename>?v=<old>` to `<filename>?v=<fresh>`.
# Done via Python to avoid sed -i portability hassle.
# -----------------------------------------------------------------------------
for entry in "${TRACKED[@]}"; do
    IFS='|' read -r src tmpl name <<< "$entry"
    src_full="$ROOT/$src"
    tmpl_full="$ROOT/$tmpl"
    [ -f "$src_full" ] && [ -f "$tmpl_full" ] || continue
    fresh=$(content_hash "$src_full")
    python3 - "$tmpl_full" "$name" "$fresh" <<'PY'
import re, sys
path, name, fresh = sys.argv[1], sys.argv[2], sys.argv[3]
with open(path, encoding='utf-8') as f:
    src = f.read()
# Rewrite only on lines that contain filename='<name>'. This way two
# different ?v= for two different files in the same template don't
# collide. The replacement updates the trailing ?v=... to the fresh hash.
new_lines = []
hits = 0
for line in src.splitlines(keepends=True):
    if f"filename='{name}'" in line:
        out, n = re.subn(r'\?v=[A-Za-z0-9._-]+', f'?v={fresh}', line)
        new_lines.append(out)
        hits += n
    else:
        new_lines.append(line)
new = ''.join(new_lines)
if new != src:
    with open(path, 'w', encoding='utf-8') as f:
        f.write(new)
    print(f"  rewrote {path}: ?v={fresh} ({hits} replacement)")
PY
done
printf "\n${G}Templates updated.${NC}\n"
