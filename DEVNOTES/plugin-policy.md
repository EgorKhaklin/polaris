# DEVNOTES/plugin-policy.md — what Claude plugins Polaris accepts and refuses

**Origin:** session 2026-05-17 joint Architect ↔ Anti-Architect plugin
audit. Sanctum: `sanctum/2026-05-17-plugin-installation-tier2.md`.
**Audience:** future agent (Claude) considering installing a plugin
from `claude-plugins-official` or any other marketplace.
**Distinction:** this document is the **refusal list**. The accept
list lives at `~/.claude/plugins/config.json` (truth = `claude plugin list`).
This document exists so a future agent does not re-propose categories
already refused on constitutional grounds.

---

## The frame

The Claude plugin catalog is **not a neutral menu**. Each plugin in
the catalog is a temptation to integrate a third-party system, and
each integration has constitutional cost. Polaris has a
load-bearing Vocation (anti-coercion) and ten hard constraints
(C1–C10) that several whole categories of plugin directly violate.

The drift→test promotion discipline (v8.12, Architect's brief
2026-05-17 #003) applied to plugin governance: every refusal recorded
here is a class-level catch that prevents the next agent from
re-running the same analysis from scratch.

---

## Accepted (installed)

These were approved without Sanctum or via Sanctum and are running. The
authoritative list is `claude plugin list`; the entries below explain
*why* each was acceptable.

| Plugin | Tier | Reason for acceptance |
|---|---|---|
| `pyright-lsp` | 1 (no-Sanctum) | Zero-token LSP; type-checks Python (14,898-line test suite + watchers + ants). No constitutional surface touched. |
| `rust-analyzer-lsp` | 1 (no-Sanctum) | Zero-token LSP; supports `polaris_zk/` crate prepping for crates.io. No constitutional surface touched. |
| `playwright` | 2 (Sanctum-bundle 2026-05-17) | Gotcha #6 already names Playwright for Atlas E2E; first-classes the workflow. Per-session browser surface — no SaaS phone-home. |
| `chrome-devtools-mcp` | 2 (Sanctum-bundle 2026-05-17) | Local Chrome DevTools surface for `atlas-globe.js` debugging; runs against `localhost:2222`. Does not phone home; CSP (C5) unaffected because the inspector connects in-process. |
| `claude-md-management` | 2 (Sanctum-bundle 2026-05-17) | Enforces the trim discipline we just executed (672→250 lines per BIG MISSION Tier 4 #14). Class-level catch against narrative re-bloat. |
| `hookify` | 2 (Sanctum-bundle 2026-05-17) | Formalizes `pre-commit-scope-check.sh` + `ai-done.sh` step-14 as harness hooks. Follow-up integration ship will wire them; this Sanctum only installs. |

Future additions: append to this table when a plugin clears
Sanctum, with one sentence on *why it doesn't violate any refused
category*.

---

## Refused categories (constitutional, not preference)

A category being on this list means **do not propose plugins from
this category** in a future scan. If the catalog grows new plugins
fitting a refused category, they are refused on sight.

### R1 — Payments / banking
**Violates:** C10 (identity is not money).
**Examples in catalog:** `stripe`, `mercadopago`, `sumup`, `revenuecat`, `legalzoom`.
**Reasoning:** the C10 constraint is the constitutional boundary
between identity and value-transfer. The Architect's adversary walk
(`ai-architect.sh §IV`) names the "identity layer carrying monetary
payoffs" as the equilibrium-breaking failure mode. Installing a
payments plugin into the Polaris workspace is the agent-side version
of that boundary-crossing.
**Correct alternative:** build a separate repo that consumes Polaris
verification proofs over HTTP. Stripe etc. belong in that repo, not
this one.

### R2 — Surveillance / telemetry SaaS
**Violates:** Vocation (anti-coercion); threat-model surfaces T-CL-1..T-CL-5.
**Examples in catalog:** `amplitude`, `posthog`, `fullstory`, `sentry`, `datadog`, `logfire`, `dash0`.
**Reasoning:** Polaris does not phone home. The audit-of-record (C1)
lives in our own Postgres with append-only proofs and 12 schema-level
guarantees. Routing app telemetry to a third-party dashboard
inverts the trust model and creates a centralized aggregation point
that the operator does not control. Per `DEVNOTES/observability.md`:
"an operator should be able to monitor production behavior without
loading the cognitive substrate" — and without trusting a SaaS.
**Correct alternative:** `/api/metrics` JSON endpoint + operator's
own monitoring of their choice on their own hardware.

### R3 — Auth SaaS
**Violates:** self-coherence (Polaris IS the identity layer).
**Examples in catalog:** `auth0`, `vanta-mcp-plugin`.
**Reasoning:** if we use a third-party auth provider in our own
development workflow, we are admitting we don't trust the system we
are building. Beyond the optics, every secret stored at Auth0 is a
coercion target outside our threat model.
**Correct alternative:** use Polaris itself.

### R4 — Cloud providers
**Violates:** local-Docker-on-operator-hardware architecture.
**Examples in catalog:** all `aws-*` (7+ plugins), `azure*` (2+), `vercel`, `netlify-skills`, `railway`, `supabase`, `planetscale`, `neon`, `firebase`, `cloudflare`, `deploy-on-aws`, `cloud-sql-postgresql`.
**Reasoning:** Polaris is designed to run on operator hardware —
Postgres in Docker, Flask via Gunicorn, all secrets in
`/tmp/polaris-state` under operator control. A cloud-provider plugin
in the agent's hands is the on-ramp to "let me just deploy this to
AWS for you" which inverts the sovereignty model the threat model
assumes.
**Correct alternative:** `polaris-deploy.sh` to operator-controlled
hardware. The Architect's S2 Sanctum settled this.

### R5 — Productivity SaaS
**Violates:** C1 (single audit-of-record); v9.26 AppendOnlyBypass test.
**Examples in catalog:** `linear`, `asana`, `notion`, `slack`, `discord`, `intercom`, `imessage`, `telegram`.
**Reasoning:** the journal (`journal/`) + Sanctum index
(`meta/sanctum-index.md`) + CHANGELOG are the audit-of-record per C1.
Sharding state into Linear/Notion/Slack splits the record and
guarantees drift between systems. The v9.26 AppendOnlyBypass kill
test exists precisely to catch agents introducing escape hatches
around append-only.
**Correct alternative:** `ai-journal.sh decision` for in-session
captures; Sanctum for strategic decisions; CHANGELOG entry for ships.

### R6 — Redundant code-review tooling
**Violates:** AP3 (instance-level rules when class-level coverage exists); creates a second source of authority.
**Examples in catalog:** `coderabbit`, `sonarqube`, `code-review`, `pr-review-toolkit`, `greptile`.
**Reasoning:** Polaris already has `/review`, `/security-review`, and
`/ultrareview` as user-invoked skills. The pre-ship gate
(`ai-done.sh`, 15 checks, v9.28 CM-enforce) is the load-bearing
class-level review. Adding a third reviewer creates "which one is
authoritative" ambiguity and dilutes the kill-test signal.
**Correct alternative:** strengthen `ai-done.sh` checks when a new
class of defect is discovered. The simplifier skill (already
available) covers the reuse-and-quality lens.

### R8 — Internal-extraction plugins (packaging the cognitive layer)
**Violates:** T7#9 verbatim — "the strong claim is killed on insufficient evidence; the experiment is preserved; future external replication is the only way to revive the claim" (`sanctum/2026-05-16-tier-7-8-thesis-test-and-freeze-line.md`). Also AP6 (form-without-substance — scripts without the journal/sanctum/DEVNOTES they're embedded in).
**Examples (none exist; this is a refusal of a category):** `polaris-internal` plugin packaging the 39 ai-* + 31 polaris-* scripts; any "package the cognitive layer" proposal in any form (full bundle / minimal scaffold / thin reader).
**Reasoning:** the cognitive layer's discipline lives in the journal, the Sanctum index, and the DEVNOTES — not in the script files. Extracting the scripts as a plugin (even a thin reader that shells out to the operator's local repo) is revival-by-apparatus of a hypothesis we explicitly killed. The honest test of "is the cognitive layer portable" is an outside human reading MISSION.md cold and operating the system. That test cannot be moved earlier by building scaffolding. Scaffolding can only confirm a verified result or hide an unverified one.

**Revisit-gates (the ONLY triggers that justify reopening this refusal):**

1. **External cold-read returns positive.** T7#9's named "only an operator can commission this" cold-read happens and produces evidence that an outside operator successfully ran the cognitive layer in a context we didn't construct. Then the plugin would operationalize a verified capability, not test an unverified one.
2. **An actual second operator appears.** Real portability demand (collaborator, public release, multi-machine workflow VANTA actually uses) — not speculated demand. User count must change from 1 to ≥2 with documented use case.
3. **A new post-v2 arc explicitly names portability as a constraint.** Same logic as v8.74 heavy-production: a new mission can override a settled boundary, but the override must be explicit in MISSION.md / a new R-id, not implicit in "well we could now."

**Explicitly NOT a trigger:** the v9.31 freeze ending. The freeze was supporting evidence; T7#9's external-replication requirement is the load-bearing argument and survives unfreeze.

**Decided:** `sanctum/2026-05-17-polaris-internal-plugin-tier3.md` (Option D + user-config). VANTA's user-config side-channel (`~/.claude/commands/*.md` shelling to absolute polaris-repo paths) serves typing-shortcut value without violating this refusal — it is deliberately non-portable, single-operator, single-machine.

### R7 — LLM gateways / multi-provider routers
**Violates:** T-CL-3 (Sanctum prompt injection / cognitive-layer attack surface).
**Examples in catalog:** `huggingface-skills`, `outputai`.
**Reasoning:** Claude is the only LLM in the loop by design. Adding
a router (or a HuggingFace skill that may dispatch to arbitrary
hosted models) introduces a path where the cognitive layer's outputs
are influenced by a model with different alignment properties.
T-CL-3 specifically calls out the prompt-injection surface; broadening
the model surface multiplies it.
**Correct alternative:** if a non-Claude model is genuinely needed
for a specific task, the operator can run it outside the cognitive
loop and feed results in by hand.

---

## Not-yet-refused but watch-worthy

These plugins are not on the refusal list, but a future agent
proposing them should explicitly walk through whether they fit a
refused category in disguise:

- **`semgrep`** — our `security_watcher.py` and `ai-done.sh` cover the
  same surface. Could complement; could duplicate. Requires an
  Architect/Anti-Architect joint pass before install.
- **`context7`** / **`exa`** / **`firecrawl`** / **`brightdata-plugin`** —
  web-research tools. WebSearch + WebFetch are already available;
  adding more requires the AP3 check.
- **`mongodb`** / **`clickhouse`** / **`cockroachdb`** / **`pinecone`** /
  **`qdrant-skills`** / **`zilliz`** — alternative DBs. Polaris is
  Postgres-only by design (Architect: "no NewSQL until 10M rows and a
  cause we can name"). Refusal lives in `DEVNOTES/atlas-scaling.md`.

---

## How to extend this document

If you (future Claude) find yourself doing a fresh plugin-catalog
audit, **read this file first**. If the new candidate fits an
existing R-class, refuse without re-running the analysis. If it
genuinely doesn't fit, run the Architect ↔ Anti-Architect joint
pass and append either to the Accepted table (with reason) or to
the Refused categories (with new R-id).

The AP2 (Sanctum-overuse) signal applies to plugin-shopping the same
way it applies to feature-shopping: cap to one bundle Sanctum per
plugin pass.
