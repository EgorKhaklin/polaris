#!/bin/bash
# =============================================================================
# scripts/ai-journal.sh
#
# Episodic memory layer. Appends a structured journal entry to journal/ that
# captures what happened in this session, what decisions were made, what
# worked, what didn't, and what should be remembered.
#
# Design: a brain consolidates episodic memory during sleep (hippocampal
# replay). I don't sleep — I die at the end of every conversation. So the
# consolidation has to be EXPLICIT and CHEAP. This script makes it cheap.
#
# Usage:
#     ai-journal.sh start "task description"     # mark session start
#     ai-journal.sh decision "what + why"        # log a decision
#     ai-journal.sh learning "what was learned"  # log a new gotcha/insight
#     ai-journal.sh end                          # close the session entry
#
# Each call appends to today's journal file (or creates one). The file is
# plain markdown, grep-friendly, and consumed by ai-recall.sh.
# =============================================================================

set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
JOURNAL_DIR="$ROOT/journal"
mkdir -p "$JOURNAL_DIR"

# One file per day. Multiple sessions in a day get separated by SESSION marks.
DATE=$(date +%Y-%m-%d)
TIME=$(date +%H:%M)
ENTRY_FILE="$JOURNAL_DIR/$DATE.md"

# Initialize with a header if first write of the day
if [ ! -f "$ENTRY_FILE" ]; then
    cat > "$ENTRY_FILE" <<EOF
# Journal — $DATE

Episodic memory for this date. Each session opens with "## SESSION
HH:MM" and closes with "## END HH:MM". Decisions and learnings are
flat-list under their session.
EOF
fi

CMD="${1:-}"

case "$CMD" in
    start)
        TASK="${2:-(unstated task)}"
        cat >> "$ENTRY_FILE" <<EOF

## SESSION $TIME — $TASK

EOF
        echo "[journal] session opened in $ENTRY_FILE"
        ;;

    decision)
        TEXT="${2:-(unspecified)}"
        echo "- **decision** $TIME — $TEXT" >> "$ENTRY_FILE"
        echo "[journal] decision logged"
        ;;

    learning|gotcha)
        TEXT="${2:-(unspecified)}"
        echo "- **learning** $TIME — $TEXT" >> "$ENTRY_FILE"
        echo "[journal] learning logged (consider promoting to DEVNOTES/known-gotchas.md if recurrent)"
        ;;

    bug)
        TEXT="${2:-(unspecified)}"
        echo "- **bug** $TIME — $TEXT" >> "$ENTRY_FILE"
        echo "[journal] bug logged"
        ;;

    note)
        TEXT="${2:-(unspecified)}"
        echo "- **note** $TIME — $TEXT" >> "$ENTRY_FILE"
        echo "[journal] note logged"
        ;;

    end)
        cat >> "$ENTRY_FILE" <<EOF

## END $TIME

EOF
        echo "[journal] session closed"
        ;;

    show)
        # Show today's journal
        cat "$ENTRY_FILE"
        ;;

    tail)
        # Last 30 lines
        tail -30 "$ENTRY_FILE"
        ;;

    *)
        cat <<EOF
ai-journal.sh — episodic session log

Usage:
    ai-journal.sh start    "task description"
    ai-journal.sh decision "what + why"
    ai-journal.sh learning "what was learned"
    ai-journal.sh bug      "what broke + how"
    ai-journal.sh note     "anything else"
    ai-journal.sh end
    ai-journal.sh show     # print today's journal
    ai-journal.sh tail     # last 30 lines

Journal lives at: $ENTRY_FILE
EOF
        ;;
esac
