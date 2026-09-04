## Motivation

<!-- The need this change answers. Link the issue or proposal. -->

## Change

<!-- What changed, in the order a reviewer should read it. -->

## Blast radius

<!-- Tables, routes, scripts, documents and checks touched; what an operator must do on upgrade; anything reopened from the roadmap. -->

## Constraints

<!-- Which of C1 to C10 this touches and how each stays enforced at the database level, or "none". -->

## Test discipline

- [ ] `python3 -m polaris_checks.run` reports READY
- [ ] `./scripts/polaris-test.sh` passes (the DB-backed suites)
- [ ] `./scripts/polaris-link-check.sh --ci` resolves every reference
- [ ] New behaviour carries a test that fails without it, or a `check_*` with a detection test
- [ ] `polaris_web/__version__.py`, `deploy/helm/polaris/Chart.yaml` and CHANGELOG.md are updated in this PR
- [ ] Documentation that describes the changed behaviour is updated in this PR
