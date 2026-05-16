# proposals/R8-3-oidc-integration.md

**Risk class:** HIGH (explicit human approval required, with constraint analysis)
**Mission link:** Done-list item 13
**Status:** PROPOSED — explicit human approval needed; constraint analysis below

## Problem

Production deployments need to integrate with an external IdP
(GitHub OAuth, Google Workspace, Keycloak, Okta) rather than use
local password auth. Per `MISSION.md`, this is item 13 of the
done-list.

## Why HIGH risk

OIDC integration is HIGH risk because:

1. **Delegates trust.** Polaris currently controls auth end-to-end.
   OIDC means "trust this token from someone else." If the IdP is
   compromised or misconfigured, Polaris's auth is too.

2. **Touches the security-critical path.** Bugs here let attackers
   skip auth entirely. Hard to test exhaustively.

3. **Increases attack surface.** OAuth callback handlers, JWKS
   fetch, token caching — all new attack vectors.

4. **May or may not violate constraint C5 (CSP).** If the IdP redirect
   page must inline scripts, CSP becomes non-trivial.

## Constraint analysis

For each MISSION.md hard constraint, how does R8-3 affect it?

| Constraint | Effect | Mitigation |
|---|---|---|
| C1 append-only | Unchanged | OIDC events should land in AuthAuditLog |
| C2 ZK→token NULL | Unchanged | Auth is orthogonal to verification disclosure |
| C3 one active per indiv. | Unchanged | Individuals are not AppUsers |
| C4 atomic increment | Possibly relaxed | OIDC removes failed_login_count usage; the column persists for password fallback |
| C5 CSP 'self' | **AT RISK** | OIDC redirect handlers may need exceptions; mitigation: OIDC popup runs on the IdP's domain, not Polaris. Verify before merge. |
| C6 disclosure server-side | Unchanged | OIDC affects auth, not verification |
| C7 algorithm metadata | Unchanged | OIDC uses its own JWT signing; not stored in CryptographicAlgorithm |
| C8 atlas hard caps | Unchanged | |
| C9 concurrency tests | Unchanged | |
| C10 identity ≠ money | Unchanged | OIDC affects operator auth, not identity tokens |

**Net:** C5 is the only constraint at risk; the implementation must
verify CSP doesn't require relaxation.

## Recommended approach

**Opt-in via env var.** Password auth remains the default; a new
`POLARIS_AUTH_BACKEND=oidc` switches to OIDC. Both backends share
the AppUser table (OIDC users are auto-provisioned on first login,
linked to an existing AppUser by email match if configured).

Use `authlib` for the OIDC client — battle-tested, minimal API.

Phased rollout:
1. Phase 1: GitHub OAuth (single IdP, simple case)
2. Phase 2: Generic OIDC (support Keycloak, Okta, etc.)
3. Phase 3: Optional: WebAuthn / passkey support (BACKLOG)

Alternative considered: SAML. Rejected: SAML is heavyweight, harder
to test, and the deployment targets (small-to-medium agencies) don't
typically have SAML IdPs.

## What this requires from you

This is HIGH risk. I am not executing it autonomously. To proceed:

1. **Explicit approval** that OIDC integration is desired now (vs
   waiting until production deployment is closer).
2. **Decision** on which IdPs are first-class: GitHub-only, generic
   OIDC, or both?
3. **Decision** on auto-provisioning: should an OIDC login auto-
   create an AppUser, or require pre-existing username match?
4. **Acknowledgment** of the C5 risk: implementation must verify
   no CSP relaxation is needed.

A proposal of this magnitude is also a candidate for a separate
branch, with feature-flag rollout, rather than being merged into
main directly. I'd suggest implementing it on a branch and
merging only after staging-environment validation.

## What this does NOT do

- Does not remove password auth (compatibility preserved)
- Does not change the AppUser schema (OIDC fields are added optionally)
- Does not affect identity tokens, verifications, or any non-auth path
