# Sanctum: changelog-archive-extension

**Date:** 2026-05-17
**Petitioner:** agent (Claude, Opus 4.7)
**Principal:** VANTA
**Trigger:** HIGH — amends v9.24's "byte-frozen archive" claim (an AoR primitive). Pre-authorized by VANTA 2026-05-17: "have the changelog at 10 latest ships, the other ones move to the archive changelog."
**Risk class:** HIGH (touches AoR claim)
**Status:** CLOSED
**Architect brief ID:** n/a — surfaced from cap-relaxation friction in v9.34 + v9.36 + the "ripe" note in ROADMAP

---

## I. The Matter

v9.24 compressed CHANGELOG.md from 17,946 lines to a "last 10 ships" curated index, with the older history preserved byte-identical at `archive/CHANGELOG-FULL.md`. The v9.24 entry's last paragraph reads: *"no entry was edited or deleted in the v9.24 compression — the v8.20 audit-of-record discipline holds."*

That claim has been operationally consistent so long as no NEW ships were trimmed FROM CHANGELOG.md. But as v9.25+ ships accumulated, the "last 10" convention required trimming v9.24+ entries out of CHANGELOG.md — and the archive couldn't grow without amending the byte-frozen claim. v9.34 caught the tension (lost v9.24 entry briefly during a trim, restored it). v9.36 hit the convention's headroom cap (13 ships at the 12 limit) and relaxed to 14. The ROADMAP captured the work as "NOW RIPE."

**The Matter:** amend the v9.24 byte-frozen claim to allow APPENDS (no edits/deletions) to `archive/CHANGELOG-FULL.md`. Move CHANGELOG.md entries past the last-10 into the archive under a clearly-marked "post-v9.24 section." Restore the test cap from 14 → 10 + 1 headroom for the in-flight current ship.

## II. Preparation

- Architect brief: n/a (surfaced live from CHANGELOG cap pressure)
- Proposal draft: none — convention amendment + bulk-move ship
- Alignment audit:
  - **v8.20 AoR discipline**: preserved. APPENDS to the archive don't EDIT or DELETE existing rows; they only add new ones. Past v9.x entries remain byte-identical in their new archive location.
  - **v9.24 claim text**: the phrase "no entry was edited or deleted" technically permits appends. But the spirit of "byte-frozen" arguably forbids any change to the archive's content. This Sanctum amends both the literal AND the spirit: archive grows by append-only after v9.38.
  - **AP2 status**: this Sanctum was opened mid-arc which would normally worsen AP2. Pre-authorized by VANTA in the same turn that requested it ("have the changelog at 10 latest ships, the other ones move"), so it counts toward the active arc, not a separate Sanctum-burst. Net AP2 effect: neutral.
  - **Apparatus ratio**: this Sanctum is APPARATUS (governs how CHANGELOG flows). Adds one more apparatus Sanctum. The mitigation: this Sanctum REPLACES the v9.34/v9.36 cap-relaxation pattern with the proper fix, so the friction stops accumulating.
- Blast radius:
  - `CHANGELOG.md`: 4 entries removed (oldest 4: v9.27, v9.26, v9.25, v9.24)
  - `archive/CHANGELOG-FULL.md`: grows by ~4 entries + section header
  - `polaris_web/test_structural_invariants.py`: `test_changelog_compressed` cap 14 → 11 (10 + 1 for in-flight ship)
  - `ROADMAP.md`: archive-extension entry moves to "done"
- Tests planned: 3 invariants in TestWave38V938 (archive grew; archive section marked; cap restored)

## III. Alternatives considered

1. **Continue relaxing the cap each ship.** The pattern v9.34 → v9.36 set. Cost: cap-ratcheting indefinitely, narrative bloat in CHANGELOG.md, no actual archive growth. Rejected: locally-valid-globally-a-ratchet pattern named by v9.29.
2. **Move entries WITHOUT amending the v9.24 claim** (just stretch the literal interpretation of "no edit or deletion"). Rejected: lawyering an AoR claim is exactly the AP-pattern the discipline catches.
3. **This Sanctum — explicit amend + move (recommended).** Honest. Archive grows; v9.24 claim updated; cap restored.
4. **Just delete v9.24-v9.27 entries.** Rejected: violates AoR. The v9.34 in-flight catch was a near-miss of exactly this failure mode.

## IV. Recommendation

Execute the move + amendment in this single Sanctum-decided ship (v9.38):

1. Append entries v9.27, v9.26, v9.25, v9.24 (in that descending order, matching CHANGELOG.md's existing newest-first layout) to `archive/CHANGELOG-FULL.md` under a new section header: `## Post-v9.24 ships (appended per Sanctum 2026-05-17-changelog-archive-extension)`.
2. Remove those 4 entries from `CHANGELOG.md`. Result: 10 ships (v9.37 ... v9.28). Adding v9.38 ship entry takes it to 11; matches the new cap.
3. Amend `test_changelog_compressed` cap: 14 → 11 (last-10 + 1 in-flight headroom).
4. Update ROADMAP entry from "NOW RIPE" to "DONE in v9.38."
5. TestWave38V938 invariants: archive's post-v9.24 section exists; v9.24 entry present in archive; cap = 11; v9.27/v9.26/v9.25/v9.24 NOT in CHANGELOG.md.

## V. What's needed from VANTA

Pre-authorized: "have the changelog at 10 latest ships, the other ones move to the archive changelog." Agent executes directly.

## VI. Decision

**VANTA: ship the recommendation as v9.38.** (Pre-authorized 2026-05-17 in chat as part of the close-out arc.)

## VII. Outcome

**v9.38 SHIPPED 2026-05-17.** Execution complete:

- v9.24, v9.25, v9.26, v9.27 moved byte-identical from CHANGELOG.md
  to new `## Post-v9.24 ships (appended per Sanctum
  2026-05-17-changelog-archive-extension)` section in
  `archive/CHANGELOG-FULL.md` (200 lines / +6KB archive growth).
- `CHANGELOG.md` reduced to 10 stable ships (v9.37 → v9.28) + this
  v9.38 ship entry = 11 total.
- `test_changelog_compressed` cap restored 14 → 11 (10 + 1 in-flight).
- ROADMAP archive-extension entry transitioned "NOW RIPE" → "DONE".
- TestWave38V938 × 5 invariants pin the move + amendment.
- Sanctum index entry prepended at top of `meta/sanctum-index.md`.

**Amendment text (now binding):** archive grows APPENDS-only; no
edits or deletions of existing rows. The v9.24 byte-frozen claim
applies to the pre-v9.24 content section; the post-v9.24 section
follows the same discipline going forward.

**The pattern future ships follow:** when CHANGELOG.md ship count
exceeds 11, agent moves the oldest entry to the post-v9.24 archive
section (byte-identical, no edits) and the ship CHANGELOG entry
replaces it. test_changelog_compressed catches deviation.
