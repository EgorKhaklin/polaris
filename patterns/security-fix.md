# patterns/security-fix.md

## Trigger

- A vulnerability is identified (manual review, OWASP scan, audit
  finding, dependency CVE)
- The fix is being scoped: what code changes, what tests verify it,
  what documentation reflects the new posture

## Recipe

### 1. Classify the finding against MISSION.md

Before changing code, find which MISSION constraint (C1-C10) the
vulnerability touches:

- C1 (append-only) → audit modification path
- C2 (ZK→token NULL) → disclosure semantics path
- C3 (one active per indiv.) → uniqueness path
- C4 (atomic increment) → concurrency path
- C5 (CSP 'self') → XSS / inline-script path
- C6 (server-side disclosure) → client-trust path
- C7 (algorithm metadata) → crypto config path
- C8 (atlas hard caps) → unbounded API path
- C9 (concurrency tests use threading) → race path

If the vulnerability fits into NONE of C1-C10, it's either novel
(add a constraint) or the framing is wrong.

### 2. Map to STRIDE in DEVNOTES/threat-model.md

Find the threat row in `DEVNOTES/threat-model.md` that matches.
Update the residual-risk note when the fix lands.

### 3. Write the failing test FIRST

The test must:
- Fail on the current code
- Pass after the fix
- Stay in the suite as a regression check

For C1-C10 invariants, prefer property tests in
`test_invariants_property.py` (Hypothesis) over hand-written cases —
they generalize to inputs you didn't think of.

```python
def test_<vulnerability_name>_is_blocked(self):
    # arrange the vulnerable preconditions
    ...
    # attempt the attack
    response = self.client.post(...)
    # verify it's blocked
    self.assertEqual(response.status_code, 400)
    # verify the side-effect that SHOULD have happened didn't
    self.assertEqual(0, count_in_db(...))
```

### 4. Implement the fix

Smallest change that makes the test pass. Resist the temptation to
"also clean up" adjacent code in the same commit; small fixes are
easier to audit.

### 5. Verify the fix doesn't introduce new attack surface

Specifically check:
- Does the fix add a new code path that bypasses an existing check?
- Does the fix add a new error message that leaks information?
- Does the fix add logging that captures sensitive data?

### 6. Update docs/operator/SECURITY.md and DEVNOTES/threat-model.md

- docs/operator/SECURITY.md gets a one-line entry under the appropriate version
- threat-model.md: residual-risk note updated for the affected threat
- If the fix moves a DEFERRED threat to ADDRESSED, update both lists

### 7. Run ai-coverage.sh

```bash
./scripts/ai-coverage.sh CN     # where N is the constraint touched
```

Confirm the new test is picked up by the coverage script. If not,
either the test name doesn't match the search pattern (rename test)
or the search pattern in `ai-coverage.sh` needs updating.

### 8. CHANGELOG entry

Format:

```
### Security fix: <one-line description>

[CWE-XXX or category]. The vulnerability allowed [attack scenario].
Fixed by [implementation summary]. Test:
test_<name> in test_app.py.

Constraint reinforced: C<N>. Threat-model entry: T-<S/T/R/I/D/E><N>
status moves from [old] to [new].
```

## Pre-known gotchas

- **Don't ship a security fix without a regression test.** A fix
  without a test is half a fix; the same vulnerability returns when
  the next refactor undoes the change.

- **Don't expand fix scope.** "While I'm here, let me also fix..."
  is how security fixes become hard-to-review monsters. Scope creep
  is the enemy of audit-ability.

- **Don't fix a security issue silently.** Even a tiny fix (one-line
  CSP header) needs a CHANGELOG entry. Future-auditors need to be
  able to reconstruct the security history.

- **The fix may need to be backwards-incompatible.** If the
  vulnerability requires breaking client code to fix, document it
  loudly in CHANGELOG and bump the API version (BACKLOG: API
  versioning).

- **Don't use `if XSS_RISK: pass`-style escape hatches.** A toggle
  that disables a security control is itself a vulnerability if
  someone can flip it.

## Completion check

- [ ] Vulnerability mapped to C1-C10 (or new constraint added)
- [ ] STRIDE entry updated in DEVNOTES/threat-model.md
- [ ] Failing regression test written
- [ ] Smallest-possible fix implemented
- [ ] All existing tests still pass
- [ ] docs/operator/SECURITY.md updated
- [ ] CHANGELOG entry with constraint reference
- [ ] ai-coverage.sh shows the test counted under the right constraint
- [ ] No new code path bypasses existing checks (review yourself)
