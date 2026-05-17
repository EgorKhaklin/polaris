# Sanctum: polaris-internal-plugin-tier3

**Date:** 2026-05-17
**Petitioner:** agent (Claude, Opus 4.7)
**Principal:** VANTA
**Trigger:** HIGH-risk Sanctum — recursive plugin packaging the cognitive layer itself; surfaced from joint plugin audit 2026-05-17 (Tier 1 + Tier 2 already shipped this session)
**Risk class:** HIGH
**Status:** CLOSED
**Architect brief ID:** n/a — surfaced live in chat; recursive scope means standard arch-* ID does not capture it (the cognitive layer being packaged is the producer of arch-* IDs)

---

## I. The Matter

Build a `polaris-internal` Claude plugin that packages Polaris's own cognitive layer (39 `ai-*.sh` + 31 `polaris-*.sh` scripts + the meta/ directory + a curated subset of DEVNOTES) as a loadable plugin. The intent: a fresh operator on a new machine, working on a different project or a fresh Polaris checkout, can `claude plugin install polaris-internal` and immediately have `/ai-prime`, `/ai-architect`, `/ai-sanctum`, etc. available.

This is the **recursive** move. The cognitive layer that produced this Sanctum would itself become a distributable artifact.

## II. Preparation

- Architect brief: this Sanctum is the brief.
- Proposal draft: (none — no R-id; cognitive-layer scope, not a feature)
- Alignment audit:
  - **Tier 7 #9 (publish-or-kill)** in `sanctum/2026-05-16-tier-7-8-thesis-test-and-freeze-line.md` was resolved as HYPOTHESIS-NOT-VERIFIED. The hypothesis being tested was *"the cognitive layer is portable and learnable by other operators."* This Tier 3 plugin is the experimental apparatus that would actually test that hypothesis — it converts the question from speculation to falsifiable.
  - **AP2 status:** at session start, 60 sanctums/7d/0 ships. After this session: 63/7d/0 ships (Tier 1 directly, Tier 2 closed, Tier 3 opens this entry). The Sanctum-overuse signal is now louder. Opening this Sanctum at all is a cost item that needs naming.
  - **Apparatus-dominant ratio:** 14 core / 48 apparatus / 0.29 — already firing "cut deeper." A polaris-internal plugin is apparatus by definition (it does not introduce a new C-invariant, AoR table, or vocation primitive). Shipping it would push the ratio worse.
  - **Freeze line:** v9.30 is the constitutional freeze per `sanctum/2026-05-16-tier-7-8...`. v9.31 = mechanical freeze-line verification. Building the plugin would be at minimum a v9.32+ ship, post-freeze. The freeze allows hardening/measurement/cold-read-only. **Is plugin-packaging hardening, measurement, or cold-read?** Strongest case: it's cold-read (T7#9 referent). Weakest case: it's new scope (extracts portability claim into shippable form).
  - **Vocation check (anti-coercion):** the cognitive layer encodes opinionated discipline (Sanctum protocol, AP1–AP8, 22-pattern catalog, predicates). Packaging it means **the discipline becomes copyable** — a different operator can run it in a non-Polaris context where C1–C10 are not load-bearing. The opinionated parts may not survive translation. This is the load-bearing concern.
- Blast radius (if approved at full scope):
  - New top-level directory: `polaris-internal-plugin/` containing `.claude-plugin/plugin.json` + `commands/` (70 wrappers, one per script) + `skills/` (curated subset of DEVNOTES surfaced as skills) + `README.md` + `LICENSE`.
  - Distribution path adds attack surface: GitHub repo, marketplace submission, or operator-local-only.
  - Version-coupling: every `ai-*` script bump requires a plugin version bump or the bundled version drifts.
  - Tests: new structural invariants in `TestSanctum_PolarisInternalPlugin_2026_05_17_<vNN>` covering "every ai-* script has a corresponding plugin command" + "plugin.json schema valid" + "no script references absolute polaris-repo paths".
- Tests planned: ~6–10 invariants depending on Option chosen.

## III. Alternatives considered

1. **Option A — Full package (heavy):** bundle all 70 scripts + meta/ + curated DEVNOTES into a self-contained plugin. Plugin works without a Polaris checkout.
   - **Strength:** maximally testable portability claim (T7#9 closure).
   - **Weakness:** maximum drift surface; the cognitive layer is journal-coupled (the journal/ is the audit-of-record for the discipline that gives the scripts meaning). A package without journal/ is "scripts only, brain removed" — the AP6 (form-without-substance) risk in its clearest form.
   - **AP cost:** AP6 high, AP3 moderate (instance-level commands when class-level discipline doesn't transfer).

2. **Option B — Minimal scaffold (light):** bundle only `ai-prime`, `ai-status`, `ai-help`, `ai-journal` + a `BOOTSTRAP.md` skill that instructs operator to clone the polaris repo if they want the full cognitive layer.
   - **Strength:** preserves the "the discipline is the repo, not the scripts" invariant.
   - **Weakness:** the plugin becomes a 4-script README-pointer. Genuine question: is this worth a plugin at all, or just a doc link?
   - **AP cost:** AP1 moderate (cargo-cult risk — operator runs ai-prime in a non-Polaris context and gets meaningless output).

3. **Option C — Thin reader (most honest):** plugin contains zero bundled scripts. Plugin exposes commands like `/polaris-prime` that **shell out to `$POLARIS_REPO/scripts/ai-prime.sh`** at runtime. Plugin enforces presence of polaris repo via env var; refuses to run without it.
   - **Strength:** zero drift (scripts always come from the operator's repo). No "removed brain" risk. The plugin is *purely a UX layer* over a real Polaris checkout.
   - **Weakness:** does not test the portability hypothesis at all — operator still needs the repo. Closes T7#9 only weakly.
   - **AP cost:** very low. Honest scope match.

4. **Option D — Defer indefinitely.** No polaris-internal plugin. T7#9 stays HYPOTHESIS-NOT-VERIFIED; the operator who wants the cognitive layer clones the repo.
   - **Strength:** lowest cost; respects AP2 (Sanctum-overuse), apparatus-dominant ratio, and freeze line.
   - **Weakness:** leaves a load-bearing capability un-extracted. The cognitive layer remains permanently coupled to this one repo.
   - **AP cost:** AP4 risk (declining to ship the thing that would test the claim — symmetric to "always shipping" being AP3, "never shipping" is its inverse).

5. **Option E — Defer to external cold-read.** Open the actual cold-read VANTA noted at T7#9 ("only an operator can commission this — see T7#9 decision"). Let the cold-reader tell us whether portability is real. **Only after** the cold-read returns a result, decide between A/B/C/D.
   - **Strength:** uses external referent (the protocol Anti-Architect taught us in `sanctum/2026-05-16-v9-29-constitution-sanctum-cm.md` — "the operator's outside-check is the only thing that catches locally-valid-globally-a-ratchet patterns").
   - **Weakness:** the cold-read costs real human time and money. May never happen.

## IV. Recommendation

**Joint recommendation: Option C (thin reader) with Option E (external cold-read) as the strict sequencing requirement.**

The Architect would naturally favor A (most ambitious extraction). The Anti-Architect would naturally favor D (defer; respect freeze). C+E is the joint resolution that:

- **Honors the freeze** (Option C is genuinely hardening/measurement, not new scope — it's a UX layer over scripts that already exist).
- **Honors AP2** (one bundled Sanctum, not separate sanctums for plugin-build + plugin-test + plugin-publish).
- **Honors the external-referent protocol** (Option E sequences cold-read FIRST; we do not get to mark T7#9 "verified" by building the artifact and self-evaluating).
- **Honors AP6** (Option C cannot be form-without-substance because there is no bundled form — everything resolves to the operator's real repo).
- **Honors the apparatus ratio** (Option C adds minimal new apparatus because the plugin is a thin shim, not 70 new commands).

**The cost of the recommendation:** if VANTA never commissions the cold-read, Option C ships and the portability claim remains untested. This is acceptable — Option C is still net-useful as a UX improvement (faster `/polaris-prime` than `cd ~/desktop/polaris && ./scripts/ai-prime.sh`) even if T7#9 stays HYPOTHESIS-NOT-VERIFIED.

**Anti-Architect dissent recorded:** Anti-Architect would prefer D outright. The dissent is "the cognitive layer is not actually portable in a meaningful sense — the discipline lives in the journal/sanctum/DEVNOTES, not in the script files; a thin-reader plugin masks this by giving the operator a `/polaris-prime` command they can invoke without ever reading MISSION.md." This dissent should be carried forward into the implementation: the thin-reader's first action on any command should be a hard check that `MISSION.md` exists and was read this session, or the command refuses.

## V. What's needed from VANTA

One of:

- **C+E (recommended):** approve Option C build (thin reader) AND commit to commissioning the external cold-read before we close T7#9. Agent builds the thin-reader plugin as v9.32 (post-freeze, justified as hardening); marks T7#9 status as "experimental apparatus built; awaiting cold-read."
- **C-only:** approve Option C build without the cold-read commitment. T7#9 stays HYPOTHESIS-NOT-VERIFIED indefinitely. Agent ships the thin reader as v9.32; records the un-tested portability claim as a permanent open item.
- **A:** approve Option A (full package). Agent acknowledges higher AP6/AP3 risk; ships as v9.32+ with the new test class covering form-vs-substance invariants.
- **B:** approve Option B (minimal scaffold). Lightest ship; the plugin is a 4-script README-pointer.
- **D (Anti-Architect's preferred):** decline all. No plugin. T7#9 stays HYPOTHESIS-NOT-VERIFIED; the cognitive layer stays repo-bound. Agent records the decision in MISSION.md as a permanent boundary.
- **E-only:** commission the cold-read first. Defer the plugin question entirely until cold-read returns. Agent records "polaris-internal plugin deferred pending cold-read" and stops.

## VI. Decision

**VANTA: Option D — no plugin (with user-config side-channel).** (Confirmation 2026-05-17 in chat: "after the unfreeze you still think D+user-config is the best move?" → agent's revisited answer: yes, T7#9's external-replication requirement survives the freeze; freeze dissolution is not a revival trigger; only positive cold-read / real second operator / new post-v2 arc would justify reopening. VANTA: "proceed with the recommendations.")

The petitioner's initial recommendation (C+E thin-reader-plus-cold-read) was retracted on re-anchoring against T7#9 verbatim: *"the strong claim is killed on insufficient evidence; the experiment is preserved; future external replication is the only way to revive the claim."* Building an internal artifact to test the killed claim is revival-by-apparatus, not revival-by-evidence — the v9.29-Sanctum-named locally-valid-globally-a-ratchet pattern. The Anti-Architect's dissent in §IV ("the discipline lives in the journal/sanctum/DEVNOTES, not in the script files") is upheld as the controlling argument.

## VII. Outcome

**Inside Polaris:** no plugin built. No version bump. No CHANGELOG entry. No new apparatus. R8 (internal-extraction plugins) added to `DEVNOTES/plugin-policy.md` covering this and any future "package the cognitive layer" proposal; three explicit revisit-gates recorded so future agents do not treat unfreeze itself as a trigger.

**Outside Polaris (user-config, not a ship):** 8 user-level slash commands written to `~/.claude/commands/` for VANTA's typing convenience:
- `/prime` → `bash /Users/vanta/desktop/polaris/scripts/ai-prime.sh`
- `/status`, `/architect`, `/anti-architect`, `/sanctum`, `/journal`, `/hydra`, `/done`

Each is a 3-line markdown file with hardcoded absolute path; not portable; not testable as the portability hypothesis (deliberately). This is a developer-environment customization for VANTA specifically. Cleanup if Polaris ever moves: `rm ~/.claude/commands/*.md`.

**Three revisit-gates** (recorded in R8 of `DEVNOTES/plugin-policy.md`):
1. External cold-read returns positive (T7#9 revival condition met).
2. An actual second operator appears (real portability demand, not speculated).
3. A new post-v2 arc explicitly names portability as a constraint (mission override).

**What stays true:** the honest test of "is the cognitive layer portable" is an outside human reading MISSION.md cold and operating the system. That test cannot be moved earlier by building scaffolding. Scaffolding can only confirm a verified result or hide an unverified one.

**Signal effects after close:**
- T7#9: HYPOTHESIS-NOT-VERIFIED honored (no internal revival attempt).
- Apparatus ratio (0.29, "cut deeper"): not worsened by this Sanctum (no apparatus added).
- AP2 (Sanctum-overuse, 63/7d/0 ships): this Sanctum closes with no ship → trajectory can start declining.
- Future agent: reads R8, doesn't re-litigate without one of the three triggers firing.

Journal: `journal/2026-05-17.md` decision entry.
Sanctum index: entry prepended at top of newest-first index.
ai-link-check: re-verified post-close.
