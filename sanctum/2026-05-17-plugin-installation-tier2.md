# Sanctum: plugin-installation-tier2

**Date:** 2026-05-17
**Petitioner:** agent (Claude, Opus 4.7)
**Principal:** VANTA
**Trigger:** MEDIUM-risk propose-and-wait — bundle install of four Claude plugins that touch test surface, browser-debug surface, and pre-commit gate surface
**Risk class:** MEDIUM
**Status:** CLOSED
**Architect brief ID:** n/a — surfaced live in chat 2026-05-17 from full cognitive-architecture scan (ai-prime + ai-swarm-health + ai-hydra + ai-meta + ai-architect + ai-anti-architect + ai-foresight + ai-coherence)

---

## I. The Matter

Install four plugins from `claude-plugins-official` as one bundle: `playwright`, `chrome-devtools-mcp`, `claude-md-management`, `hookify`. Decided together rather than four separate Sanctums to avoid worsening the AP2 (Sanctum-overuse) signal the Anti-Architect already flagged this cycle.

## II. Preparation

- Architect brief: (live, in-chat — joint Architect ↔ Anti-Architect brief; not a stored `arch-*` ID)
- Proposal draft: (none — plugin governance, not a code R-id proposal)
- Alignment audit:
  - Tier 1 (`pyright-lsp`, `rust-analyzer-lsp`) already installed without Sanctum — zero-token, zero-vocation-cost LSPs.
  - Refusal list for entire catalog being written to `DEVNOTES/plugin-policy.md` in same session — covers payments (C10), surveillance SaaS (Vocation), cloud providers (architecture), auth SaaS (self-coherence), productivity SaaS (C1 AppendOnlyBypass), redundant code review (AP3), LLM gateways (T-CL-3).
  - AP2 candidate already firing (60 sanctums / 7 days / 0 ships) — bundling four candidates into one Sanctum is the defense move.
- Blast radius (if approved):
  - `~/.claude/plugins/` registers four more plugins (user scope).
  - Per-ship gate (`ai-done.sh`) may gain a hookify-managed pre-commit step in a follow-up ship — not in this Sanctum.
  - No `polaris_*` source modification. No constitutional surface touched.
- Tests planned: 0 in this Sanctum. Follow-up Hookify integration ship would add structural invariants under `TestSanctum_PluginTier2_2026_05_17` if it materializes.

## III. Alternatives considered

1. **Four separate Sanctums (one per plugin).** Rejected: amplifies AP2 (Sanctum-overuse) which is already a live signal this cycle.
2. **Install all four directly without Sanctum (like Tier 1).** Rejected: `playwright` and `chrome-devtools-mcp` add browser-side surface that has CSP implications (C5); `hookify` couples pre-commit gates to harness rather than shell scripts; `claude-md-management` could enforce trim rules that conflict with our just-completed BIG MISSION T4#14 trim (672→250). Each warrants explicit operator decision.
3. **Defer all four pending more usage data.** Rejected: opportunity cost is real — Atlas globe debugging today is print-and-reload; Playwright tests are already gotcha-#6-aware but ad-hoc.
4. **Build internal equivalents.** Rejected as larping: external tools already exist; the cognitive layer should not duplicate them. (The Tier 3 `polaris-internal` plugin packages our cognitive layer; it does not rebuild Playwright.)

## IV. Recommendation

Install all four plugins as a bundle in this session:

| Plugin | Anchor reason | Concrete near-term use |
|---|---|---|
| `playwright` | Pre-known gotcha #6 names Playwright already; makes the workflow first-class | Atlas globe E2E + login-flow regression coverage |
| `chrome-devtools-mcp` | Atlas globe (`atlas-globe.js`) debugging is currently print-and-reload | Visual debugging of WebGL globe + reticle; aligns with v9.27 cold-read step-4 test-validation discipline |
| `claude-md-management` | Just trimmed CLAUDE.md 672→250 per Tier 4 #14; enforces what we already chose | Prevents narrative re-bloat |
| `hookify` | Formalizes `pre-commit-scope-check.sh` + `ai-done.sh` step-14 as harness hooks | Pre-commit gates stop relying on memory |

Anti-Architect concurs **only as a bundle**; refuses to debate four individually.

## V. What's needed from VANTA

One of:

- **A (recommended):** approve the bundle as-is. Agent runs four `claude plugin install` commands, verifies with `claude plugin list`, closes Sanctum.
- **B:** approve a subset (name which). Agent installs subset, records the omissions and their reasons in Decision section.
- **C:** reject entirely. Agent records the reasons in Decision section so the catch is preserved for future scans.

## VI. Decision

**VANTA: Option A — approve the bundle as-is.** (Verbatim: "proceed with the recommendation", 2026-05-17.)

## VII. Outcome

All four plugins installed successfully (`claude plugin install <name>@claude-plugins-official`, scope: user, all status enabled). `claude plugin list` now shows 6 enabled plugins (Tier 1 + Tier 2).

- `playwright@claude-plugins-official` — version unknown, enabled
- `chrome-devtools-mcp@claude-plugins-official` — version 0.22.0, enabled
- `claude-md-management@claude-plugins-official` — version 1.0.0, enabled
- `hookify@claude-plugins-official` — version unknown, enabled

`DEVNOTES/plugin-policy.md` Accepted table updated with all four entries and per-plugin acceptance reasoning.

Journal: `journal/2026-05-17.md` (decision entry logged via `ai-journal.sh decision`).
Sanctum index: this entry prepended.
ai-link-check: 629 → (re-verify after this close).

Not a ship per CLAUDE.md ship sequence (no `__version__.py` bump, no CHANGELOG entry, no test added) — this is a workspace governance decision recorded as a Sanctum. The follow-up *integration* work (wiring hookify into `ai-done.sh` step-14, adding Playwright Atlas-globe E2E suite) will be separate ships with their own version bumps and test classes.

Tier 3 (`polaris-internal` recursive plugin) explicitly deferred to its own HIGH Sanctum; not opened in this session per AP2 (Sanctum-overuse) defense.
