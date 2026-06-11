# Changelog (recent ships)

This file is the curated record of Polaris's recent ships. The complete
ship-by-ship history is preserved in the git log.

---

## v9.144 — 2026-06-11 (Atlas console rework: full-viewport command surface)

The Atlas was a 700px-capped globe widget floating inside the 1480px content
column; on a large display most of the screen was empty page background. It
is now a true full-viewport console. Lighthouse (desktop): a perfect
100 perf / 100 a11y / 100 best-practices / 100 SEO with CLS 0 (up from 98
perf); 503 web + 64 CLI green; verified in the browser at 2560, 1440, and
390 widths.

- **Layout: command bar / stage + dock / status bar.** `body-atlas` unlocks
  full bleed (no content max-width, footer hidden, page does not scroll;
  the masthead widens to align with the console edges). All controls
  consolidate into ONE command-bar row (view, window, modifiers, context,
  zoom, spin/reset, LIVE) instead of two stacked toolbar rows.
- **The globe is sized by its stage box, no pixel cap.** The stage is
  flex:1 of the viewport; `baseRadius = min(w,h)/2` so a 5K display gets a
  display-sized globe, not a 700px disc. A ResizeObserver re-measures and
  refetches when the stage box changes (dock stacking, flash messages),
  not just on window resize.
- **The node console no longer covers the globe.** It docks beside the
  event feed in a tabbed right dock (Event Feed / Node Console); selecting
  a reticle auto-switches the dock to the console. The feed gets real
  width (clamp 320px..460px) instead of a cramped 320px rail.
- **Heading/pitch/zoom readouts and the activity histogram move to a
  bottom status bar** alongside the classification banner and the Z-clock;
  the stage keeps only the two HUD clusters that matter at a glance
  (tokens/anomalies, PQ/ZK). Inline style attributes on the HUD are gone
  (hud-stack-gap / hud-label-tight classes).
- **Dead v8-era layout CSS removed** (god-view shell, god-rail,
  notification-rail, globe-command, the old fullbleed negative margins and
  their media queries); responsive now stacks stage-over-dock below 1100px
  and restores page scroll there.
- All pinned markup survives (atlas-id-strip OPERATIONAL, atlas-fullbleed,
  atlas-globe-data, HUD signal texts, Event Feed, OPERATIONAL ATLAS), every
  data-atlas-* hook is unchanged, and the role-crawler suite stays green.

## v9.143 — 2026-06-11 (the Atlas becomes fully operational + a role-gate/alignment sweep, proven by crawler tests and Lighthouse)

A production-grade pass over the whole UI with the proof to back the words.
Lighthouse (desktop): landing 100/100/100/100, dashboard 100/100/100/100,
atlas 98 perf / 100 a11y / 100 best-practices / 100 SEO. Suites: 503 web +
64 CLI green, 68 checks, 65 detection tests.

- **The Atlas now ships data on first load.** The default time window was
  24H, but the notional events are months old, so the globe rendered EMPTY
  on every first visit; the default is now ALL (live deployments narrow it).
  An empty viewport explains itself with a hint chip instead of silently
  showing nothing, and a fetch failure raises an ATLAS FEED INTERRUPTED chip
  with a Retry control (a console.warn is invisible to an operator).
- **The globe is operable, not just watchable.** Clusters actually zoom in on
  click (their tooltip promised it; the handler never did it); +/− zoom chips
  join Spin/Reset; the globe is keyboard-operable (tabindex + arrows rotate,
  Shift accelerates, +/− zoom, space toggles spin); a tone legend names the
  color code (zero-knowledge / selective / full / alert) instead of making
  operators guess; LIVE means live: reticles, HUD stats, and the histogram
  refresh every 60s while the tab is visible and immediately on tab return.
  One setZoom() now serves wheel, chips, keyboard, and cluster drill-down.
- **Role-gate sweep (the "buttons lead to error pages" class).** A
  three-role crawl found controls rendered for roles that 403 on click:
  operator/auditor-visible New-Agency/New-Individual/Edit/Delete buttons,
  auditor-visible Record-Verification and Issue-Token buttons, the
  state-transition form and Delete Token on token detail, and an edit link
  on the investigate page. Every control now sits behind the same role gate
  its route enforces.
- **Orphaned pages wired in.** /investigate/token/N and
  /investigate/individual/N were reachable only from each other; Investigate
  buttons now exist on the tokens list, token detail, and individuals list.
- **Overscroll seam fixed.** Rubber-banding past the top showed a visible
  border: the browser canvas (html background) restarted the body gradient.
  The canvas is now a solid tone matched to the masthead, and
  overscroll-behavior stops the bounce where supported.
- **Alignment fixes.** td.actions used display:flex, which detaches a table
  cell from the row border/baseline grid and visibly misaligned every
  actions column; buttons/pills now align inline (vertical-align: middle).
- **Proof, permanent:** (1) UiLinkIntegrityTests crawls every <a href>
  reachable as EACH role and fails if anything a user can see renders an
  error page — it caught a leak (investigate-page edit link) on its first
  run; plus pinned tests for the investigate navigation and each role-gated
  control. (2) check_template_endpoints_resolve (68th check) statically
  verifies every url_for() in templates names a real @app.route function,
  with detection tests. (3) A meta description fixed the one failing
  Lighthouse SEO audit.

## v9.142 — 2026-06-10 (full UI redesign, README rewrite, GitHub Pages site, and an 11-bug fix sweep)

The whole presentation layer, rebuilt, plus every confirmed finding from a
26-agent discovery sweep fixed. Verified by the full suites (498 web + 64 CLI,
green), all 67 checks, and a 12-surface visual pass in a real browser.

- **One unified stylesheet.** The two-layer CSS stack (light `polaris.css` +
  the v8.14 `polaris-scifi.css` skin, ~6.5k lines of override-the-override)
  is replaced by ONE dark mission-console design system (`polaris.css`,
  ~3.3k lines): deep-navy surfaces, gold command accents, cyan live data,
  per the DEVNOTES/style.md visual contract. The battle-tested Atlas globe
  internals carried over re-tokenized; everything else (masthead, nav,
  buttons, forms, tables, pills, cards, login, landing, demo, errors) is
  fresh. Coverage proven mechanically: every class referenced by templates/JS
  resolves in the new sheet. A11y: `:focus-visible` rings everywhere,
  `aria-checked`/`aria-pressed` on the atlas chips, reduced-motion kills all
  animation, print styles for warrant audits, responsive breakpoints (the
  old UI had none). The dashboard boot overlay + staggered reveal are now
  scoped to the dashboard (`body-dashboard`); pre-v9.142 they leaked onto
  every page. New SVG favicon. Every test-pinned selector and string survived:
  the full app suite passed unchanged.
- **Recovery queue state is finally readable**: `.channel-tick` (B/S/W
  out-of-band channels), `.pill-warn/-pending/-approved/-rejected`, and the
  `.info-panel`/`.kv`/`.muted`/`.footnote` structural classes had NO rule in
  either old stylesheet; an admin could not read the three-channel state. All
  styled now.
- **Bug sweep (19 confirmed findings + 1 loader bug, all fixed):** static UC
  prerequisite notices no longer vanish after 4.5s (flash dismisser scoped to
  `.flash-region`); the WebAuthn credential Remove button's `data-confirm`
  actually fires (moved to the form, matching every other destructive form);
  `/atlas` dropped ~190 lines of dead per-request work (3 queries + node
  assembly for a JSON island the v6 architecture never reads — and the C6
  check now reflects that the strongest redaction is not reading location at
  all); non-numeric `?page=`/`?page_size=`/`?individual_id=` on the HTML list
  routes return a styled 400 instead of a 500 (new `_int_arg` + 400 handler);
  the atlas fetch dedupe key resets on failure so a transient error no longer
  freezes the globe for a viewport; the event-feed counter populates; three
  dead JS hooks deleted; `#batch-N` deep links from token detail now land on
  an anchored row; demo step nav dropped bogus tab roles;
  `investigate_token` stopped fetching a 4-subquery ontology row it never
  rendered; and `01_schema.sql` gained the missing
  `DROP TABLE IF EXISTS IndividualErasureEvent`, which broke `00_load_all.sql`
  re-loads on any DB that had applied the erasure migration.
- **README rewritten** against ground truth: 28 tables / 11 procedures /
  70 routes / 67 checks / 562 tests (the old one said 26/14/67/17 in various
  places, claimed "current as of v9.63", and never mentioned the entire
  production arc: prod stack, PQ TLS edge, two-witness signing, CVE gates,
  pgBackRest DR). New "Production posture" section; quickstart now covers the
  prod deploy path. `check_table_count_matches_doc` hardened to validate EVERY
  stated table count (re.findall), with a detection test for the
  first-right-later-drifted case that v9.141 actually shipped.
- **GitHub Pages site** (`site/` + `.github/workflows/pages.yml`):
  a single-page project site in the same design language at
  https://egorkhaklin.github.io/polaris-id/. Pages enabled
  (build_type=workflow), repo homepage set, stale `swarm-intelligence` topic
  removed (dead since the v9.55 apparatus cut).
- **Doc rot fixed** (all adversarially verified first): dead
  `DR-SINGLE-REGION.md` references → `DR.md` (7 files); QUICKSTART/generator
  header no longer describe the pre-v9.140 "3 files, 0600" secrets posture
  that would re-break a Linux prod boot if "restored"; SYSTEM-MAP refreshed
  from its v9.08 freeze (deploy/, prod Dockerfiles, all 7 CI jobs, false
  test claim removed); NOTICE corrected (CM cut in v9.55, nine AoR triggers
  not eight, no more empty-sanctum citation); ROADMAP's PQC pointer updated
  (client-to-edge hybrid KEX shipped v9.136); landing page's "~350 legible
  lines" check-layer claim was 6x stale, reworded without rot-prone counts.

## v9.141 — 2026-06-09 (container hardening: every prod service drops all Linux capabilities)

With the prod-stack-boot job now able to prove the stack still serves, the prod
containers can be hardened safely. Every service in `docker-compose.prod.yml` now
drops ALL Linux capabilities and forbids privilege escalation
(`security_opt: no-new-privileges:true`), adding back only the few capabilities
each entrypoint genuinely needs.

- **The app + pgbouncer run with ZERO capabilities** (verified at runtime:
  `CapEff: 0000000000000000`). They are non-root and bind ports above 1024, so
  they need nothing.
- **The public Caddy edge** keeps only `NET_BIND_SERVICE` (to bind :80/:443) and
  drops everything else, so even though it is uid 0 it can do nothing but bind
  ports.
- **postgres and redis** keep only the five capabilities their root-then-drop
  init needs (`CHOWN`, `DAC_OVERRIDE`, `FOWNER` for the data dir, `SETGID`,
  `SETUID` for the gosu/setpriv drop to the unprivileged service user). Getting
  this wrong is silent: an early draft with `cap_drop: ALL` and no add crashed
  redis with `setpriv: setresuid failed: Operation not permitted` — caught by
  booting the hardened stack, not by reading the compose.
- **Proven, not asserted.** The `prod-stack-boot` CI job boots the HARDENED stack
  and asserts it still serves `/api/health` end to end. `check_container_hardening`
  (67th check) requires every service to drop ALL caps + forbid escalation, and
  requires the boot job to exist so a capability mistake fails CI, not production.
  (Full non-root `USER` for the Caddy edge, which needs careful volume-ownership
  handling the citest boot would not fully exercise, is a noted follow-up.)

## v9.140 — 2026-06-06 (the full production stack now boots end to end, and a prod-down init bug it found)

Booting the FULL production compose for the first time (only the dev compose and
per-image tests ran in CI before) found that the prod stack had never actually
come up. `polaris_sql/09_grants.sql` hardcoded `GRANT CONNECT ON DATABASE
polaris_test` — the dev/CI database name. Production uses `polaris`, so init hit
`ERROR: database "polaris_test" does not exist`, and under `ON_ERROR_STOP=1` +
`set -e` the whole `docker-init.sh` aborted BEFORE it enabled TLS. Result:
postgres came up with `ssl=off`, pgbouncer's verify-ca backend connection was
refused, the app could not reach the DB, gunicorn workers hung and crash-looped,
and nothing served. Every existing test uses the `polaris_test` name, so this was
invisible until the prod stack was booted as a whole.

- **The fix.** `09_grants.sql` now grants CONNECT on `current_database()` via
  dynamic SQL, the same pattern the file already uses for its ALTER DATABASE GUC
  settings. It loads correctly into `polaris` (prod), `polaris_test` (dev/CI), or
  any DB name. Verified: the prod stack boots, postgres comes up `ssl=on`, and
  `/api/health` serves 200 through the Caddy TLS edge with database (41 tables,
  ~18ms through the verify-ca hop), redis, and zk_binary all healthy.
- **The keystone test.** A new `prod-stack-boot` CI job generates real secrets +
  certs, builds the prod images, boots `docker-compose.prod.yml` +
  `docker-compose.citest.yml` (the only change from prod is Caddy's internal CA
  instead of ACME, since CI has no public domain), and asserts the stack serves
  `/api/health` end to end with the DB-backed components healthy and postgres
  `ssl=on`. This is the gap that let v9.135 and v9.140 ship; it is now closed.
- **A second prod-down bug it found: unreadable secrets.** With postgres fixed,
  the Linux CI boot surfaced another deploy-blocker the macOS boot had hidden:
  `polaris-generate-secrets.sh` wrote the file-mounted secrets 0600, but docker
  compose mounts file secrets with the source file's perms (it ignores the secret
  `mode`/`uid`), so on Linux the non-root app/pgbouncer containers (uid 1000)
  could not read a 0600 host-owned secret — pgbouncer exited "password file
  unreadable" and crash-looped, and with that fixed postgres's docker-init (which
  runs as the non-root postgres user) could not `cp` the 0600 server key
  ("Permission denied") and silently skipped replication readiness. EVERY secret a
  non-root container process reads is now 0644 inside the 0700 dir (the dir is the
  host boundary, the same model v9.131 used for the pgbouncer key):
  `polaris_secret_key`, `polaris_db_password`, `polaris_signing_key`,
  `polaris_replicator_password`, and `postgres_server.key`. Only
  `polaris_db_root_password` stays 0600 (the postgres entrypoint reads it as root).
  `SECRETS.md` is corrected so an operator does not `chmod 0600 secrets/*` and
  re-break it. macOS Docker Desktop uid-maps bind mounts, which hid all of this;
  the Linux CI boot found each layer.
- **Pinned.** `check_prod_stack_boot` (66th check) requires the boot harness
  (`Caddyfile.citest`, `docker-compose.citest.yml`) and a CI job that generates
  secrets, boots the full prod compose, and probes `/api/health`. Because the job
  boots on a Linux runner with non-root containers, it catches exactly this class.

## v9.139 — 2026-06-06 (fix a real deploy-blocker: the liboqs banner corrupted the generated signing key)

Exercising the full production-stack bring-up found a genuine production bug.
`polaris-generate-secrets.sh` mints the ML-DSA-65 signing key by capturing the
stdout of a `python -c "...print(json.dumps(generate_keypair()))"` (run via the
prod image when liboqs is not local, the common operator path). But liboqs-python
prints `liboqs-python faulthandler is disabled` to STDOUT at import, so the
capture prepended that banner to the JSON and wrote a malformed key file. With
`POLARIS_USE_REAL_PQC=1` (the production default since v9.116), the app then
refuses to load it (`RuntimeError: ...malformed`), so real-PQC token issuance
would have been broken on first deploy and only discovered there.

- **Clean capture.** The generator now swallows stdout during the pqc import
  (`sys.stdout = io.StringIO()`), so no import-time banner can leak into the key
  JSON. Verified end to end: the regenerated key parses, and the app signs with it
  (public key matches the trust anchor).
- **Fail loud, never write a malformed key.** The captured output is now validated
  to parse as ML-DSA-65 key JSON (both key halves present) before it is written;
  contamination fails generation rather than shipping a broken key.
- **Empty files regenerate.** The secret existence guards were `-e` (exists), so a
  0-byte file from an interrupted prior run silently blocked regeneration and could
  ship an empty secret. They are now `-s` (non-empty).
- **Pinned three ways.** `check_signing_key_generation` (65th check) asserts the
  stdout swallow, the JSON validation, and the `-s` guards; a detection test
  covers it; and the `pqc-real` CI job now runs the generator's snippet under real
  liboqs and asserts it emits clean ML-DSA-65 JSON.

## v9.138 — 2026-06-06 (scan the container images for CVEs, and patch the fixable ones)

A repo-grounded production-readiness gap analysis found a real, standard control
entirely absent: container IMAGE CVE scanning. pip-audit covers Python deps and
bandit covers our code, but the OS packages baked into every base image were
never scanned. They shipped real, fixable, CRITICAL CVEs. Measured with Trivy:
the app's Debian Bookworm base carried 2 fixable CRITICAL + 3 HIGH, and
postgres:16-alpine carried 1 CRITICAL + 16 HIGH. This adds the scan AND patches
what is fixable, so the control is not just reporting.

- **Patch the bases.** The four self-built Dockerfiles now upgrade their base
  packages: `apt-get -y upgrade` (Dockerfile.prod) and `apk upgrade --no-cache`
  (Dockerfile.caddy / pgbouncer / postgres). Measured result: the app image drops
  to 0 fixable CRITICAL and 0 HIGH; caddy, pgbouncer, postgres to 0 fixable
  CRITICAL.
- **Gate on fixable CRITICAL.** A new `image-cve-scan` CI job builds every prod
  image and runs Trivy, gating on fixable CRITICAL (`--severity CRITICAL
  --ignore-unfixed --exit-code 1`) and reporting HIGH informationally (base-image
  HIGHs churn daily and are mostly unfixable, so gating on them would flake).
- **One documented exception.** `.trivyignore` carries CVE-2025-68121 (a Go
  crypto/tls CVE in the postgres base image's `gosu` binary) with justification:
  gosu is the entrypoint's privilege-drop helper and opens no TLS, so the
  vulnerable session-resumption path is unreachable; it rides in across
  postgres:16/17-alpine and is not addressable by apk upgrade. Re-evaluate when
  the base ships a rebuilt gosu.
- **Pinned.** `check_image_cve_scanning` (64th check): CI must Trivy-scan the
  images gating on fixable CRITICAL with `--ignore-unfixed`, the self-built
  Dockerfiles must patch their bases, and exceptions must be documented in
  `.trivyignore`. Image CVEs cannot ship silently again.

## v9.137 — 2026-06-06 (precision: the internal-hop PQ gate is measured, and it is two limiters not one)

A small honesty correction to the v9.134/v9.136 audit, grounded in measurement.
The audit credited pgbouncer as "the" limiter holding the two internal TLS hops
classical. Measuring the actual OpenSSL versions of every component shows that is
incomplete: ML-KEM needs OpenSSL 3.5 on both ends of a hop, and the app's libpq
is OpenSSL 3.0.20 (Debian Bookworm base), pgbouncer is 3.3.7 (Alpine 3.20), and
postgres is already 3.5.6 (Alpine 3.23). So the app-to-pgbouncer hop is held
classical by BOTH ends, with the app's Bookworm libpq the older limiter, not just
the pooler. The doc, gap table, and roadmap P2 now state this precisely: closing
the internal hops needs TWO image base bumps (the app and pgbouncer), and the app
bump (Bookworm to Trixie or a 3.13 image) is a deliberate refresh with its own
regression surface, low priority given the notional, internal-only exposure.

This also records the honest conclusion of probing the next buildable transport
item: the internal-hop PQ KEX (audit P2) is gated on base-image upgrades and is
low value (notional data inside the trust boundary), not a quick win. No code
change; the security claim is simply made more accurate.

## v9.136 — 2026-06-06 (proven: the client-to-edge TLS hop does post-quantum hybrid key exchange)

The v9.134 audit called the client-to-edge TLS hop classical. Continuing down the
honest path, I tested it instead of assuming, and it was wrong in our favor: the
self-built Caddy edge (v9.135, Go 1.24+ TLS stack) negotiates the hybrid
post-quantum group X25519MLKEM768. This closes the audit's P1 gap (the
highest-priority transport item) with proof, not inference.

- **Proven off a real handshake.** Booting the edge with `tls internal` and
  connecting with an OpenSSL 3.5 client, the negotiated group is
  `X25519MLKEM768`, both when the client forces it AND with the client's default
  groups (so the server offers and selects the hybrid by default). A classical
  X25519-only client still completes the handshake, so it negotiates classical
  X25519. The KEX group is cert-independent, so the production Let's Encrypt path
  negotiates the same group as the test. A new `caddy-edge` CI step asserts all of
  this on every push.
- **Honest scope (adversarially reviewed).** A review panel checked the claim for
  overclaim and caught real qualification gaps, all fixed: the protection is
  OPPORTUNISTIC (the edge cannot require the hybrid without breaking pre-ML-KEM
  clients), so harvest-now-decrypt-later is closed only for connections from
  modern clients; old clients and active group-downgrade keep classical exposure.
  The gap-table status is `PQ_SECURE (modern clients)`, not unconditional. The
  toolchain claim is "Go 1.24+" (what the build supports), not a precise version
  the build does not pin.
- **The internal hops stay classical, precisely.** The audit now records that the
  two internal hops (app to pgbouncer, pgbouncer to postgres) remain classical
  because pgbouncer's image is on OpenSSL 3.3.7 (ML-KEM landed in 3.5); postgres
  is already on 3.5.6, so the pooler is the limiter. P2 is gated on rebuilding
  pgbouncer against an OpenSSL 3.5+ base.
- **Pinned.** `check_edge_pq_kex` (63rd check) keeps the claim honest: if
  `PQC-POSTURE.md` names the hybrid group, the `caddy-edge` CI job must read the
  negotiated group off a real handshake and gate on it. The doc can never drift
  ahead of the proof.

## v9.135 — 2026-06-06 (the production TLS edge actually starts: self-built Caddy with the rate_limit plugin)

The prod stack's TLS front door would not come up. The Caddyfile uses the
`rate_limit` directive (edge brute-force defense, 200 req/min/IP), which is the
third-party caddy-ratelimit plugin and is NOT compiled into the stock
`caddy:2-alpine` image the compose pinned. Validating the real Caddyfile against
the pinned image proves it:

    Error: adapting config: Caddyfile:85: unrecognized directive: rate_limit

So the edge container crash-looped on startup and nothing reached the app. This
is the same class as the bitnami/pgbouncer removal (v9.110): a latent prod-down
breakage CI never caught because the docker boot job runs the DEV compose, which
has no Caddy.

- **Self-built edge.** `polaris_web/Dockerfile.caddy` compiles Caddy from source
  with `xcaddy --with github.com/mholt/caddy-ratelimit`, both FROM stages
  digest-pinned (the runtime stage is the same image the compose pinned before),
  with an in-build `caddy list-modules` guard so a plugin-less build fails the
  image, not production. The compose `caddy` service now builds it
  (`image: polaris-caddy:prod`) instead of pulling the stock image, exactly like
  the self-built pgbouncer. Verified locally: the real Caddyfile reports "Valid
  configuration" against the built image and `http.handlers.rate_limit` is present.
- **CI regression guard.** A new `caddy-edge` job builds `Dockerfile.caddy` and
  runs `caddy validate` on the real Caddyfile against it, plus asserts the plugin
  module is present. A future unbacked directive or a broken plugin build fails in
  CI, not at deploy. This closes the blind spot that let the bug ship.
- **Pinned.** `check_caddy_self_built` (62nd check): if the Caddyfile uses a
  third-party directive, the edge must build from `Dockerfile.caddy` with that
  plugin compiled in, and CI must validate the Caddyfile against the built image.
  The stock image can never silently return.

## v9.134 — 2026-06-06 (an honest post-quantum posture audit: what is PQ, what is still classical)

Polaris's thesis is a "post-quantum identity system." That is true of the token
core and false of the transport, and an honest system has to say which is which.
This audits the entire cryptographic surface against the NIST timeline and writes
the result down without softening either side.

- **The audit.** `docs/reference/PQC-POSTURE.md` separates the layers. Post-quantum
  today: the ML-DSA-65 token signature (FIPS 204, two-witnessed since v9.133), the
  SHA3 binding and anchor hashing, the Plonky2 FRI-based ZK inclusion proof (which
  reduces to Poseidon collision-resistance, no Shor-breakable assumption), and the
  scrypt / symmetric session layer. Still classical: TLS key exchange on all three
  hops (classical ECDHE, harvest-now-decrypt-later), the RSA/ECDSA cert signatures,
  and the WebAuthn operator-MFA algorithms (ES256/EdDSA/RS256). Each classical
  surface states its real threat and its bounded exposure (the internal hops carry
  only notional data; the WebAuthn key never leaves the authenticator; WebAuthn and
  public-PKI migration are gated on third parties, not on Polaris).
- **Mapped to the NIST clock.** Every primitive is tagged against FIPS 203/204/205
  and IR 8547 (deprecate classical public-key after 2030, disallow after 2035),
  with a prioritized migration roadmap led by hybrid X25519+ML-KEM-768 on the
  client-to-edge hop.
- **Grounded, not asserted.** The inventory is built from the real code (an
  adversarial review caught and corrected a draft that presented BLAKE3/BLAKE2b as
  live anchor hashes when `anchoring.py` falls back to SHA3-256, and that mislabeled
  cert-signature forgery as harvest-now-decrypt-later). The audit reflects what the
  code actually does.
- **Pinned.** `check_pqc_posture` (61st check) keeps the audit honest: it must keep
  BOTH the post-quantum AND the still-classical sections, name the classical
  surfaces (TLS, WebAuthn) as classical, map to the 2030/2035 NIST clock, and
  disclaim production-readiness. The doc cannot be quietly softened into an
  overclaim. Linked from the reference index and the production-readiness ledger.

## v9.133 — 2026-06-06 (the ML-DSA-65 verify path is two-witnessed, like the ZK path)

Real ML-DSA-65 is the production signing default (v9.116), but every signature
verdict came from ONE library: liboqs. A bug or compromise in that single
implementation could silently accept a forged token, and a lone verifier would
never know. The ZK path already guards against exactly this with an independent
second witness (`polaris_zk/witness2/`); the PQC path did not. This brings the
same discipline to signing.

- **A second, independent witness.** `cryptography==48.0.0` (already pinned)
  ships an OpenSSL-backed ML-DSA-65 — a DIFFERENT FIPS 204 implementation than
  liboqs. `pqc_signing._verify_second_witness()` verifies the same SHA3-256
  digest through it. Interop is real, not assumed: a liboqs signature verifies
  under cryptography/OpenSSL (proven in tests and the pqc-real CI job).
- **The two must AGREE.** `verify_both()` runs both and returns valid only when
  they concur. A DISAGREEMENT — one accepts, one rejects — is a cryptographic red
  flag (a library bug, a compromise, or tampering a lone verifier would miss), so
  the verdict is False and the disagreement is logged loudly. Every real-PQC
  verify site routes through it: the issuance self-verify (refuses to issue a
  signature that fails the two-witness check), `verify_stored_signature`
  (token-detail), and `verify_token_signature` (verify-at-use). The smoke test
  exercises it too.
- **Graceful, honest degradation.** When the witness library is too old to
  provide ML-DSA, `verify_both` falls back to the lone primary — no worse than
  before v9.133 — and `availability_report()` surfaces whether the witness is
  live so operators are never misled about which guarantee is in force.
- **Pinned + proven.** `check_pqc_second_witness` (60th check) asserts
  `verify_both`/`_verify_second_witness` exist, the witness is cryptography's
  MLDSA65 (not a second liboqs call), a disagreement is refused, all three verify
  sites route through `verify_both`, and CI runs the agreement tests. New
  `SecondWitnessTests` prove the two implementations agree on a valid signature,
  both reject a tampered one, a forced disagreement is refused, and the path
  degrades to the primary when the witness is absent. The pqc-real CI job
  installs the witness and asserts cross-implementation agreement.

## v9.132 — 2026-06-06 (hardening: ENFORCE verify-ca at startup, from a review of v9.131)

A focused adversarial review of the v9.131 verify-ca ship found the pinning was
not ENFORCED: a hand-rolled deploy that set `verify-ca` but forgot the cert would
boot and fail confusingly at the first DB connection (it fails CLOSED — no
plaintext leak — but late and cryptically). The review also confirmed the key
posture is sound (the 0700 dir gates the 0644 key; no leak in logs/layers/git).
This makes the misconfigurations fail loud and early, like the v9.129 guards.

- **App: whitelist + require the pin.** The production startup guard now
  WHITELISTS `POLARIS_DB_SSLMODE` (must be `require`/`verify-ca`/`verify-full` — a
  typo like `verifyca` that the old blacklist let through is now rejected), and
  when the mode is verify-*, REQUIRES `POLARIS_DB_SSLROOTCERT` to point at a
  readable file. Refuses to start otherwise.
- **pgbouncer: require the CA + pair the cert/key.** The entrypoint now refuses
  to start when `server_tls_sslmode` is verify-* but no CA file is set, and when
  the client cert/key are half-set (one without the other, which would silently
  fall back to a generated cert the app cannot pin). Cert/CA paths are checked for
  control chars (they are interpolated into pgbouncer.ini).
- **Pinned + proven.** `check_prod_fail_closed` asserts the verify-* sslrootcert
  guard; `check_app_db_tls` asserts the entrypoint's CA-required enforcement.
  Subprocess tests prove the app refuses verify-ca-without-sslrootcert and a
  typo'd mode; the entrypoint enforcement (verify-ca-without-CA, cert-without-key)
  was proven against the built image.

## v9.131 — 2026-06-06 (hardening: both DB hops now VERIFY the pinned certs, not just encrypt)

The last review item: v9.121 encrypted both prod DB hops with `require`, which
defeats passive sniffing but not an active in-network MITM (it does not validate
the peer's cert). This raises both hops to verify-ca, pinning the self-signed
certs — no real CA needed.

- **The app pins pgbouncer.** `DB_CONFIG` gains `sslrootcert` from
  `POLARIS_DB_SSLROOTCERT`, and the prod compose sets `POLARIS_DB_SSLMODE=verify-ca`
  pointing at pgbouncer's cert. A MITM presenting a different cert on the
  app->pgbouncer hop is rejected.
- **pgbouncer pins postgres.** The entrypoint gains `server_tls_ca_file`; the
  prod compose sets `PGBOUNCER_SERVER_TLS_SSLMODE=verify-ca` with postgres's cert
  as the CA. The backend hop verifies, not just encrypts.
- **A stable, pinnable pgbouncer cert.** pgbouncer's client cert was regenerated
  per start (unpinnable). `polaris-generate-secrets.sh` now mints a STABLE
  `pgbouncer_server.crt/.key`; the entrypoint uses the mounted cert when present.
  Both files are 0644 inside the 0700 `secrets/` dir, so the non-root pgbouncer
  user reads the key across a Linux bind mount while the directory gates host
  access (a self-signed cert is its own CA for verify-ca, which skips hostname
  checks; `verify-full` + a real CA + hostname stays the operator's upgrade).
- **Proven on Linux in CI.** A new verify-ca pinning round-trip stands up
  postgres(ssl) + the pooler with both hops verify-ca and asserts: the correct
  pin connects, the backend hop is SSL (`pg_stat_ssl`), and a WRONG cert is
  rejected (`certificate verify failed`). Validated locally end to end first.
  `check_app_db_tls` now asserts verify-ca + the pinning wiring on both hops.

## v9.130 — 2026-06-06 (hardening: pgBackRest operational safety, from the v9.121-v9.128 review)

Three concrete operational gaps the review found in the v9.127 pgBackRest ship:
an operator could enable archiving but never bootstrap the stanza (WAL fills the
disk), run against a local repo thinking it was offsite, or leak S3 keys via the
compose environment.

- **Deploy auto-bootstraps the stanza.** When `POLARIS_PGBACKREST_ENABLED=1`,
  `polaris-deploy.sh` now runs `pgbackrest --stanza=polaris stanza-create` +
  `check` against the running stack (idempotent). A failure WARNS loudly but does
  not block the deploy. Closes the "enabled but unbootstrapped -> archive-push
  fails every WAL -> disk fills" gap.
- **Loud local-repo warning.** `docker-init.sh` warns when archiving is enabled
  but the repo is local (no `repo1-type=s3`) — a local repo does not survive host
  loss, so it is not the offsite durability an operator usually expects.
- **Secure S3-credential guidance.** pgBackRest has no `*_FILE` env convention, so
  `pgbackrest.conf` + `DR.md` now show the correct pattern: write the keys into a
  0600 file under `polaris_web/secrets/` (gitignored) and mount it at
  `/etc/pgbackrest/conf.d/`, NOT as compose `environment:` literals (which leak
  via `docker inspect`).
- **Pinned.** `check_pgbackrest_scaffolding` now also asserts the deploy
  auto-bootstrap, the local-repo warning, and the file-mounted-credential
  guidance; detection tests cover each.

## v9.129 — 2026-06-06 (hardening: fail closed on production misconfiguration, from a review of this session's ships)

A multi-agent adversarial review of v9.121-v9.128 surfaced silent-failure and
silent-misconfiguration gaps (each verified by hand; the speculative ones —
"force duress sync in prod", a trigger that would break rectification — were
discarded). This closes the four concrete ones.

- **Refuse a plaintext DB hop in production.** `POLARIS_DB_SSLMODE` defaults to
  `prefer`, which silently falls back to plaintext if the server lacks TLS. The
  prod compose sets `require`, but a hand-rolled deployment could miss it. app.py
  now refuses to start when `POLARIS_ENV=production` and `POLARIS_DB_SSLMODE` is
  `prefer`/`allow`/`disable` (mirrors the default-`SECRET_KEY` guard).
- **Refuse the duress timing side-channel in production.** `POLARIS_DURESS_SYNC=1`
  records the duress event on the request thread, reintroducing the v9.82 timing
  side-channel (a coerced operator's match becomes measurable). It is a test-only
  knob; app.py now refuses to start with it set in production.
- **The duress page can't fail silently.** `_METRICS_DURESS.inc()` was
  `try/except: pass`; a lost increment (mmap permission, corrupt multiproc file)
  would mean `PolarisDuressEvent` never fires and no one knows. It now logs the
  failure to stderr (safe: off the request thread, and prod sync is refused).
- **`/metrics` carries the duress signal — say so.** As of v9.128 a `/metrics`
  scraper can observe that a duress alarm fired. The route docstring and
  `deploy/observability/README.md` now state plainly that `/metrics` MUST be
  reachable only by the operator's monitoring, never the public internet.
- **Pinned.** `check_prod_fail_closed` (59th check) asserts both startup guards;
  subprocess tests prove production boot is refused on a plaintext sslmode and on
  `POLARIS_DURESS_SYNC=1`, and permitted on `require`.

## v9.128 — 2026-06-06 (production-readiness: the duress signal is now alertable)

`observability.py` calls duress "the headline metric": a coerced operator's
duress code raises a silent `DuressEvent`, and an unread one is the
coercion-cover failure mode (the whole mechanism is decorative if no one reads
the row). The signal lived only in the JSON `/api/metrics`, which Prometheus does
not scrape, so it could not page anyone. This makes it page-able.

- **`polaris_duress_events_total` on `/metrics`.** A new Prometheus counter,
  incremented in `_record_duress_async` right where the silent `DuressEvent` is
  written (best-effort, never raises into the duress path). Multiprocess-
  aggregated (v9.120), so the count is whole-app.
- **`PolarisDuressEvent` alert (SEV-1, immediate).** `increase(...) > 0` fires on
  any new duress event with no `for` window — duress cannot wait out a debounce.
- **A response runbook.** `RUNBOOKS.md` gains a `PolarisDuressEvent` section that
  is deliberately NOT a system-fix runbook: it is the coercion-response procedure
  (read the event out of band, never tip off a coercer, do NOT revoke or alter
  the holder's record in reaction, preserve the append-only evidence). The human
  response is operator-defined; Polaris's job ends at recording + paging.
- **Pinned + proven.** `check_duress_alertable` (58th check) fails the build if
  the counter is removed, stops being incremented at the record site, or loses
  its alert (a dead alert on a never-moving counter is worse than none). A
  DB-backed test drives a real duress-code match and asserts the `/metrics`
  counter increments; `check_alert_runbooks` enforces the new runbook section.

## v9.127 — 2026-06-06 (production-readiness: continuous WAL archiving with pgBackRest)

DR.md named continuous WAL archiving (pgBackRest) as the path to the ≤1-min RPO
but called it "not yet configured." This ships the configuration, leaving only
the operator's offsite repo.

- **pgBackRest in the DB image.** `Dockerfile.postgres` extends the
  digest-pinned `postgres:16-alpine` with pgBackRest (the `archive_command` runs
  inside the postgres process, so it must live on the DB host); the prod compose
  builds it (`polaris-postgres:prod`).
- **The stanza config.** `polaris_web/pgbackrest.conf` defines the `polaris`
  stanza with a local filesystem repo by default and documents the S3 swap (the
  keys stay in the environment, never the file). It is honest up front that a
  local repo is not offsite.
- **Opt-in archiving.** `docker-init.sh` enables `archive_mode` + the
  `archive_command` only when `POLARIS_PGBACKREST_ENABLED=1`, so a deployment
  with no provisioned repo never accumulates unarchivable WAL. `DR.md` is
  reconciled (config ships; the operator points the repo at S3 and runs
  `stanza-create`).
- **Proven end to end in CI.** A new `pgBackRest archive + backup + restore`
  round-trip builds the image, archives WAL, takes a full backup, then RESTORES
  into a fresh container and asserts a row written AFTER the backup comes back
  via WAL replay (the whole point of continuous archiving). Pinned by
  `check_pgbackrest_scaffolding` (57th check), which also fails the build if the
  config stops documenting the offsite repo or archiving stops being opt-in.

## v9.126 — 2026-06-05 (production-readiness: streaming-replication readiness + a failover runbook)

The single Postgres node was an unmitigated SPOF. This ships the buildable HA
scaffolding — a replication-ready primary, the standby bootstrap + promotion
runbook, and a CI proof — leaving only the operator-supplied standby host.

- **Replication-ready primary.** When the operator mounts the
  `polaris_replicator_password` secret, `docker-init.sh` sets the WAL params a
  standby needs (`wal_level=replica`, `max_wal_senders`, `max_replication_slots`,
  `hot_standby`, `wal_log_hints` via `ALTER SYSTEM`), creates a least-privilege
  `polaris_replicator` role (`LOGIN REPLICATION` only — it can stream WAL, not
  read application data), and adds the `pg_hba` entry
  (`POLARIS_REPLICATION_CIDR`, default `samenet`).
  `polaris-generate-secrets.sh` mints the password; the prod compose mounts it.
- **`docs/operator/FAILOVER.md`.** The standby bootstrap (`pg_basebackup -R`,
  which writes `standby.signal` + `primary_conninfo`), the promotion runbook
  (fence the old primary, `pg_promote`, repoint the app/pgbouncer), re-establishing
  redundancy, and the RPO/RTO story (async streaming meets the ≤1-min RPO far
  more tightly than the backup interval for the standby-survives class). Honest:
  the standby HOST and the failover decision are operator-gated; promotion is
  manual, not an automated controller.
- **Proven in CI.** A new `Streaming-replication primary -> standby` round-trip
  stands up a primary with the shipped config, clones a standby with
  `pg_basebackup -R`, and asserts a row written AFTER the clone replicates, the
  standby is in recovery, and `pg_stat_replication` sees it. Pinned by
  `check_replication_scaffolding` (56th check), which also fails the build if
  `FAILOVER.md` overclaims a running standby. DR.md + PRODUCTION-READINESS.md
  reconciled (HA scaffolding ships; standby host operator-supplied).

## v9.125 — 2026-06-05 (production-readiness: right-to-erasure that respects the audit)

PRIVACY.md said pseudonymizing a holder's name was "operationally supported,"
but nothing implemented it. This ships the mechanism, designed so erasure cannot
become a path around C1 (the append-only audit) or around non-repudiation.

- **`uc_pseudonymize_individual(individual_id, actor_user_id, reason)`.** Replaces
  `Individual.legal_name` with a deterministic `PSEUDONYMIZED-<id>` marker. The
  Individual row stays, so every audit and token reference to its `individual_id`
  remains whole. It is gated to an ACTIVE admin by parameter and issues NO
  `DELETE` (it is not SECURITY DEFINER and cannot be a covert deletion path). It
  refuses to double-erase by consulting the authoritative `IndividualErasureEvent`
  log (not the current name, which has no format constraint), and it writes no
  server-log line about the holder (the DB row is the record).
- **`IndividualErasureEvent`, append-only.** The pseudonymization is itself
  audit-of-record: a row records who erased, when, and why — but deliberately
  NOT the prior name or a hash of it (storing either would defeat the erasure).
  The table joins the append-only set: the `reject_audit_modification` trigger
  rejects UPDATE/DELETE, and `09_grants.sql` REVOKEs them from `polaris_app`
  (the v9.85 boundary, so even the GUC carve-out cannot reach it).
- **Operator entry point.** `scripts/polaris-pseudonymize-individual.sh`
  validates argv (numeric ids; the reason is SQL-literal-escaped) and calls the
  procedure. PRIVACY.md now points at the real mechanism.
- **Proven + pinned.** `ErasureTests` (DB-backed) proves the name is replaced,
  the act is recorded, the append-only audit and token bindings are untouched,
  the erasure log rejects UPDATE/DELETE, and double-erase + non-admin are
  refused. `check_erasure_procedure` (55th check) pins the wiring and that the
  procedure never DELETEs; `check_aor_privilege_boundary` now covers the new
  table. Schema is 28 tables (docs reconciled). A four-axis adversarial review
  (C1-bypass, Vocation-leak, injection/privilege, correctness) hardened the
  double-erase guard, added the active-admin check, and dropped the server-log
  line before ship; its name-leak "blockers" were verified false (the marker
  carries only the non-secret structural `individual_id`, and no table copies
  `legal_name`).

## v9.124 — 2026-06-05 (production-readiness, wave 3: the at-rest posture, documented and pinned)

The last agent-buildable Wave 3 item. Polaris encrypts backups (v9.102) and the
app<->DB path (v9.121), but the live database files are not encrypted by Polaris,
and `TokenStateEpochLeaf.proof_path` is plaintext JSONB the schema itself flags
("v1 stores proof_path in plaintext"). This ships the honest posture, not a false
claim that the live DB is encrypted.

- **`docs/operator/ENCRYPTION-AT-REST.md`.** Enumerates the plaintext-sensitive
  surfaces (`Individual.legal_name`, `Individual.date_of_birth`,
  `TokenStateEpochLeaf.proof_path`); records what is already protected (encrypted
  backups, in-transit TLS) and what is not (the live data files + WAL); and
  explains why the right control is host volume encryption (LUKS / dm-crypt /
  fscrypt), not field-level: encrypting `legal_name` / `date_of_birth` breaks the
  C3 one-identity partial unique index, and encrypting `proof_path` breaks the ZK
  second witness that recomputes the Merkle path. Data minimization is named as
  the strongest control: biometric / genomic plaintext never enters the DB.
- **`check_encryption_at_rest_posture` (54th check).** Grounds the doc in the
  schema: it must name `proof_path` / `legal_name` / `date_of_birth`, must say
  `plaintext` while the schema still stores `proof_path` that way (drift guard),
  must name the host-level path, and must NOT claim the live DB is encrypted at
  rest (honesty guard). Detection test covers each branch.
- **The agent-buildable arc converges here.** With this ticked, every remaining
  item in `docs/PRODUCTION-READINESS.md` is operator-gated (the host encryption
  layer + key custodian, the offsite/WAL store, and the legal/HA/HSM/pen-test
  decisions) — organizational calls, not code.

## v9.123 — 2026-06-05 (production-readiness, wave 4: SLOs + alert runbooks, grounded and honest)

Wave 4 shipped the alert rules (v9.115) but left the SLO targets and the
response runbooks open. This closes both, grounded only in metrics Polaris
actually exposes, and refuses to overclaim that any of it is enforced.

- **`docs/operator/SLOS.md`, reference SLO targets.** Availability (≥ 99.9%
  non-5xx, the exact complement of the `PolarisHigh5xx` ratio), request-latency
  p99 < 2s, and DB-round-trip p99 < 5s, each computed from a metric the app
  emits (`polaris_requests_total`, `polaris_request_latency_seconds`,
  `polaris_db_query_latency_seconds`) over a 30-day window. Error budget stated
  (0.1% of requests, ~43 min/30d). Honesty discipline up front: these are
  reference targets for a notional deployment, not a measured guarantee, and the
  Prometheus + Alertmanager backend is operator-gated. `duress_events_total` and
  `auth_failures_per_minute` are deliberately excluded as SLIs (security
  signals, not reliability budget; per-identity SLOs would be an aggregation
  vector, vocation).
- **`docs/operator/RUNBOOKS.md`, one runbook per shipped alert.** A section
  for each of the five alerts (`PolarisAppDown`, `PolarisAppInfoAbsent`,
  `PolarisHigh5xx`, `PolarisHighDBLatency`, `PolarisHighRequestLatency`), each
  with Trigger / Likely cause / Diagnosis / Remediation, cross-linked to the DR
  failure-class procedures and the SLO thresholds.
- **`check_alert_runbooks` (53rd check).** Parses the `- alert: <Name>` lines
  out of `polaris-alerts.yml` and asserts a one-to-one mapping with the
  `## <name>` runbook headings: FAIL if an alert has no runbook (a page with no
  runbook is a 03:00 dead end), FAIL on an orphan section (stale guidance).
  Detection test covers missing-runbook, one-to-one-OK, orphan, and
  missing-file cases.
- **Production-readiness ledger.** The Wave 4 "SLOs; runbooks" item is now
  ticked.

## v9.122 — 2026-06-05 (production-readiness, wave 4: request-correlation ids that cannot become a surveillance key)

Production debugging needs to tie a log line to the request a caller saw, but in
a privacy-first identity system a correlation id is a hazard: persist it into the
audit trail and it becomes a permanent, reconstructable record of one person's
activity. This ships the id with that failure mode designed out.

- **Per-request, ephemeral by construction.** `observability.py` holds the id in
  a `contextvars.ContextVar` set in `before_request` and cleared in
  `teardown_request`, so it never leaks into the next request a worker serves.
  It lives only in that contextvar and the `X-Request-ID` response header. There
  is no DB column, cookie, cache, or global registry.
- **Stamped into the logs, echoed to the caller.** Every `structured_log` line
  carries `request_id`, and the unhandled `[db_error]` path now routes through
  `structured_log` so the single most useful line to correlate is tagged. The id
  is echoed in `X-Request-ID` on every response produced through the normal
  pipeline, including handled error responses (404/403/413/429).
- **Bounded and mint-always.** An inbound id is accepted only if it matches
  `\A[A-Za-z0-9-]{8,64}\Z` (safe charset, bounded length, newline-proof anchors);
  anything else is replaced by `uuid4().hex`. An inbound id is honoured only
  behind a trusted proxy (`POLARIS_TRUST_PROXY`, symmetric with
  `X-Forwarded-For`); otherwise the server always mints its own, so an untrusted
  client cannot choose its correlation token.
- **Vocation, enforced.** The id is never derived from identity and never written
  to the append-only audit-of-record. `check_correlation_id` (52nd check) fails
  the build if `observability.py` gains DB access, if `security.py` references
  the id, if it co-occurs with an audit call, if `set_request_id` is fed anything
  but the validator, or if it is seeded from a session/user. The proof a static
  check cannot give is a DB-backed test: it drives failed logins (which write
  audit rows) while a trusted operator-chosen id is in context, then asserts no
  `AuthAuditLog` row contains it. Useful for live debugging, inert as an
  aggregation vector. That asymmetry is the anti-coercion property.

## v9.121 — 2026-06-05 (production-readiness, wave 3: the app<->DB path is encrypted on both hops)

The prod stack routes the app through pgbouncer to Postgres, and both hops moved
plaintext: a tap on the pod network (or a compromised sidecar) could read every
query and the SCRAM exchange in the clear. Wave 3 turns on TLS end to end.

- **Postgres hop.** `docker-init.sh` copies a server cert mounted at
  `/etc/polaris-pg-certs/` into `PGDATA` (key 0600, cert 0644) and runs
  `ALTER SYSTEM SET ssl = on` with `ssl_cert_file`/`ssl_key_file`, then reloads
  (`ssl` is SIGHUP-reloadable). `scripts/polaris-generate-secrets.sh` mints the
  self-signed cert (`/CN=postgres`, 825 days) at deploy time if absent, alongside
  the signing key — it never enters the repo (secrets/ is gitignored).
- **Both pgbouncer hops.** The self-built pooler now reads
  `PGBOUNCER_SERVER_TLS_SSLMODE` (pgbouncer -> postgres) and
  `PGBOUNCER_CLIENT_TLS_SSLMODE` (app -> pgbouncer); for the client hop the
  entrypoint mints its own `/CN=pgbouncer` cert with openssl (added to
  `Dockerfile.pgbouncer`). Both sslmodes are validated against the pgbouncer
  enum before they reach `pgbouncer.ini`. The prod compose sets both to
  `require`; both default OFF so dev and the existing CI round-trip stay plaintext.
- **App hop.** `DB_CONFIG` gains `sslmode` from `POLARIS_DB_SSLMODE` (default
  `prefer` for dev; the prod compose sets `require`), so the psycopg2 connection
  negotiates TLS to the pooler. `require` encrypts without pinning a CA, which a
  self-signed cert satisfies; `verify-full` against a real CA stays an
  operator-gated step (documented, not claimed).
- **Proven + pinned.** A local docker stack brought all three containers up with
  TLS and confirmed `SSL established: TLSv1.3` on both hops (backend_ssl=t). CI
  gains a `client_tls` round-trip: a pooler with `CLIENT_TLS=require` must mint
  its cert and serve an `sslmode=require` client. `check_app_db_tls` (51st check)
  asserts the wiring across app.py, the prod compose, docker-init, and the
  pgbouncer entrypoint so a hop cannot silently revert to plaintext.

## v9.120 — 2026-06-05 (production-readiness, wave 4: Prometheus metrics aggregate across workers)

The `/metrics` endpoint used a per-worker Prometheus registry, so a scrape
reported only the gunicorn worker that happened to serve it — a 4x undercount
of every counter under the prod default of 4 workers. Any absolute-count alert
or dashboard built on it would read low by the worker count.

- **Multiprocess mode.** When `PROMETHEUS_MULTIPROC_DIR` is set (now the prod
  default), each worker file-backs its samples into that directory and the
  `/metrics` scrape aggregates ALL of them through a fresh
  `MultiProcessCollector` — so a counter reflects the whole app. The dedicated
  single-process registry path is preserved for dev. The `polaris_app_info`
  gauge gets `multiprocess_mode='max'` to collapse cleanly to one line.
- **Worker lifecycle.** `gunicorn.conf.py` clears the metric directory at master
  start (`on_starting`, before workers fork, so a previous run's files don't
  pollute) and reaps a dead worker's files on `child_exit`
  (`mark_process_dead`), so a cycled worker stops contributing to the aggregate.
- **Proven across real processes.** `MetricsMultiprocessTests` increments a
  counter in one process and scrapes `/metrics` from a SEPARATE process, which
  must see the increment — the genuine cross-worker property, not a single-
  process stand-in. The CI prod smoke-boot now sets the dir so the gunicorn
  multiprocess path boots cleanly.
- **Pinned + reconciled.** `check_prometheus_multiprocess` (50th check) asserts
  the collector + `child_exit` + the dir; the alert-rules README no longer warns
  about per-worker undercounting. Ticks the Prometheus box in
  `docs/PRODUCTION-READINESS.md` Wave 4.

## v9.119 — 2026-06-05 (production-readiness, wave 2 COMPLETE: uc6 migration routes through the signing module)

The last hardcoded signature. uc6 algorithm-migration wrote
`f"UC6_OPERATOR_MIGRATE_{token_id}_{new_algorithm}"` directly into
`TokenSignature.signature_bytes` — a non-signature that bypassed the signing
module entirely, so a migrated token's new signature verified as neither real
nor a valid placeholder.

- **uc6 now signs like issuance.** The `/uc6/migrate` route fetches the token's
  value, calls `pqc_signing.signature_with_key_for_token()` (real ML-DSA-65 when
  enabled, else the deterministic SHA3-256 placeholder), and passes the bytes +
  the issuer public key to `uc6_migrate_algorithm`, which now takes
  `p_signing_public_key_hex` and stores it in `signing_public_key_hex` — so a
  migrated signature is self-contained and verifies on the token-detail page
  exactly like an issued one. Signing failures block the migration.
- **No new migration needed.** The column already exists (v9.117); the procedure
  change reaches upgraded DBs via the v9.118 `--sync-objects` re-sync.
- **Tested + pinned.** `test_uc6_route_signature_routes_through_signing_module`
  proves the route stores `sha3(token_value)`, not the old string;
  `check_pqc_wired` now also fails if `UC6_OPERATOR_MIGRATE` reappears. All 17
  multi-signature tests pass.

**Wave 2 (the cryptographic core) is complete:** real ML-DSA-65 testable →
persistent-key trust anchor → verification enforced → real PQC the production
default → issuer key stored as a DB trust anchor, verification surfaced at use →
every signing path (issuance and migration) routes through the module.

## v9.118 — 2026-06-05 (production-readiness: procedure/trigger changes reach an UPGRADED database, not just a fresh one)

A latent deploy bug, surfaced while wiring uc6: `docker-init.sh` loads the full
schema + all procedures/triggers/grants and applies migrations — but only on a
**fresh** data volume (postgres init scripts never re-run on an existing one).
On an **upgrade**, `polaris-deploy.sh` brought the stack up and did nothing
else: no migrations, no procedure re-sync. So a changed stored procedure never
reached the running DB — concretely, **v9.117's `uc1_issue_and_activate`
signature change would be absent on an upgraded prod DB and issuance would fail**
(the app passes one more argument than the stale procedure accepts). It is
systemic: it applies to every procedure/trigger/view/grant change.

- **`polaris-migrate.sh --sync-objects`** re-applies the idempotent object files
  (views, procedures, triggers, queries, atlas/foresight/ontology helpers,
  grants) — all verified safe to re-apply to a populated DB. A dropped-then-
  synced procedure round-trip proves it restores the current definition.
- **Migrations now apply over the containerized stack.** `--up`/`--down` inline
  the migration body (via `cat`) instead of `\i <host-path>`, which a psql
  running *inside* the postgres container cannot resolve — so
  `--target=docker-stack` works by piping the SQL over stdin (verified the
  `$$`-quoted trigger migration survives the inlining; up/down round-trips).
- **The deploy now updates the DB.** `polaris-deploy.sh` runs `--up` +
  `--sync-objects` against the running stack after bring-up — idempotent on a
  fresh deploy, the fix on an upgrade.
- **Pinned** by `check_deploy_syncs_db_objects` (the 49th check).

## v9.117 — 2026-06-05 (production-readiness, wave 2: the issuer public key is a DB trust anchor, verification is surfaced at use)

v9.113 enforced verification but left it dependent on the live
`POLARIS_PQC_SIGNING_KEY_FILE`, and `TokenSignature` recorded only the crypto
algorithm — not the signature SCHEME — so a verifier could not tell a real
ML-DSA-65 signature from the SHA3-256 placeholder, nor verify after a key
rotation. v9.117 stores the issuer public key WITH each signature and shows the
verification result on the token-detail page.

- **`TokenSignature.signing_public_key_hex`** (migration
  `2026-06-05-001`): the issuer public key (hex) that produced the signature,
  NULL for a placeholder. Self-contained — verification needs no live key file —
  and null-vs-not captures the scheme. Write-once: the immutability trigger now
  protects it (`IS DISTINCT FROM`, since it is nullable; verified by a refused
  UPDATE).
- **Threaded through issuance.** `signature_with_key_for_token()` surfaces the
  public key; `uc1_issue_and_activate` takes `p_signing_public_key_hex` and
  stores it; the placeholder path stores NULL.
- **Verified at use.** The token-detail page calls
  `verify_stored_signature(token_value, bytes, key)` for each signature and
  renders a Verification column — *verified* (real, checks against the stored
  key), *INVALID*, *placeholder*, or *verifier offline* — without the raw bytes
  or key ever reaching the response.
- **Tested + pinned.** DB-backed `test_token_detail_surfaces_signature_verification`,
  two new `pqc_signing` unit tests, and the migration's up/down + write-once
  proven against a throwaway DB. `check_signature_self_contained_verify` (the
  48th check) pins the column + procedure param + the token-detail verify.
  Advances the Wave 2 box in `docs/PRODUCTION-READINESS.md` (only uc6 remains).

## v9.116 — 2026-06-05 (production-readiness, wave 2: real ML-DSA-65 is the production default)

Real post-quantum signing was testable (v9.103) and verification was enforced
(v9.113), but production still signed with the SHA3-256 placeholder: liboqs was
not in the prod image, so `POLARIS_USE_REAL_PQC=1` there would have failed to
import. This ship makes real ML-DSA-65 the actual default in production.

- **liboqs ships in the prod image.** `Dockerfile.prod`'s Python builder now
  builds liboqs from source (the `liboqs-python` install triggers it) and the
  runtime stage copies the prebuilt library into the `polaris` user's home — no
  compiler or build tools in the runtime layer. Validated by building the image
  and signing inside it: `available: True, enabled: True, ML-DSA-65, 3309-byte
  signature, verify-at-use True`, all as the non-root user.
- **The flag is on, with a real trust anchor.** `docker-compose.prod.yml` sets
  `POLARIS_USE_REAL_PQC=1` and mounts a new `polaris_signing_key` secret (the
  ML-DSA keypair), pointed to by `POLARIS_PQC_SIGNING_KEY_FILE` — so the public
  key is the stable anchor `verify_token_signature` checks against.
- **Key minting.** `polaris-generate-secrets.sh` mints the signing keypair (via a
  local liboqs or the built `polaris-app:prod` image) into the gitignored
  secrets dir, mode 0600. Operators custodying key material in an HSM/KMS supply
  their own loader instead — that custody stays operator-gated.
- **CI proves it in the image.** The `docker-image` job now runs real ML-DSA-65
  sign + verify-at-use inside the built prod image, so a broken liboqs copy fails
  CI, not a deploy. Pinned by `check_prod_real_pqc`. Closes the Wave 2 prod-
  default box in `docs/PRODUCTION-READINESS.md` (DB trust-anchor table +
  use-surface wiring + uc6 remain).

## v9.115 — 2026-06-05 (production-readiness, wave 4: alerting rules are a shipped, validated artifact)

`DR.md` told operators that "PolarisHigh5xx and related Prometheus alerting
rules" classify incidents automatically — but those rules existed only as a
snippet inside `OPERATIONS.md`. There was nothing an operator could actually
deploy: a doc-overclaim with no shipped artifact behind it.

- **A real, promtool-validated bundle.** `deploy/observability/` now ships
  `polaris-alerts.yml` (five rules: `PolarisAppDown`, `PolarisAppInfoAbsent`,
  `PolarisHigh5xx`, `PolarisHighDBLatency`, `PolarisHighRequestLatency`,
  severity-labelled to the DR.md SEV ladder), a `prometheus.yml` scrape config
  that loads them, and a README. Both pass `promtool check`.
- **Honest about the metric limitation.** The app's `/metrics` uses a per-worker
  registry, so absolute counters are per-gunicorn-worker until multiprocess
  aggregation lands. The shipped alerts are deliberately **ratios** (5xx share)
  and **quantiles** (latency percentiles), which stay valid per worker — the
  README warns against absolute-count thresholds until aggregation exists.
- **Docs reconciled.** `DR.md` and `OPERATIONS.md` now point at the shipped file
  instead of implying rules that did not exist. The alerting backend
  (Alertmanager + pager) stays operator-provided.
- **Pinned** by `check_alert_rules` (the 45th check): the rules + scrape config
  must ship and be wired. Ticks the alert-rules box in
  `docs/PRODUCTION-READINESS.md` Wave 4.

## v9.114 — 2026-06-05 (production-readiness, wave 4: prod images are pinned by digest, not a mutable tag)

The prod compose pulled `caddy:2-alpine`, `postgres:16-alpine`, and
`redis:7-alpine` by tag. A tag is a mutable pointer: upstream can repoint it at
different content, or retire it entirely — exactly what happened to
`bitnami/pgbouncer:1.22` (v9.110). Pulling by tag means the deploy can silently
run something other than what was reviewed.

- **Digest-pinned.** All three third-party prod images are now
  `name:tag@sha256:<digest>` — the tag stays for readability, the digest makes
  the image immutable. The deploy runs exactly the bytes that were vetted; a
  mutated or deleted upstream tag cannot change that. (The locally-built
  `polaris-app` / `polaris-pgbouncer` images have no registry digest to pin.)
- **Kept current.** A frozen digest never receives security updates on its own,
  so the `docker` ecosystem was added to `.github/dependabot.yml` — it opens PRs
  to bump a pinned digest when the upstream tag moves.
- **Pinned** by `check_prod_images_digest_pinned` (the 44th check): every
  third-party `image:` in the prod compose must carry `@sha256:` and Dependabot
  must track docker. Ticks the image-digest box in
  `docs/PRODUCTION-READINESS.md` Wave 4.

## v9.113 — 2026-06-05 (production-readiness, wave 2: signature verification is enforced, not just possible)

The signing core could produce a real ML-DSA-65 signature (v9.103), but
`verify()` was never called on any live path — a signature nothing ever checks
is theater. v9.113 makes verification a live, enforced obligation.

- **Issuance self-verifies.** `signature_bytes_for_token()` now verifies the
  real signature it just produced against its own public key before handing it
  to the DB, and raises `SigningError` (issuance blocked, surfaced to the
  operator) if it does not check out. A broken key or liboqs can no longer
  persist an unverifiable signature.
- **A use-path verification primitive.** `verify_token_signature(token_value,
  signature_bytes, algorithm_label)` checks a stored `TokenSignature` against
  its token. For a real `ML-DSA-65` signature it verifies against the published
  **trust anchor** (`trust_anchor_public_key_hex()`, the persistent signing
  key's public key) — a genuine authenticity proof; without a configured anchor
  it returns False (cannot prove authenticity). For the placeholder it is an
  integrity recompute. Dispatch is on the algorithm recorded WITH the signature,
  so a token verifies correctly regardless of the verifier's current mode.
- **Exercised in CI.** The `pqc-real` job now asserts the trust anchor matches,
  a real signature verifies at use, tamper/forgery is rejected, and the issuance
  self-check refuses a signature that fails to verify. Eight new unit tests in
  `test_pqc_signing.py` cover both the placeholder and real paths.
- **Pinned.** `check_verify_enforced` (the 35th check, after `check_pqc_real_signing`)
  asserts issuance self-verifies and CI exercises `verify_token_signature`.
  Advances the Wave 2 box in `docs/PRODUCTION-READINESS.md` (still owed: a DB
  trust-anchor table, wiring verification to a use surface, real PQC as the prod
  default, and uc6 through the signing module).

## v9.112 — 2026-06-05 (production-readiness, wave 4: SAST in CI catches a world-writable state dir)

Dependency CVEs were scanned (v9.105) but our own source never was. Adding
bandit (SAST) immediately surfaced a real HIGH: `_ensure_state_dir()` did
`chmod 0o777` on `POLARIS_STATE_DIR` — world-writable — and that directory can
hold sensitive state (in the dev launcher path, the persisted Flask
`secret_key`). On a shared host any local account could replace those files
(session forgery) or drop the `quit` file to tear the stack down.

- **The state dir is locked down in production.** `_ensure_state_dir()` now
  `chmod`s `0o700` when `POLARIS_ENV=production` — the container owns the
  directory and no host launcher shares it, so owner-only is correct. The looser
  `0o777` survives only outside production, where the watch-mode launcher runs as
  a different uid and genuinely needs the cross-uid share (carrying an inline
  `# nosec B103` with the rationale).
- **SAST gates the build.** The `cve-scan` job (now "Dependency CVE scan + SAST")
  runs `bandit` over `polaris_web` + `polaris_cli`, gating on HIGH severity +
  medium confidence. Lower-severity findings (bind-all inside the container,
  parameterized SQL flagged as string-building, the dev `/tmp` default) are
  reported but do not block.
- **Pinned + tested.** `check_sast_scanning` (43rd check) asserts CI runs bandit
  gating on high severity; `StateDirPermsTests` proves the dir is `0o700` in
  production and `0o777` only in dev. Ticks the SAST box in
  `docs/PRODUCTION-READINESS.md` Wave 4.

## v9.111 — 2026-06-05 (production-readiness: CI builds + round-trips the self-built pgbouncer image)

v9.110 made pgbouncer self-built but nothing in CI built or ran that image — the
same blind spot that let a broken app image (v9.40, v9.58) and an unbuildable
prod image (v9.98) ship green. A regression in `Dockerfile.pgbouncer` or the
entrypoint would only surface at deploy, when the stack cannot reach the
database.

- **Real round-trip in CI.** The `docker-image` job now builds the pgbouncer
  image and exercises the actual path: a Postgres (scram) backend, a
  `polaris_app` role, the file-mounted secret, then a client query through
  `pgbouncer:6432` asserting `PB-OK` — proving SCRAM works on both hops in CI,
  not just on a developer's machine. A negative check confirms the container
  fails closed when the secret is not mounted.
- **Pinned.** `check_pgbouncer_self_built` now also requires CI to build
  `Dockerfile.pgbouncer`, so the coverage cannot be silently dropped.

## v9.110 — 2026-06-05 (production-readiness: the prod stack's pgbouncer is self-built, not a vanished vendor image)

The production compose pinned `bitnami/pgbouncer:1.22` for connection pooling.
Bitnami retired their free Docker Hub catalogue in August 2025: that tag now
404s and the whole `bitnami/pgbouncer` repo has zero tags (the `bitnamilegacy`
mirror is gone too). `docker compose -f docker-compose.prod.yml up` could no
longer pull the pooler, and since the app reaches Postgres only through
`pgbouncer:6432`, the entire stack was unstartable — a latent outage waiting for
the next clean deploy, the same class as the v9.98 unbuildable-image bug.

- **Self-built pooler, no third-party catalogue.** `polaris_web/Dockerfile.pgbouncer`
  builds pgbouncer from `alpine` + the distro package (PgBouncer 1.22.1, same
  version as before). Nothing external can disappear out from under the stack
  again.
- **Secret stays a file, SCRAM on both hops.** `pgbouncer-entrypoint.sh`
  generates `pgbouncer.ini` + `userlist.txt` at start, reading the DB password
  from the file-mounted Docker secret (`POLARIS_DB_PASSWORD_FILE`) — it never
  enters the environment, the image, or `docker inspect`. The password is stored
  plaintext in a `0600` userlist with `auth_type = scram-sha-256`, so pgbouncer
  runs SCRAM both verifying the app and authenticating onward to Postgres.
  Embedded quotes are doubled per pgbouncer's userlist grammar so an exotic
  password cannot break or inject a second entry.
- **Least privilege + validated config.** No `admin_users`/`stats_users`, so the
  app role cannot issue pgbouncer admin commands (PAUSE/RELOAD/SHUTDOWN); the
  backend user is pinned in the `[databases]` entry so a client cannot have a
  claimed identity forwarded; control-character passwords and malformed numeric/
  enum/identifier settings are rejected at start rather than corrupting the
  generated config. (These came out of an adversarial review of the change.)
- **Healthcheck + ordering.** The pgbouncer service gets a TCP healthcheck and
  the app now waits on `pgbouncer: service_healthy`.
- **Verified with real containers.** Built the image and ran the full path —
  Postgres (scram) -> pgbouncer -> client through `:6432` — with both an ordinary
  and an adversarial (`"`/`\`) password, confirmed transaction pooling, the
  healthy healthcheck, and a loud failure when the secret is missing.
- **Pinned.** `check_pgbouncer_self_built` (42nd check) fails if bitnami/pgbouncer
  reappears, the self-built Dockerfile/entrypoint goes missing, or the password
  moves to an env var.

## v9.109 — 2026-06-05 (production-readiness, wave 4: every prod container bounds its memory, CPU, and logs)

The production compose set no resource limits and no log rotation on any
service. So one container with a memory leak could consume all host RAM and
take the whole stack down with it (no cgroup ceiling), and the default
json-file log driver grows without bound until it fills the disk — a slow
outage that looks like nothing until `df` hits 100%.

- **Resource limits on all five services.** caddy, app, pgbouncer, postgres,
  and redis each get `deploy.resources.limits` (memory + cpu) and a memory
  reservation, sized to role (postgres 1G, app 768M, redis 256M, caddy +
  pgbouncer 128M). Compose v2 honors these for `docker compose up`, so a runaway
  container is OOM-killed by its own cgroup instead of starving its neighbors.
- **Log rotation on all five.** Each service uses the `json-file` driver capped
  at `max-size: 10m` x `max-file: 5` (50 MB/container ceiling), so logs roll
  over instead of filling the disk.
- **Pinned.** `check_compose_resource_limits` (41st check) parses the compose by
  text (the check layer runs on system python, no PyYAML) and fails unless every
  service has both a limit block and a rotating log driver. `docker compose
  config` resolves the file cleanly. Ticks the resource-limits box in
  `docs/PRODUCTION-READINESS.md` Wave 4.

## v9.108 — 2026-06-05 (production-readiness, wave 4: liveness and readiness are separate probes)

`/api/health` ran the full dependency roll-up (database, redis, ZK binary,
disk) and the container HEALTHCHECK keyed on it returning `"status":"healthy"`.
That conflates two different production signals. A liveness probe answers "is
this process alive?" and its failure should RESTART the container; a readiness
probe answers "can this instance serve traffic?" and its failure should STOP
routing without a restart. Keying the container HEALTHCHECK on the dependency
roll-up means a transient DB or redis blip marks the container unhealthy and can
trigger a restart that cannot bring the dependency back — a restart storm.

- **Two probes, split by cost.** `/api/health/live` is the liveness probe:
  deliberately cheap, it touches no external dependency and returns 200
  `{"status":"alive"}` whenever the worker can answer. `/api/health/ready` is
  the readiness probe: it runs the dependency checks and returns 503 when a
  critical dependency is down. `/api/health` is unchanged (the readiness
  payload) for backwards compatibility; the shared roll-up moved into
  `_compute_readiness()`.
- **The container HEALTHCHECK now uses liveness.** `Dockerfile.prod` probes
  `/api/health/live`, so a dependency outage no longer marks the container
  unhealthy; readiness is left for the reverse proxy / orchestrator to gate
  traffic on.
- **Pinned + tested.** `check_health_liveness_readiness_split` (40th check)
  asserts both routes exist, the liveness handler does not run the dependency
  roll-up, and the prod HEALTHCHECK uses liveness. Two new `HealthEndpointTests`
  prove liveness is cheap (no `checks` key, always 200) and readiness carries
  the dependency checks. Ticks the liveness/readiness box in
  `docs/PRODUCTION-READINESS.md` Wave 4.

## v9.107 — 2026-06-05 (production-readiness, wave 4: WEB_CONCURRENCY is no longer an inert knob)

`Dockerfile.prod` and `docker-compose.prod.yml` both advertise
`WEB_CONCURRENCY` as the worker-count knob (gunicorn's own convention), but
`gunicorn.conf.py` read only `POLARIS_WORKERS`. So an operator scaling the
stack with `WEB_CONCURRENCY=8` silently got the default 4 workers — and, with
no Redis configured, a per-worker in-memory rate limiter at 4x the intended
per-IP cap. The knob the deploy surface tells you to use did nothing.

- **The config honors both knobs.** `gunicorn.conf.py` now resolves
  `POLARIS_WORKERS` (explicit Polaris override) > `WEB_CONCURRENCY` (the deploy
  knob) > 4. The resolved count is still re-exported to `POLARIS_WORKERS` so
  `security.py`'s multi-worker detection (which warns when >1 worker runs
  without Redis) stays accurate regardless of which knob was set.
- **Bad values fall back, they don't crash.** A non-integer worker count
  resolves to 4 rather than raising during every worker boot.
- **Pinned + tested.** `check_web_concurrency_honored` (39th check) asserts the
  config reads `WEB_CONCURRENCY`; `GunicornConfigTests` (4 cases, in the CI app
  suite) proves the resolution: WEB_CONCURRENCY honored, POLARIS_WORKERS wins,
  default 4, bad value falls back. Ticks the WEB_CONCURRENCY box in
  `docs/PRODUCTION-READINESS.md` Wave 4.

## v9.106 — 2026-06-05 (production-readiness, wave 4: migrations bound their lock + statement time so one ALTER cannot stall the site)

A schema migration that needs an ACCESS EXCLUSIVE lock — most `ALTER TABLE`
forms — queues behind any open transaction and, once it acquires the lock,
blocks every read and write on that table until it finishes. The runner set no
timeouts, so the wait was unbounded: one slow background query in front of a
migration could stall all traffic on the table indefinitely. This is one of the
classic ways a routine deploy takes down a live database.

- **`lock_timeout` + `statement_timeout`, SET LOCAL in the apply transaction.**
  `polaris-migrate.sh` now sets both inside the `BEGIN; … COMMIT;` for every
  apply and revert. `lock_timeout` (default `3s`) makes a blocking migration
  ERROR fast and release the line instead of queueing in front of all other
  traffic; `statement_timeout` (default `60s`) caps a runaway migration. Both
  reset automatically at COMMIT (SET LOCAL) and are overridable for long,
  legitimate work via `POLARIS_MIGRATE_LOCK_TIMEOUT` /
  `POLARIS_MIGRATE_STATEMENT_TIMEOUT` (e.g. a big in-transaction index build).
- **Validated, not interpolated blindly.** The two values are interpolated into
  the SQL, so they are checked against `^[0-9]+(ms|s|min|h)?$` and the script
  refuses anything else (a `3s; DROP TABLE …` attempt exits with a usage error).
- **Pinned.** `check_migration_timeouts` (38th check) asserts the runner SET
  LOCALs both timeouts. Ticks the migration-timeout box in
  `docs/PRODUCTION-READINESS.md` Wave 4.

## v9.105 — 2026-06-05 (production-readiness, wave 4: no test frameworks in the prod image; dependency CVE scanning gates the build)

The dependency surface was pinned but never audited, and a single
`requirements.txt` mixed runtime packages with test tooling (pytest,
hypothesis, playwright). Both Docker images installed the whole file, so the
production image shipped a test framework that carried a CVE — `pip-audit`
flags pytest 8.4.2 (CVE-2025-71176). Test frameworks in a production image are
dead weight and pure extra attack surface.

- **Runtime / dev split.** `requirements.txt` is now the runtime surface only
  (what the images install); pytest, hypothesis, and playwright moved to a new
  `requirements-dev.txt` that pulls the runtime in via `-r requirements.txt`.
  The Docker images install `requirements.txt` — the production image no longer
  carries any test framework. CI and the macOS launcher's `test` path install
  the dev file (they run the suites); the launcher's run path stays lean.
- **CVE scanning, gating on what ships.** A new `cve-scan` CI job runs
  `pip-audit --strict` against `requirements.txt` — a known CVE in the
  production dependency surface now **fails the build**. The dev tooling is
  audited informationally (a test-tool CVE is surfaced but does not gate or
  ship). With pytest out of the runtime file, the gating audit is clean today.
- **Dependabot.** `.github/dependabot.yml` opens weekly update PRs for pip, the
  Rust ZK crate, and the GitHub Actions, so a new advisory is one review away.
- **Pinned.** `check_prod_image_no_test_deps` (asserts no test packages in the
  runtime file and that the images install it, not the dev file) and
  `check_cve_scanning` (asserts the gating `--strict` audit + Dependabot) are
  the 36th and 37th checks. Ticks the CVE-scanning box in
  `docs/PRODUCTION-READINESS.md` Wave 4.

## v9.104 — 2026-06-05 (production-readiness, wave 4: the /sql console is read-only at the engine, not just the keyword gate)

The operator SQL console refused writes with a first-keyword whitelist: only
`SELECT` and `WITH` were accepted. But `WITH` admits a data-modifying CTE —
`WITH gone AS (DELETE FROM Individual WHERE ... RETURNING *) SELECT * FROM gone`
starts with `WITH`, sails past the gate, and deletes. `polaris_app` holds DELETE
on the non-audit tables, so nothing below the app stopped it. The console was
write-capable through a CTE.

- **The session is now read-only at the database.** `sql_query` calls
  `conn.set_session(readonly=True)` immediately after connect, before any
  statement opens a transaction, so Postgres itself refuses every write —
  "cannot execute DELETE in a read-only transaction" — regardless of how the SQL
  is shaped. The keyword whitelist stays as a friendly early error; it is no
  longer the boundary.
- **The subtlety that needed a DB-backed test.** The first attempt issued `SET
  default_transaction_read_only = on` mid-transaction. It did nothing: psycopg2
  had already opened the transaction on the prior `SET statement_timeout`, and
  that GUC only binds transactions that begin after it. The CTE-DELETE still
  succeeded ("0 rows"). The new `test_data_modifying_cte_refused_by_db_readonly`
  caught it — it failed (write executed), then passed once the fix moved to
  `set_session(readonly=True)` before any statement. A static check alone would
  have green-lit the non-fix.
- **Pinned both ways.** `check_sql_console_readonly` (35th check) asserts the
  handler calls `set_session(readonly=True)`; the DB-backed test proves the
  engine actually refuses the CTE write. Ticks the SQL-console box in
  `docs/PRODUCTION-READINESS.md` Wave 4.

## v9.103 — 2026-06-05 (production-readiness, wave 2: real ML-DSA-65 signing, persistent key, tested in CI)

The defining gap between reference and reality: token signing was not real. The
default signed with a `sha3_256(token_value)` placeholder that authenticates
nothing, real ML-DSA-65 was never exercised in CI, and even with the flag on
`sign()` generated a fresh ephemeral keypair per call and threw the private key
away — so the public key was never stable and the signature was unverifiable
against any known anchor. This wave lays the real foundation:

- **Real ML-DSA-65 is now tested.** A dedicated `pqc-real` CI job installs
  liboqs-python and proves the real path end to end: it generates a keypair,
  signs with a persistent key, verifies (True), and confirms a forged message
  and a wrong key both fail. Real signatures are 3309 bytes, public keys 1952
  bytes (FIPS 204). liboqs builds and runs.
- **Persistent signing key.** `sign()` loads a long-lived keypair from
  `POLARIS_PQC_SIGNING_KEY_FILE` (JSON `{algorithm, secret_key_hex,
  public_key_hex}`) when set, so every signature uses the same key and its public
  key is a stable, publishable **trust anchor**. The ephemeral per-call keypair
  remains only as the dev/test fallback. A malformed key file fails loud (never
  silently degrades). `generate_keypair()` mints one; the real private key
  belongs in an HSM/KMS (operator-custodied) — this is the loading mechanism.

Still ahead in Wave 2 (tracked in `docs/PRODUCTION-READINESS.md`): store the
issuer public key as a DB trust anchor, store the real signature at issuance and
**enforce verification at use**, make real PQC the prod default (liboqs in the
prod image), and route uc6 through the signing module.

- `polaris_web/pqc_signing.py` — `_load_persistent_keypair`, `generate_keypair`,
  persistent-key `sign()`.
- `.github/workflows/ci.yml` — `pqc-real` job (real ML-DSA sign+verify).
- `polaris_web/test_pqc_signing.py` — `PersistentKeyTests` (skip without liboqs).
- `polaris_checks/checks.py` — `check_pqc_real_signing` (34th check).

## v9.102 — 2026-06-05 (production-readiness, wave 3: backups are encrypted at rest, DR doc made honest)

A database backup is a full `pg_dump` of the (would-be) national-identity
database. Shipping it as plaintext on local disk is a BLOCKER. `polaris-backup.sh`
now encrypts the tarball with AES-256-CBC (PBKDF2) when `POLARIS_BACKUP_KEY_FILE`
is set, removes the plaintext, and warns loudly when no key is configured;
integrity is covered by the SHA-256 MANIFEST inside, which the restore verifies
after decryption. `polaris-restore.sh` transparently decrypts `.enc` backups with
the same key and **fails closed** when the key is missing or wrong. Verified
end-to-end locally and in CI: the DR round-trip step now dumps → encrypts →
(negative: refuses without the key) → decrypts → restores → confirms the data.

`DR.md` is also reconciled: it had claimed a wired ≤1-minute RPO via
pgbackrest/WAL/S3 that does not exist. It now states the real RPO (the encrypted
`pg_dump` interval, ~24h) and presents continuous WAL archiving as the
not-yet-configured target (an operator-gated offsite-store decision).

- `scripts/polaris-backup.sh` — optional AES-256 at-rest encryption.
- `scripts/polaris-restore.sh` — decrypt `.enc` backups; fail closed without the key.
- `.github/workflows/ci.yml` — encrypted DR round-trip + no-key negative check.
- `docs/operator/DR.md` — honest RPO; `docs/PRODUCTION-READINESS.md` — Wave 3 ticks.
- `polaris_checks/checks.py` — `check_backup_encryption` (33rd check).

## v9.101 — 2026-06-05 (production-readiness, wave 1: no default credentials, real rate limiting, honest roadmap)

The maintainer asked to make Polaris production-ready. A six-dimension assessment
found 49 properties already production-grade (the seven review passes built a real
base), 45 engineering gaps an agent can close, and 10 that need operator/legal
decisions. The honest gap ledger is now `docs/PRODUCTION-READINESS.md` — nothing
here flips the project to "production-ready"; that claim only becomes true as the
boxes are checked. Wave 1 closes the two BLOCKERs that are pure default-hygiene:

**Demo credentials no longer reach a production database.** The SQL seed loads
`admin/Admin@123!`, `operator/Operator@123!`, `auditor/Auditor@123!` and a demo
duress code — fine for dev, an instant full compromise in production. In
`POLARIS_ENV=production`, `docker-init.sh` now disables those accounts
(is_active=FALSE), scrambles their passwords (so re-enabling can't restore the
known password), locks them, and clears the demo duress enrollment. Rows are
disabled, not deleted, because the append-only audit tables FK to AppUser. The
operator bootstraps the first real admin with `scripts/polaris-create-operator.sh`;
no default credentials ship and `/login` refuses everyone until then.

**The rate limiter actually uses Redis in production.** The prod compose ran a
Redis service but never set `POLARIS_REDIS_URL`, so `security.py` silently fell
back to per-worker in-memory buckets — and prod runs 4 gunicorn workers, so per-IP
brute-force limits fragmented 4x. Now wired to `redis://redis:6379/0`, so the
atomic cross-worker Redis limiter is used.

- `polaris_web/docker-init.sh` — neutralize demo accounts + demo duress code in
  production.
- `polaris_web/docker-compose.prod.yml` — `POLARIS_REDIS_URL`; `POLARIS_ENV` to
  the postgres init container.
- `polaris_checks/checks.py` — `check_prod_hardening` (32nd check) pins both.
- `docs/PRODUCTION-READINESS.md` — the honest roadmap; linked from ROADMAP.

## v9.100 — 2026-06-05 (a successful restore looked like a failure — DR path fixed + CI-validated)

Applying the prod-image lesson (untested operator tooling is silently broken) to
the disaster-recovery path: a backup -> restore round-trip against the test DB
revealed that **a successful restore reported failure**. `pg_restore` returns a
non-zero exit for benign reasons — the `--clean --if-exists` DROPs of
not-yet-existing objects, and version-specific SET directives a newer `pg_dump`
emits that an older target rejects (e.g. `SET transaction_timeout` from a PG17+
dump into PG16). `polaris-restore.sh` treated that exit code as a hard failure
and aborted with "✗ pg_restore failed — DB state may be partial," even though all
30 tables and every row had restored. For a DR tool, that false alarm is the
worst kind: an operator mid-disaster sees "failed," and may discard a perfectly
good restore or thrash.

The restore now judges success by **verifying the outcome** — the core schema
(`identitytoken`) must be present after `pg_restore` — not by the exit code. A
real failure (no schema) still aborts; a benign-warning success reports complete
with a one-line note that the data is verified present. Verified locally: the
same PG18-dump-into-PG16 case now reports success, exit 0.

And the DR path joins the images in CI: a new round-trip step dumps the loaded
DB, restores it into a fresh database, and asserts the data came back — so a
broken backup or restore fails CI, not a real recovery.

- `scripts/polaris-restore.sh` — verify the restored schema; do not fail on
  benign `pg_restore` warnings.
- `.github/workflows/ci.yml` — backup + restore round-trip in the test job.

## v9.99 — 2026-06-05 (launcher: tear the stack down exactly once)

The last of the launcher-audit robustness items. Watch mode has three teardown
paths — the browser quit beacon, the stale-heartbeat timeout, and the
INT/TERM/HUP trap — and the trap was not self-disabling, so a second signal
during teardown (a double Ctrl+C) or a beacon racing the trap re-entered
`stop_all`, printing a spurious banner and a misleading "Nothing running." A new
`_teardown_once` guard runs the teardown once and disarms the trap as soon as it
begins; all three paths route through it. Verified: a second call is a clean
no-op.

(The other audit item — `preflight_port` whitelisting any `python` listener — is
left as is on purpose: the broad match is what lets the launcher recognise and
restart its own prior gunicorn, and tightening it via PID matching would risk
breaking that common relaunch path for a rare edge case.)

- `polaris_mac_launch.sh` — `_teardown_once` guard; the trap and both watch-loop
  teardown paths use it.

## v9.98 — 2026-06-05 (the production image could not be built — fixed and CI-validated)

Investigating whether CI should validate the prod image surfaced that the prod
image **could not be built at all**. `Dockerfile.prod`'s Rust stage COPYs
`polaris_zk/` (a sibling of `polaris_web/`, so it needs the repo root as the
build context), while its app stages COPY bare `app.py` / `static/` / `templates/`
(which only resolve from a `polaris_web/` context). Docker COPY cannot escape its
context, so no single context satisfies both — and `polaris-deploy.sh prod`
(which runs `docker compose -f docker-compose.prod.yml build`, context
`polaris_web/`) failed at the Rust stage. The deploy artifact was broken.

The fix: build from the repo root, with repo-root-relative app paths.
`docker-compose.prod.yml` now sets `context: ..` + `dockerfile:
polaris_web/Dockerfile.prod`, and every app-file COPY in `Dockerfile.prod` is
prefixed `polaris_web/`. Verified: the prod image now builds (multi-stage Rust +
Python) and boots — gunicorn brings up all four workers with no import crash.

To keep it that way, the `docker-image` CI job now also builds the prod image
(buildx + gha cache, so the Rust layer stays warm) and smoke-boots it (asserts
the gunicorn workers come up and the logs carry no `ModuleNotFoundError` /
`ImportError` / `Traceback`). Both Polaris images — dev (built + booted + route-
smoked) and prod (built + boot-smoked) — are now validated on every push.

- `polaris_web/Dockerfile.prod` — repo-root-relative app COPY paths + a context note.
- `polaris_web/docker-compose.prod.yml` — `context: ..`, `dockerfile: polaris_web/Dockerfile.prod`.
- `.github/workflows/ci.yml` — build + boot-smoke the prod image (buildx@v4,
  build-push@v7, current majors).

## v9.97 — 2026-06-05 (the launcher is honest about the Docker ZK degradation)

The Docker dev image ships without the Rust ZK prover by design (README: "the
compiled binary does not ship; the app degrades gracefully"). The native path
builds it (v9.93), but on the Docker path that degradation was silent — a user
only found out when `/api/zk/verify` returned a 400. The project's discipline is
no silent degradation, so the launcher now says it at bring-up: the Docker dev
image has no ZK prover, every page serves and `/epochs` renders the seeded
epochs, only NEW epoch close/verify need it, and `up --native` gives the full ZK
demo. Nothing is hidden; the user knows exactly what works and how to get the
rest.

Also: `--help` no longer leads with the machine-readable `AI-context:` line. It
starts at the human title (the audit flagged this).

- `polaris_mac_launch.sh` — docker post-launch hints state the ZK degradation +
  the `--native` path to it; `usage()` skips the AI-context header line.

## v9.96 — 2026-06-05 (the launcher tells you WHY it failed)

When the v9.94 Docker crash happened, the launcher printed "Web app failed to
start. View logs: ./polaris_mac_launch.sh logs app" and stopped there. The actual
cause (`ModuleNotFoundError: No module named 'pqc_signing'`) was one `logs app`
command away, but the launcher made you go find it. A launch tool should hand you
the error, not a place to look for it.

The docker bring-up failure path now prints the diagnosis inline: the app
container state (including restart count, the crash-loop tell), and the last 30
lines of the app log — which is exactly where the real startup error lives. It
also distinguishes the two failure modes that used to collapse into one opaque
message: it no longer proceeds to wait for the web app when the database never
became healthy (the app cannot start without it), and it shows the db logs in
that case. The native path got the same treatment — on a gunicorn boot failure it
prints the last 30 log lines instead of just telling you to tail them.

Verified end-to-end: a fresh `up --docker` still brings the stack up clean
(database healthy → LIVE → 200), and the diagnostic dump surfaces the container
state + recent logs.

- `polaris_mac_launch.sh` — `_wait_db_healthy` + `_report_docker_bringup_failure`
  helpers; the heal path gates the app wait on real DB health; native failure
  dumps the log tail.

## v9.95 — 2026-06-05 (CI now builds and boots the Docker image)

v9.94 fixed the missing-module crash and added a static check that the COPY list
covers `app.py`'s imports. But the deeper reason a broken image shipped green for
~36 versions is that **CI never built or ran the image** — the `test` job
exercises the app code against a native Postgres. A bad build step, a runtime
import error from a transitive module, or a broken entrypoint would still pass.

A new `docker-image` CI job builds the dev image, brings up the full stack
(`docker compose up -d --build`), waits for the app to serve `/api/health`, and
smoke-tests `/login`, `/api/health`, and `/metrics` (all 200), then tears down.
It runs in parallel with the `test` job. The exact v9.94 failure
(`ModuleNotFoundError` crash-loop) now fails this job with the container logs
attached, instead of surfacing on a user's machine.

- `.github/workflows/ci.yml` — new `docker-image` build + boot smoke-test job.
- `polaris_web/docker-compose.yml` — drop the obsolete top-level `version: '3.9'`
  key (Compose v2 ignores it and warns; it showed up in the crash logs).

## v9.94 — 2026-06-05 (the Docker image was missing pqc_signing.py — crash-loop fixed and guarded)

The Docker path crash-looped on startup: `ModuleNotFoundError: No module named
'pqc_signing'`. `app.py` has imported `pqc_signing` since v9.58, but neither
`Dockerfile` nor `Dockerfile.prod` was updated to COPY it into the image, so the
gunicorn worker failed to boot and the container restarted forever. The native
path was unaffected (it runs `app.py` from the source tree), which is why this
stayed latent until a Docker launch hit it — the launcher's default when Docker
Desktop is installed.

Both Dockerfiles now COPY `pqc_signing.py`. Verified: a rebuilt image comes up
healthy and serves `/login`, `/metrics`, and `/api/health` (all 200).

This is the same class of bug that bit `observability.py` in v9.40 — a local
module added to `app.py`'s imports but not to the image COPY — and the only guard
was a narrow doctor check hard-coded to `security.py`. A new machine check closes
the class generally:

- `polaris_web/Dockerfile`, `polaris_web/Dockerfile.prod` — COPY `pqc_signing.py`.
- `polaris_checks/checks.py` — `check_dockerfile_copies_app_modules` (31st check)
  resolves every LOCAL module `app.py` imports (tolerating trailing comments, the
  v9.40 failure mode) and asserts BOTH images COPY each one. `test_checks.py`
  discriminates across the dev-missing, prod-missing, and complete cases.

## v9.93 — 2026-06-05 (the macOS launcher: current, faster, and pinned)

The launcher (`polaris_mac_launch.sh`, header was v2.5 / 2026-05-08) had drifted
~37 ships behind the stack. A six-dimension audit (deps, ZK binary, test runner,
startup speed, stack parity, robustness) surfaced the gaps; the load-bearing ones
are fixed and pinned with a check.

**Native dependencies (HIGH).** The native path hard-coded `pip install flask
psycopg2-binary gunicorn werkzeug webauthn` — 5 unpinned packages — while the
Docker image and CI both install from `requirements.txt` (23 pinned). It missed
`prometheus_client` (so `/metrics` was dead), `redis` (so cross-worker rate
limiting fell back to per-worker in-memory under the 2 workers it runs), and
`hypothesis` + `pytest` (so the property and ZK two-witness suites ImportError'd).
The native path now installs from `requirements.txt`, skipping the install when
the file is unchanged (sha256 marker). The venv is recreated when it is not
Python 3.12 (an older interpreter cannot install the pinned set).

**ZK prover (HIGH).** Neither launch path built the Rust `polaris-zk` binary, so
`/api/zk/*` was silently dead on a fresh extraction — the headline
zero-knowledge feature off with no warning. A new `build_zk_binary()` builds it
when cargo is present (mtime-cached so warm relaunches pay nothing), exports
`POLARIS_ZK_BINARY`, and degrades cleanly with a clear message when Rust is
absent. (The dev Docker image still omits it by design — a macOS host binary
cannot run in the Linux container; `doctor` says so.)

**Test runner (HIGH).** `test` ran only `test_app.py` + `test_cli.py`. It now runs
the canonical suite from CLAUDE.md/CI: `polaris_checks.run`, the four DB web
suites (constraints, invariants, redaction, app), the CLI suite, the ZK
two-witness pytest suites, and the cargo circuit tests — in the venv, via
`-m unittest`, against the loaded DB (no live app needed).

**Startup speed + safety (MEDIUM).** `brew install` runs only for missing
formulae; the schema reload is skipped when the DB is already loaded (the old
code re-ran `00_load_all.sql` on every launch, which TRUNCATEs every table and
wiped user data); native gunicorn now connects as the unprivileged `polaris_app`
role (explicit creds), so the native run exercises the same v9.85 append-only
boundary as production instead of leaning on localhost trust as a superuser.

- `polaris_mac_launch.sh` — all of the above + `doctor` now reports venv-vs-
  requirements, the ZK binary, and the Rust toolchain; `reset` drops the native
  DB so the next `up` reloads; header bumped to v2.6.
- `polaris_web/docker-compose.yml` — drop a stale `soldier_log_tail` comment
  (removed v9.55 apparatus).
- `polaris_checks/checks.py` — `check_launcher_current` (30th check) pins the
  three properties that drifted: deps from requirements.txt, the canonical test
  suite, and the ZK build. `test_checks.py` discriminates across four cases.

## v9.92 — 2026-06-04 (un-stale the README table count, and guard it)

The honesty pass turned up one more drift: `README.md` said "26 schema tables"
while the schema reached 27 in v9.89 (the `ZkVerificationNonce` anti-replay
store). `check_table_count_matches_doc` only guarded
`docs/ARCHITECTURE-OVERVIEW.md`, so the README count drifted unchecked — the
same class of stale-doc defect this honesty pass exists to close.

- `README.md` — "26 schema tables" → "27 schema tables".
- `polaris_checks/checks.py` — `check_table_count_matches_doc` now guards BOTH
  the architecture doc ("N tables") and the README ("N schema tables") against
  the real `CREATE TABLE` count, so neither can drift unnoticed again.
  `test_checks.py` covers the new README path (architecture-doc-correct-but-
  README-drifts now FAILs).

## v9.91 — 2026-06-04 (honesty: the thesis terminus passed, so the docs now say so)

With the forward roadmap's actionable items shipped, a multi-agent honesty audit
swept every headline claim (thesis, post-quantum, zero-knowledge, compulsion-
resistance, general "production/validated/proven" language) against what the code
actually does. The verified finding is the one the ROADMAP already flagged as an
**active dishonesty**: the thesis terminus.

`MISSION.md`'s freeze line carries a mechanical abandonment clause: "if no
cold-read attempt occurs by v9.40 ... the thesis is documented as inconclusive
and the strong claim is retired permanently." No external cold read ever happened
(only the author's own walkthrough, which `docs/THESIS.md` itself admits is not a
cold read), and the repository is now far past v9.40. So the outcome was already
decided by the constitution. But `docs/THESIS.md` still read as an *open*
experiment: status `HYPOTHESIS-NOT-VERIFIED`, "the thesis is not refuted, it is
unverified," "keep the status honest until a real cold read happens." Leaving the
softer wording past the deadline is itself the dishonesty the project forbids.
`THESIS.md` also never actually stated the v9.40 terminus that `MISSION.md` cites
it for.

`docs/THESIS.md` now reflects the terminal state the constitution mandates: status
**INCONCLUSIVE**, the strong legibility claim **retired permanently**, the v9.40
terminus stated explicitly, and the disposition closed by default (a future cold
read could reopen it only through an explicit, recorded maintainer decision, never
an automatic flip). The falsification test stays documented for anyone who later
runs it. `MISSION.md`'s freeze line is untouched (it is un-amendable here); this
only makes `THESIS.md` honor it.

Two README accuracy fixes rode along: a hardcoded "Now shipping v9.63" that had
gone 28 versions stale is now a non-versioned "the latest release" link, and the
"the operational default is already post-quantum" line is scoped to the algorithm
of record (the real ML-DSA-65 signature bytes need `POLARIS_USE_REAL_PQC=1`; the
default build records a deterministic placeholder, as the crypto section already
disclosed six lines down).

- `docs/THESIS.md` — status + terminus + retirement, reconciled throughout.
- `README.md` — un-stale the version link; scope the post-quantum-default claim.
- `polaris_checks/checks.py` — `check_thesis_terminus_honest` (29th check):
  past v9.40, `THESIS.md` must read as retired/inconclusive, never the open
  framing. Version-aware; `test_checks.py` discriminates across five cases.

## v9.90 — 2026-06-04 (CI: bump the deprecated Node 20 actions ahead of the deadline)

CI was annotating every run: `actions/checkout@v4` and `actions/setup-python@v5`
run on Node.js 20, which GitHub force-migrates to Node 24 on **2026-06-16** and
removes on **2026-09-16**. Bumped both to the current major (verified latest via
the GitHub API: `checkout@v6.0.3`, `setup-python@v6.2.0`), which run on Node 24:

- `.github/workflows/ci.yml` — `actions/checkout@v4` → `@v6`,
  `actions/setup-python@v5` → `@v6`.

A pure CI-hygiene change; the workflow's own green run on the bumped actions is
the verification. Clears ROADMAP "Next ships" #3.

## v9.89 — 2026-06-04 (real anti-replay: /api/zk/verify consumes a single-use nonce)

The review arc converged at v9.88, so this picks up the top of the forward
ROADMAP. `/api/zk/verify` binds a proof to `(epoch_id, context_id, nonce)`. That
binding prevents proof *substitution*, but on its own it does NOT prevent
*replay*: a verified bundle, captured off the wire, verifies again every time it
is resubmitted. The R2 "replay resistance" claim was only true for substitution.

`/api/zk/verify` now consumes the nonce. On a verified result it inserts
`(epoch_id, context_id, nonce)` into a new single-use store; a second submission
of the same tuple hits the primary key (`INSERT ... ON CONFLICT DO NOTHING`
returns no row) and is rejected with `verified: false, reason: "nonce already
consumed (replay)"`. Consumption happens only *after* a true verify, so a failed
proof never burns a nonce a legitimate later proof might use, and the insert is
atomic so two concurrent replays serialize on the PK — exactly one wins. Closes
threat-model T-T2; makes R2 hold in code.

The store holds **no identity** — only the spent `(epoch, context, nonce)` tuple
and the consume time, so it cannot say *who* verified, only that this tuple was
spent (Vocation). It is append-only at the privilege layer: `09_grants.sql`
revokes UPDATE/DELETE on it from `polaris_app`, because a consumed nonce must
never be un-consumed (that re-opens the replay window).

- `polaris_sql/01_schema.sql` — new `ZkVerificationNonce` table (27 tables now).
- `polaris_sql/migrations/2026-06-04-001-zk-verification-nonce.{up,down}.sql` —
  the table + append-only REVOKE for already-deployed databases.
- `polaris_sql/04_data.sql` — added to the reload TRUNCATE set (test isolation).
- `polaris_sql/09_grants.sql` — UPDATE/DELETE revoked from `polaris_app`.
- `polaris_web/app.py` — `/api/zk/verify` consumes the nonce, rejects replays.
- `polaris_checks/checks.py` — `check_zk_verify_anti_replay` (28th check).
- `polaris_web/test_app.py` — `test_api_zk_verify_replay_is_rejected` (e2e:
  first verify succeeds, the identical bundle is rejected, nonce recorded once).

## v9.88 — 2026-06-04 (pass 7 converges: a false redaction comment, and a Vocation guard for the evidence trail)

A seventh adversarial review pass over six surfaces no prior pass had swept:
template/DOM XSS, crypto-correctness (the ML-DSA-65 vs SHA3 placeholder path),
C6 disclosure on the non-atlas read paths, the multi-step token state machine,
the witness2 second-witness math, and audit-record content through the
anti-coercion lens. **Zero security defects survived verification** — the
hardening arc has converged. The one actionable item was a documentation defect.

**A schema comment falsely claimed a column was ZK-redacted (LOW).**
`VerificationEvent.requesting_purpose_text` (the operator-supplied reason for a
verification) carried the inline comment "Like requestor_location, it is
identifying-disclosure and is redacted for ZERO_KNOWLEDGE rows at read." That is
false on both counts. The column is written on every disclosure level and is
redacted *nowhere* — by design: it is the anti-coercion evidentiary trail (a
coerced verification leaves the coercer's stated purpose on the permanent
record; see migration `2026-05-15-002` and the verifications form's own help
text). `requestor_location`, by contrast, genuinely *is* ZK-redacted at the read
paths (C6, pass-3). A future engineer trusting the comment would either assume a
protection that does not exist or "fix" the missing redaction and silently
destroy the Vocation feature.

The comment is corrected to describe the deliberate retention (and to note it
does not weaken C2 — a ZERO_KNOWLEDGE row still carries no `token_id`). To stop
the confusion from recurring as a real regression, a new Vocation check now
guards the evidence trail:

- `polaris_sql/01_schema.sql` — accurate comment on `requesting_purpose_text`.
- `polaris_checks/checks.py` — `check_coercion_evidence_retained` (27th check):
  fails if the schema falsely documents the trail as ZK-redacted, or if any read
  path NULLs it for ZERO_KNOWLEDGE rows (which would destroy the anti-coercion
  evidence). `test_checks.py` discriminates across four cases.

With pass 7 returning no security findings, the multi-pass adversarial review
(v9.64–v9.88, ~37 real findings fixed across seven passes) has converged.

## v9.87 — 2026-06-04 (pass 6: close the two trust-boundary gaps prior passes left)

A sixth adversarial review pass (six surfaces not deeply covered before: the
un-reviewed procedures, the ZK subprocess boundary, session/auth internals,
transaction-isolation concurrency, route input/authz, migration/AoR integrity).
Four of six dimensions came back clean; two findings survived independent
verification. Both are cases where an earlier pass closed a *class* of issue but
left exactly one path uncovered.

**`verify()` panicked on a malformed proof (MEDIUM).** v9.84 added a bounds
check to `prove()` and the CHANGELOG claimed "compute-root/compute-leaves/verify
all return clean Errs for malformed input." `verify()` did not. It ran
`ProofWithPublicInputs::from_bytes(...)?` and then indexed
`proof.public_inputs[0..4]` (and `[4]`, `[5]`, `[6]`) with no length check.
Plonky2's `from_bytes` reads the public-input *count* straight from the
caller-supplied buffer and does not constrain it to the circuit's count until
the cryptographic verify, so a crafted proof deserializes `Ok` with a short
`public_inputs` vector and the slice panics — process abort (exit 101).
Reproduced deterministically: an all-zero `proof_hex` the length of a real proof
(155600 hex chars) crashed at `lib.rs:329`. Reachable by any authenticated user
via `POST /api/zk/verify`. It is fail-closed (the panic is before
`verifier_data.verify()`, so it can never make an invalid proof verify true) and
each verify is an isolated per-request subprocess (the crash is contained to that
child, HTTP 400 — not a worker DoS), hence MEDIUM. `verify()` now returns
`Ok(false)` when `public_inputs.len() < 7`. Confirmed: the same input now returns
`{"verified":false}`, exit 0.

**Inactive-account login was a timing oracle (LOW).** `authenticate()` defends
the unknown-user path with a dummy scrypt verify so a not-found username costs
the same as an active account with a wrong password. But the inactive-account
branch (`if not user['is_active']`) returned *before* any hashing — ~0ms vs
~scrypt — so an unauthenticated attacker could enumerate deactivated accounts by
response time (CWE-208), the exact leak the dummy hash closes for not-found
users. The password verify now runs *before* the inactive/locked branching, so
every existing-user path does the same scrypt work.

- `polaris_zk/src/lib.rs` — `verify()` length guard + `verify_rejects_malformed_proof_without_panicking` (8 ZK tests).
- `polaris_web/security.py` — hash before the account-state branch.
- `polaris_web/test_app.py` — `test_inactive_account_is_not_a_timing_oracle` (spies on the hash call; deterministic, not wall-clock).

## v9.86 — 2026-06-04 (prod syncs the polaris_app role password to the generated secret)

A deploy finding from the fifth review pass. In the production stack the app and
pgbouncer both authenticate as `polaris_app` using the file-mounted secret
`/run/secrets/polaris_db_password`. But `09_grants.sql` creates the role with the
dev default `'polaris_dev_password'`, and the **postgres** service never set
`POLARIS_APP_PASSWORD`, so `docker-init.sh` skipped its rotation block: the role
kept the dev password while every client presented the generated one. The result
is either a broken prod stack (authentication fails) or — if a deployer papered
over it by reusing the dev string — the dev password live in production.

`docker-init.sh` already had the ALTER-ROLE machinery; it was simply never fed
the secret. Now:

- **docker-compose.prod.yml** — the postgres service sets
  `POLARIS_APP_PASSWORD_FILE: /run/secrets/polaris_db_password`, the SAME secret
  the app reads. (The secret was already mounted into the service.)
- **docker-init.sh** — reads `POLARIS_APP_PASSWORD_FILE` (the `*_FILE` convention
  the rest of the stack uses, G28) and ALTERs `polaris_app` to it. `cat` strips
  the trailing newline, matching the app's `_read_secret_file().read().strip()`,
  so the role password and the clients' password compare byte-for-byte.
- The complexity gate is now entropy-aware: the absolute floor is 16 chars; a
  password under 24 chars must still mix digit + letter + symbol, but a 24+ char
  secret passes on length alone — the generated secret is 48 hex chars
  (`openssl rand -hex 24`, ~192 bits) and has no symbol by construction, so the
  old blanket symbol rule would have rejected our own secret.
- **polaris_checks** — `check_prod_app_password_synced` (26th check) asserts the
  compose role-password secret matches the app's and that docker-init reads it
  and ALTERs the role. `test_checks.py` discriminates across five failure modes.

## v9.85 — 2026-06-04 (C1 append-only becomes a privilege boundary, not only a trigger)

The thesis finding from the fifth review pass. C1 — audit-of-record, enforced at
the database level — was enforced only by the `reject_audit_modification()`
trigger, and that trigger has a carve-out: it permits UPDATE/DELETE when the
custom GUC `polaris.purge_in_progress` is `'TRUE'`. Any role can `SET` a custom
GUC. So the application role could bypass the whole append-only invariant:

```sql
-- as polaris_app, before v9.85:
SET LOCAL polaris.purge_in_progress = 'TRUE';
DELETE FROM TokenLifecycleEvent WHERE event_id = ...;   -- DELETE 1  (forged history)
```

Confirmed empirically against the live role. The trigger was the only thing
standing between `polaris_app` and a rewritten audit-of-record — exactly the
property C1 exists to make impossible.

**The grant model now backs the trigger.** `polaris_app` keeps SELECT + INSERT
(append-only IS insert-allowed) but loses UPDATE/DELETE on every append-only
table: TokenLifecycleEvent, VerificationEvent, EnrollmentStatusEvent, AnchorBatch,
TokenStateEpochLeaf, DuressEvent, AuthAuditLog, and AuditAccessLog. Now the
carve-out is unreachable from the app role — the ACL refuses the statement before
the trigger ever fires:

```sql
-- as polaris_app, v9.85:
SET LOCAL polaris.purge_in_progress = 'TRUE';
DELETE FROM TokenLifecycleEvent WHERE event_id = ...;   -- ERROR: permission denied
```

The one legitimate DELETE path, `uc_archive_purge`, is now `SECURITY DEFINER`
(with a pinned `search_path`) so it runs the purge with the procedure owner's
rights inside its existing admin-gated, checkpoint-writing transaction. It
authenticates the actor by the `p_actor_user_id` PARAMETER against `AppUser.role`
— never `current_user`/`session_user` — so elevating to the owner does not weaken
the admin gate. Verified: an admin purge still deletes; `polaris_app` calling it
still works; direct UPDATE/DELETE stays denied; INSERT still succeeds.

- `polaris_sql/09_grants.sql` — REVOKE UPDATE, DELETE on the base append-only
  tables from `polaris_app` (to_regclass-guarded loop, robust to load order).
- `polaris_sql/migrations/2026-05-15-003-audit-access-log.up.sql` — carries the
  matching REVOKE for the table it adds.
- `polaris_sql/05_procedures.sql` — `uc_archive_purge` is SECURITY DEFINER.
- `polaris_checks/checks.py` — `check_aor_privilege_boundary` (C1, 25th check):
  asserts the REVOKEs and the SECURITY DEFINER declaration. `test_checks.py`
  discriminates across five failure modes.
- `polaris_web/test_check_constraints.py` — `TestC1PrivilegeBoundary` opens an
  explicit `polaris_app` connection and proves the boundary end to end.

## v9.84 — 2026-06-04 (uc1 refuses deprecated algorithms; the ZK prover bounds-checks its index)

Two findings from a fifth review pass (the procedures uc1-uc6 and the Rust crate).

**uc1 minted tokens under a deprecated algorithm (MEDIUM).** `uc1_issue_and_activate`
validated only that the issuing agency held ISSUE/BOTH authorization on the
algorithm — never its `deprecation_date`. So a brand-new ACTIVE token could be
issued under a retired/weakened (potentially pre-quantum) algorithm.
`uc6_migrate_algorithm` already refuses to migrate a token *to* a deprecated
algorithm, so the system already treats "deprecated" as a state that must block new
signatures — uc1 was the asymmetric gap. uc1 now performs the same deprecation
check before any writes.

**The ZK prover panicked on an out-of-range index (LOW).** `polaris_zk::prove`
used the caller-supplied `leaf_index` (`all_leaves_hex[leaf_index]`, and inside
plonky2) with no bounds check, so an index past the real leaf count aborted the
process (exit 101) instead of returning an error — `compute-root`/`compute-leaves`/
`verify` all return clean `Err`s for malformed input. `prove` now validates
`leaf_index < all_leaves_hex.len()` and returns the crate's `Result` error.

- `polaris_sql/05_procedures.sql` — uc1 deprecation guard.
- `polaris_zk/src/lib.rs` — `prove` index bounds check.
- `polaris_web/test_check_constraints.py` — `TestUC1Issuance` (deprecated rejected,
  live succeeds). Rust: the 7 circuit tests pass; the binary returns a clean error.

## v9.83 — 2026-06-04 (bound three unbounded resources an attacker could grow)

The fourth review pass found three places where memory or metric cardinality grew
without bound, the last two reachable by an unauthenticated / IP-rotating client.

- **Prometheus `/metrics` cardinality (MEDIUM, memory DoS).** The per-request
  metric label was `request.endpoint or request.path or 'unknown'`. On a 404,
  `request.endpoint` is None, so the label fell back to the raw, attacker-controlled
  URL path — every `GET /<random>` minted a new label series (~1 counter + ~15
  histogram buckets) that the Prometheus client retains for the process lifetime.
  Now the label is `request.endpoint or 'unmatched'` (a bounded set; no path).
- **In-memory rate-limiter key map (LOW, slow memory leak).** `_buckets` was a
  `defaultdict(deque)` that accrued one entry per distinct `login:<ip>` /
  `write:<ip>` key forever (an attacker rotating IPs, or spoofing `X-Forwarded-For`
  under `POLARIS_TRUST_PROXY`, leaks one entry each). It is now an LRU-ordered
  `OrderedDict` capped at 50,000 keys, evicting least-recently-used beyond the cap.
- **Dashboard `ActiveTokens` query (LOW).** The default post-login landing page ran
  `SELECT * FROM ActiveTokens` with no bound, materializing every active token on
  every load — the exact national-scale hazard `individuals_list` paginates against.
  Capped to the 200 most recent.

- `polaris_web/app.py` — metric label bounded; dashboard query capped.
- `polaris_web/security.py` — `InMemoryRateLimiter` is an LRU-capped `OrderedDict`.
- `polaris_web/test_app.py` — `ResourceBoundTests`: the key map stays bounded; a
  404 path never appears as a metric label.

## v9.82 — 2026-06-04 (duress: record off the request thread so the response time reveals nothing)

The whole point of the duress mechanism is that a coerced verification is
indistinguishable from a normal one. But the duress-match branch did strictly
more synchronous work than a non-match: on a match it opened a SECOND database
connection and committed (a WAL fsync) before the request returned, a
deterministic added latency a coercer timing the response could measure to
distinguish a duress code from a real one. The docstring's claim that the variance
was "dominated by Flask overhead" understated this.

Fix: the silent DuressEvent is recorded on a background daemon thread by default,
so the synchronous response time is identical whether or not a duress code
matched (the request returns after a microsecond-scale thread spawn regardless of
outcome). Durability is verified by a test that polls for the async write;
operators who prefer the alarm committed before the response returns can set
`POLARIS_DURESS_SYNC=1` (tests use it for deterministic assertions).

Also documented honestly that duress is inherently token-bound (the silent alarm
must identify the token to look up its enrolled hash), so it cannot apply to a
pure ZERO_KNOWLEDGE verification that deliberately hides the token — the form
field now notes it applies only with a token reference, rather than implying it
works everywhere.

- `polaris_web/app.py` — `_record_duress_async` + the default-async dispatch; the
  R2 timing note corrected; the ZK-duress limitation documented at the call site.
- `polaris_web/templates/verifications_form.html` — the duress field notes it
  applies only with the token reference (kept obfuscated, no "duress" wording).
- `polaris_web/test_app.py` — sync-mode determinism + an async-durability test.

## v9.81 — 2026-06-04 (the no-cascade invariant now covers migrations, and the one live cascade is resolved)

The fourth review pass found that `check_no_fk_cascade` — which enforces the
no-`ON DELETE/UPDATE CASCADE` invariant (no silent cascade deletion) — globbed only
top-level `polaris_sql/*.sql`, not `migrations/`. The one cascade in the whole tree,
`OperatorWebauthnCredential.user_id REFERENCES AppUser ON DELETE CASCADE` (migration
2026-05-14-002), was therefore live and unflagged — and the gap let any future
migration smuggle in a genuinely destructive cascade (e.g. on an audit-of-record FK)
past a green check.

Fix: `check_no_fk_cascade` now scans the base schema AND every migration, and the
cascade is resolved to `ON DELETE NO ACTION` (the schema-wide default). Deletion of
an operator with enrolled WebAuthn credentials is now explicit — the credentials
must be removed first — rather than a silent cascade; operators are deactivated, not
deleted, in normal operation, and credential lookup is unaffected.

- `polaris_checks/checks.py` — `check_no_fk_cascade` scans `migrations/` too
  (+ detection test placing a cascade in a migration fixture).
- `polaris_sql/migrations/2026-05-14-002-operator-webauthn.up.sql` — the FK is
  `ON DELETE NO ACTION`. Verified: a fresh build's FK is NO ACTION, webauthn green.

## v9.80 — 2026-06-04 (operator scripts: validate argv to close four SQL injections)

A fourth review pass (residual surfaces: anchoring, dashboard, duress, schema
constraints, observability, operator scripts) found the operator shell scripts
interpolate unvalidated argv straight into superuser `psql -c` statements. Since
`psql -c` runs multiple semicolon-separated statements, a crafted argument
executes arbitrary SQL as `postgres`:

- **`polaris-recover-admin.sh --target`** (HIGH) — the emergency password-login
  recovery flow; `--target` was only checked non-empty, then interpolated into
  three `psql -c` statements (the recovery-code hash lookup, the admin check, the
  audit INSERT). A value like `x'; <SQL>; --` injects, and an `' OR '1'='1`-style
  value could subvert which row's recovery hash is compared.
- **`polaris-purge.sh --actor-user-id`** (HIGH) — the one script whose job is to
  DELETE from audit tables; `--actor-user-id` was interpolated bare into the
  destructive `CALL uc_archive_purge(...)`.
- **`polaris-migrate.sh --actor-user-id`** (MEDIUM) — interpolated into the
  append-only `schema_version` INSERT.
- **`polaris-archive.sh --cutoff-days`** (MEDIUM) — interpolated into an
  `interval '... days'` literal it could break out of.

Fix: each SQL-bound argument is now regex-validated immediately after parsing —
usernames against `^[a-z0-9._-]{3,50}$`, ids/days against `^[0-9]+$` (migrate
also allows the `NULL` default) — and the script exits with a usage error before
any psql runs. `check_operator_scripts_validate_argv` guards all four (the check
layer is now 24).

- `scripts/polaris-recover-admin.sh`, `polaris-purge.sh`, `polaris-migrate.sh`,
  `polaris-archive.sh` — argv validation.
- `polaris_checks/checks.py` — `check_operator_scripts_validate_argv` + detection.

## v9.79 — 2026-06-04 (schema completeness: 01_schema.sql declares every column the app writes)

The review noted that `VerificationEvent.requesting_purpose_text` existed only in
a migration, not in `01_schema.sql`'s `CREATE TABLE` — so a fresh build from
`01_schema.sql` alone lacked a column the app writes. A sweep found two more in
the same state: `AppUser.webauthn_required_after` and `AppUser.recovery_code_hash`.
The supported build (`00_load_all` + migrations) was always complete, but the
canonical schema file read on its own was not, and a cold reader would miss them.

Fix: all three columns (and their CHECK constraints) are now declared in
`01_schema.sql`, and the three migrations that add them are idempotent
(`ADD COLUMN IF NOT EXISTS`, guarded `ADD CONSTRAINT`), so on a fresh load the
column already exists and the migration is a no-op, while on an older deployed
database the migration still adds it. `check_no_migration_column_drift` cross-checks
every migration `ADD COLUMN` against `01_schema.sql`, so this drift cannot recur
(the check layer is now 23).

This also closes the review's note that `requesting_purpose_text` and
`requestor_location` are identifying-disclosure: both are documented as such in the
schema, and v9.77 already redacts `requestor_location` for ZERO_KNOWLEDGE rows at
every read path (`requesting_purpose_text` is an intentional anti-coercion
evidentiary field that no read path exposes).

- `polaris_sql/01_schema.sql` — the three columns + CHECKs declared.
- `polaris_sql/migrations/*.up.sql` — the three column migrations made idempotent.
- `polaris_checks/checks.py` — `check_no_migration_column_drift` + detection test.

## v9.78 — 2026-06-04 (atlas event feed: a full-precision cursor stops dropping sub-second events)

The atlas event feed (`/api/atlas/events`) paginates by the keyset cursor
`(event_timestamp, event_id)`, but built the cursor's timestamp from
`to_char(event_timestamp, 'HH24:MI:SS')` — whole seconds, floored. `atlas_recent_events`
then filters with a strict `(event_timestamp, event_id) < (cursor_ts, cursor_id)`.
So if the last row of a page had true timestamp `S.f` (f>0), the cursor became
`S.000000`, and every event in the open band `(S.000000, S.f)` was excluded from
the next page even though it was never shown on the previous one — silently
dropped from the feed. The infinite-scroll frontend re-feeds the cursor, and no
test exercised cross-page pagination.

Fix: the route now emits the cursor from a full-microsecond
`to_char(event_timestamp, 'HH24:MI:SS.US')` value (the human-readable whole-second
display column is unchanged), matching the full-precision pattern `/verifications`
already uses. The internal cursor field is kept out of the JSON body.

- `polaris_web/app.py` — `api_atlas_events` builds the cursor at microsecond
  precision.
- `polaris_web/test_app.py` — `AtlasEventCursorTests` inserts five events in one
  whole second with distinct microseconds: the full-precision cursor skips none,
  and a whole-second cursor demonstrably drops the sub-second band (proving why
  the fix is needed).

## v9.77 — 2026-06-04 (C6: a ZK verification's location is redacted at every read path, not just the warrant audit)

A third review pass (fresh dimensions: templates/XSS, C6 redaction, migrations,
atlas/C8, ZK circuit soundness, substrate SQL) returned clean on four of six —
notably the Plonky2 inclusion circuit is properly constrained — but found a
HIGH C6 disclosure escalation.

`uc7_warrant_audit` (admin/auditor only) deliberately NULLs `requestor_location`
for `ZERO_KNOWLEDGE` verifications, because a precise location is exactly the
spatial side-channel that de-anonymizes a ZK holder (co-locate it with a
SELECTIVE/FULL event). But that redaction lived in *one* place. Every other read
path — all reachable by any authenticated user with no role gate — exposed the
exact ZK location:

- `/verifications` (`verifications_list`) selected `ve.*` and printed
  `requestor_location` for ZK rows.
- `/api/atlas/points` (`atlas_points_verifications`) returned ZK lat/lon +
  location; the map plotted each ZK event at its exact coordinates.
- `/api/atlas/clusters` averaged ZK coordinates into grid cells (a single-ZK cell
  leaks the exact point).
- `/api/atlas/events` (`atlas_recent_events`) returned ZK lat/lon + the location
  subtitle.
- `/atlas` ran its own globe query selecting `requestor_location` for ZK events.

Fix: ZERO_KNOWLEDGE verifications never appear on the spatial map and never carry
a location anywhere. The points and cluster layers exclude ZK; the event feed and
the globe NULL its coordinates and location text; the `/verifications` list
projects `requestor_location` through the same redaction CASE uc7 uses (it stopped
using `ve.*`). ZK activity is still counted non-spatially by `atlas_stats`.
`check_c6_atlas_redacts_zk_location` guards every path against regression.

- `polaris_sql/11_atlas.sql`, `polaris_web/app.py` — redaction at all five paths.
- `polaris_checks/checks.py` — `check_c6_atlas_redacts_zk_location` (22 checks).
- `polaris_web/test_app.py` — `ZKLocationRedactionTests` seeds a ZK event with a
  secret location and asserts it appears nowhere across the atlas + list paths.

## v9.76 — 2026-06-04 (/api/health stops leaking infrastructure detail to anonymous callers)

The last finding from the deeper review's error-disclosure pass. `/api/health`
is intentionally unauthenticated (load-balancer and uptime probes), but its
per-component checks echoed operator-only detail to anyone: `_health_check_database`
and `_health_check_redis` returned `str(exc)[:160]` on failure — and a psycopg2
connection error embeds the DB host, port, and database name — while
`_health_check_zk_binary` returned the binary's absolute path on every call and
`_health_check_disk` returned the state-dir probe path. Any anonymous client could
read internal topology, especially during an outage (CWE-209).

Fix: `_sanitize_health_checks` strips the sensitive keys (`error`, `path`,
`mount_probe`) from the response and logs them to stderr for operators instead.
The per-component `status` tokens — which is all a probe needs — are preserved, so
load balancers still see healthy/degraded/unhealthy.

- `polaris_web/app.py` — `_sanitize_health_checks`, applied in `api_health`; also
  corrected the stale "27 tables" comment to 26.
- `polaris_web/test_app.py` — `test_health_does_not_leak_paths_or_error_detail`:
  no check carries `error`/`path`/`mount_probe`, and the state-dir probe appears
  nowhere in the body.

## v9.75 — 2026-06-04 (CLI: the read-only query is actually read-only, and bad args fail cleanly)

Three CLI robustness/safety findings from the review's CLI pass.

**The "read-only" `query` command was only read-only by accident.** Its sole
enforcement was a prefix check (`first in ('SELECT','WITH')`), but PostgreSQL
allows data-modifying CTEs, so `WITH x AS (UPDATE ... RETURNING ...) SELECT * FROM
x` passed the guard and the UPDATE executed. Only the absence of a `commit()` in
`cmd_query` kept it from persisting — a future edit adding a commit would silently
turn it into an authenticated arbitrary-write hole (the CLI's `polaris_app` role
has full DML). The command now runs in a `set_session(readonly=True)` transaction,
so the engine rejects any write outright, regardless of commit behavior.

**Two uncaught-traceback paths.** `cmd_query` connected with a bare
`psycopg2.connect` outside any try block, so a connection failure dumped a full
traceback instead of the documented exit-2 error; it now mirrors the `connect()`
helper's clean message + exit 2. And `cmd_issue` parsed `--contexts` with
`[int(c) for c in ...]` before its try block, so a non-integer value raised an
uncaught `ValueError`; it now exits 1 with a usage message.

- `polaris_cli/polaris.py` — `query` runs read-only; `query`/`issue` connection
  and `--contexts` parsing fail cleanly.
- `polaris_cli/test_cli.py` — a writable CTE is rejected by the read-only
  transaction (and leaves no write); a non-integer `--contexts` exits 1 with no
  traceback.

## v9.74 — 2026-06-04 (the lockout message is no longer a username oracle)

`authenticate()` returned the generic "Invalid username or password." for an
unknown user, an inactive user, and a wrong password — but a distinct "Account is
temporarily locked. Try again later." for a known user whose `locked_until` was in
the future. Since an unknown user never enters the locked state (it returns before
any failure counter is touched), an attacker could enumerate usernames: send a few
wrong-password attempts to trip the lockout on a real account, and the distinct
"locked" string on the next attempt confirmed the account exists. `SECURITY.md`
affirmatively claims username enumeration is prevented, so this was an unmet
documented invariant.

Fix: verify the password *before* the lockout check, and reveal the lockout only
to a caller who supplied the correct password. A wrong-password attacker — whether
the account is unknown, wrong-password, or locked — now gets the identical generic
string, so the response no longer distinguishes a real account. A legitimate user
who types the right password still learns the account is temporarily locked. The
account stays locked either way (no login, no counter bump), and every known user
now runs one password hash, which also evens out the timing side channel.

- `polaris_web/security.py` — password verified before the lockout branch; locked
  response is generic unless the password is correct.
- `polaris_web/test_app.py` — `test_locked_account_is_not_an_enumeration_oracle`:
  the locked + wrong-password response equals the unknown-user response and never
  says "lock"; the correct-password caller still sees the lockout.

## v9.73 — 2026-06-04 (uc4 / uc10: validate under the lock, not before it)

Two validate-before-lock TOCTOU races from the concurrency review pass. Both
procedures took a lock for serialization but read the state they guard on
*before* the lock, so the guard ran against a stale snapshot.

**uc4_activate_reserve** validated the lost/reserve token statuses at the top,
then acquired its per-holder `Individual` lock and never re-read. Two concurrent
calls on the same tokens both passed the pre-lock check; the second then re-ran
`UPDATE ... LOST` (a no-op the state machine waves through on
`OLD.status = NEW.status`) and inserted a SECOND `RevocationList` row for the
already-revoked token (the table has no unique constraint on `token_id`). The
status reads now happen again UNDER the lock with the token rows `FOR UPDATE`, so
a stale second caller fails cleanly with "Token N is not ACTIVE" and publishes no
duplicate CRL row.

**uc10_revoke_attestation** checked "already revoked" before taking its
per-agency advisory lock — unlike `uc8_revoke_token`, which locks first. Two
concurrent revokes both passed the pre-lock guard and the second silently
overwrote the first's reason and timestamp. Reordered to lock first, then re-read
`revocation_date` under the lock (row `FOR UPDATE`) and reject the double-revoke.

- `polaris_sql/05_procedures.sql` — uc4 re-validates under the lock; uc10 is
  lock-first then guard.
- `polaris_web/test_app.py` —
  `test_uc4_concurrent_same_tokens_one_winner_no_duplicate_crl` races the actual
  procedure (the prior uc4 concurrency test raced raw UPDATEs) and asserts one
  winner, a clean loser, and exactly one CRL row.

## v9.72 — 2026-06-04 (WebAuthn second factor can actually complete)

The deeper review's WebAuthn pass found that the assertion (second-factor login)
ceremony could never complete for a real authenticator. Registration stores the
credential id as `_b64url_encode(raw)`, which keeps base64url padding, so the
stored primary key carries a trailing `=` for any credential whose byte length is
not a multiple of 3 — i.e. essentially every real authenticator (16/20/32/64/65
bytes). But at assertion the browser sends `PublicKeyCredential.id` / `rawId`
WITHOUT padding (the WebAuthn spec, and `webauthn-assert.js`, strip it), and
`fetch_credential` did an exact-equality lookup. The padded stored key never
matched the unpadded browser id, so the row was not found and the route returned
401 "invalid credential". Net effect: any admin who enrolled a credential became
permanently locked out, and a control meant to add a second factor became a hard
denial-of-service against the privileged role. No WebAuthn integration test
existed, so it shipped undetected.

Fix: a `_canonical_credential_id` helper round-trips any incoming id (padded or
unpadded) through the padding-tolerant decoder back to the stored padded form,
applied in `fetch_credential`, `update_credential_after_use`, and
`delete_credential`. No migration needed (no credential is seeded; new rows are
unchanged).

- `polaris_web/webauthn_auth.py` — `_canonical_credential_id`, applied to all
  three credential lookups.
- `polaris_web/test_app.py` — `WebAuthnCredentialLookupTests`: the helper maps
  both forms to the padded key, and a padded-store / unpadded-lookup round trip
  resolves (the exact-match path misses, proving the regression).

## v9.71 — 2026-06-04 (recovery ceremony: works for reserve-only holders, and three channels means three actors)

A deeper second review pass (procedure suite + compulsion-resistance dimensions)
found two HIGH issues in the UC-9 catastrophic-loss recovery ceremony.

**Recovery aborted for the exact holder it serves.** `uc9_complete_recovery`'s
APPROVED loop transitioned *every* non-terminal token to `LOST`, but the state
machine only permits `ACTIVE→LOST`; `RESERVE→LOST` is illegal and raised, aborting
the whole recovery. And `uc9_initiate_recovery` requires that no ACTIVE token
exist — so the realistic catastrophic-loss case is a holder whose only surviving
token is a RESERVE, which is exactly the case the blanket `→LOST` loop broke. (Same
class as the v9.64 uc4 bug: a procedure driving a transition the state machine
forbids.) The loop now transitions by source status: `ACTIVE→LOST`,
`RESERVE→REVOKED` (the only legal terminal edge from RESERVE, with the
velocity-bound opt-out uc4/uc8 use). A reserve-only holder now recovers cleanly.

**The "three independent channels" collapsed to one actor.** The ceremony's
anti-impersonation guarantee rests on three independent out-of-band channels:
biometric, sworn statement, and a witness co-signer. But nothing required
`witness_co_sign_user_id` to differ from the approver or the requester — so one
compromised admin could self-witness *and* self-approve, reducing the
"multiplicative cost" to a single actor. `uc8_revoke_token` already enforces
co-signer-must-differ on the revocation leg; recovery (the entry leg) omitted it.
Added the check in `uc9_complete_recovery` plus a `witness_differs_from_parties`
CHECK on `RecoveryRequest` (mirroring `approver_differs_from_requester`), and moved
the demo seed and test helpers to a distinct third actor (auditor) for the witness.

- `polaris_sql/05_procedures.sql` — uc9 loop transitions by status; witness
  separation-of-duties check.
- `polaris_sql/01_schema.sql` — `witness_differs_from_parties` CHECK.
- `polaris_sql/10_auth.sql` — demo recovery witness is now the auditor, distinct
  from the operator requester and the admin approver.
- `polaris_web/test_app.py` — reserve-only recovery succeeds; witness≠approver and
  witness≠requester both rejected. `CatastrophicLossRecoveryTests` is now 18 tests.

## v9.70 — 2026-06-04 (close the cross-site drive-by on the launcher control endpoints)

The last finding from the auth-security pass. `/api/quit` and `/api/heartbeat`
are unauthenticated launcher-control endpoints — no session, no CSRF token (the
launcher beacon is anonymous by design). `/api/quit` writes the file the desktop
launcher polls to tear the stack down. So any page the user merely visited could
`fetch('http://localhost:2222/api/quit', {method:'POST', mode:'no-cors'})` and
shut down their local instance (a cross-site drive-by; low impact for a
single-user dev tool, but a real gap).

Added `security.reject_cross_site`, applied to both endpoints. It rejects only
requests whose `Sec-Fetch-Site` header is `cross-site` (a header browsers set on
every request). Same-origin browser calls (`same-origin` — the heartbeat beacon
sends this) and header-less callers (the native launcher, curl, an operator) are
unaffected, so nothing breaks. `CrossSiteGuardTests` covers all four cases.

- `polaris_web/security.py` — `reject_cross_site` decorator.
- `polaris_web/app.py` — applied to `/api/quit` and `/api/heartbeat`.
- `polaris_web/test_app.py` — `CrossSiteGuardTests` (cross-site rejected;
  same-origin and header-absent allowed).

## v9.69 — 2026-06-04 (ZK verify route: local-clock epoch boundary, honest replay scope)

Completing the review by re-running the two dimensions that had hit a session
limit (crypto-soundness, app-disclosure). Both surfaced a real issue in the ZK
verify route.

**Epoch boundary used the wrong clock (R4).** `/api/zk/verify` rejected proofs
against expired epochs with `epoch['valid_until'] < datetime.utcnow()`, but
`TokenStateEpoch.valid_until` is a `TIMESTAMP`-without-zone stored as local wall
clock (app and DB are co-located), and every other Python boundary in `app.py`
compares against `datetime.now()` — the atlas code even carries a comment that
`utcnow()` is the wrong reference here. On any server not in UTC the epoch
boundary shifted by the server's offset: valid proofs rejected early, or expired
epochs accepted late. Fixed to `datetime.now()`, and added
`check_local_clock_convention` (app.py must not reference `utcnow`) so the
convention can't drift back. The check layer is now 21.

**The "replay resistance" claim was an overclaim.** `zk-snark.md` R2 was titled
"Replay resistance via nonce binding" and said "each verification request includes
a fresh nonce," and `lib.rs` claimed the binding "defeats within-epoch replay." But
the verifier reads the nonce from the same request that carries the proof and never
issues or consumes nonces, so the identical bundle resubmitted verifies again. The
binding prevents proof *substitution* (re-labelling a proof under a different
`(epoch, context, nonce)`), not bundle replay — which the project's own
`threat-model.md` T-T2 already lists as deferred. Corrected R2, the `lib.rs`
header, and `zk-soundness.md` to state exactly what the binding does, and added the
single-use nonce store to `ROADMAP.md` as the concrete hardening that would make
the claim hold in code.

- `polaris_web/app.py` — epoch-boundary check uses `datetime.now()`.
- `polaris_checks/checks.py` — `check_local_clock_convention` + detection test.
- `DEVNOTES/ships/zk-snark.md`, `polaris_zk/src/lib.rs`, `DEVNOTES/zk-soundness.md`
  — replay claim scoped to proof substitution; bundle replay noted as deferred.
- `ROADMAP.md` — ZK verify single-use nonce store added under Next ships.

## v9.68 — 2026-06-04 (consistency: a true table count, a version module that points only at live things)

The review's recent-regressions pass found two honesty gaps the earlier cleanups
left, both the kind a cold reader trips on.

- **`docs/ARCHITECTURE-OVERVIEW.md` said "27 tables"; the schema defines 26.**
  Every other doc that states a count says 26, and the SQL self-tests are built
  around 26. Fixed the doc, and added `check_table_count_matches_doc`: it counts
  `CREATE TABLE` in the schema and fails if the architecture doc states a
  different number, so this exact drift cannot recur. The check layer is now 20.
- **`polaris_web/__version__.py` still cited deleted things.** Its docstring named
  the deleted `meta/polaris-self-roadmap-2026-05-14.md` as a provenance pointer,
  the deleted `ai-status.sh`, a deleted `test_polaris_version_is_canonical`, and a
  bump procedure with steps (journal entry, meta + coherence run) for tooling that
  no longer exists. Rewrote the docstring to reference only what is live: the
  `polaris_checks` version/changelog checks and the `ai-done.sh` gate. The v9.63
  ship claimed "no source comment points at a deleted file"; this makes that true.
- Reworded two historical mentions (`scripts/ai-done.sh`,
  `polaris_web/test_check_constraints.py`) so they describe the removed checks
  without naming deleted scripts.

## v9.67 — 2026-06-04 (test rigor: fail-loud PQC and an externally-anchored second witness)

Two test-coverage gaps the review's test-rigor pass found, where a test could
pass while the thing it implies was broken.

**PQC fail-loud was untested.** `pqc_signing`'s load-bearing safety property —
with `POLARIS_USE_REAL_PQC=1` but liboqs missing, raise rather than silently
downgrade to the deterministic placeholder — had no direct test. Only the
flag-unset DB path was exercised (via `test_app`) and the static wiring grep
(`check_pqc_signing_wired`). A regression that let the flag-set-but-unavailable
branch fall through to the placeholder digest — a silent downgrade of an operator
who asked for real PQC — would have passed the whole suite. New
`polaris_web/test_pqc_signing.py` (9 cases, no DB, no liboqs needed): the
placeholder is exactly `sha3_256(token_value)` with the non-signature label, and
every entry point (`signature_bytes_for_token`, `sign`, `verify`) raises
`PQCUnavailableError` when the flag is set but liboqs is forced unavailable. Wired
into CI alongside `test_app`.

**The second witness's positive Merkle tests were self-referential.**
`test_witness2.py`'s membership/ACCEPT cases computed the committed root with the
same `root_from_path` they then checked against — `f(x) == f(x)`, true for any
deterministic implementation including a wrong one (wrong MDS, flipped index bits,
wrong padding). The only value anchor (`test_root_agreement_bit_identical`) is
gated behind the Rust binary, so when the differential is skipped the standalone
suite could not catch a wrong-but-deterministic Python witness. Added value-pinned
tests against roots produced by the **independent Rust witness** (captured
constants): `build_root` for a fixed multi-leaf and single-leaf set, and a
membership check whose committed root is the external anchor constant, not a
self-recompute. The Python witness's Merkle math is now anchored to external
ground truth even with no binary present.

- `polaris_web/test_pqc_signing.py` — new (9 tests).
- `polaris_zk/witness2/test_witness2.py` — 4 externally-anchored Merkle tests
  (13 total); the weak length-only single-leaf assertion now pins the value.
- `.github/workflows/ci.yml` — runs `test_pqc_signing` in the app-suite step.

## v9.66 — 2026-06-04 (harden the login redirect and the session cookie)

Two security findings from the review's auth-security pass.

**Open redirect (CWE-601).** All three post-login redirect sites (password
login, the WebAuthn partial-auth redirect, and the assertion completion)
validated the attacker-controlled `?next=` with `startswith('/') and not
startswith('//')`. That misses backslash variants like `/\evil.com`: browsers
normalize a backslash to a forward slash when parsing a URL or `Location`
header, so it becomes the protocol-relative `//evil.com`, but werkzeug emits the
backslash verbatim, so the guard passed it and the browser navigated off-site. A
victim who clicked `…/login?next=/\evil.com` and authenticated was redirected to
the attacker's domain.

The three sites now route `?next=` through one helper,
`security.is_safe_next_url`, which rejects backslashes, protocol-relative URLs,
anything `urlsplit()` reads as carrying a scheme or netloc, and embedded control
characters (CR/LF header-splitting). `NextUrlSafetyTests` (6 cases) pins the
attacks the old guard let through.

**Session cookie Secure flag (CWE-614).** `SESSION_COOKIE_SECURE` was set only
from `POLARIS_COOKIE_SECURE`, independent of `POLARIS_ENV=production`. An operator
who set production but forgot the cookie flag shipped `polaris_session` without
`Secure`, so a single downgraded request could leak the session over plaintext.
It is now forced on in production (`_PRODUCTION or …`), mirroring the secret-key
guard — production removes the foot-gun rather than trusting the operator.

- `polaris_web/security.py` — new `is_safe_next_url` helper.
- `polaris_web/app.py` — three redirect sites use it; `SESSION_COOKIE_SECURE`
  forced on under `_PRODUCTION`.
- `polaris_checks/checks.py` — `check_open_redirect_guard` (the naive `//`-only
  guard must not survive) and `check_cookie_secure_in_production`, with detection
  tests. The check layer is now 19 checks.

## v9.65 — 2026-06-04 (the demo ZK epoch verifies, and CI proves it)

The same review surfaced a second regression, this one hidden from CI. When the
ZK anonymity set grew from a 16-leaf demo to a full epoch (v9.60, `TREE_DEPTH`
4 to 14), `zk.py`, `merkle.py`, and `lib.rs` all moved to depth 14, but the
hardcoded demo epoch in `polaris_sql/10_auth.sql` was left at depth 4: a stale
Merkle root and three 4-sibling inclusion paths where depth 14 needs 14 siblings.
The demo ZK verification (`test_demo_epoch_root_verifies_via_python`) actually
failed at depth 14.

It stayed invisible because CI ran `test_app` *before* building the Rust ZK
binary, and the whole `ZKSnarkTests` class skips when the binary is absent. So the
masking hid not just this stale-data bug but every ZK proof round-trip test:
honest-prover acceptance, cross-epoch / cross-context / wrong-nonce rejection, and
the demo-epoch verification, 20 tests, none of them running in CI.

- `polaris_sql/10_auth.sql` — regenerated the demo epoch's root and the three
  per-leaf proof paths at depth 14 via the Rust witness (`zk.compute_epoch_leaves`).
  The leaf hashes are `derive_leaf_seed` (plain SHA3-256, depth-independent) and
  were already correct; only the root and the path lengths were stale.
- `.github/workflows/ci.yml` — set up Rust and build the ZK binary *before* the
  app suite, with `POLARIS_ZK_BINARY` in the job env so `zk._binary_path()` finds
  it. `ZKSnarkTests` now runs in CI instead of skipping. The reorder un-masks 20
  ZK tests; the demo-epoch verification is the standing guard against future depth
  or seed drift.

Verified: the full `test_app` suite is green with the binary present (all 20
`ZKSnarkTests` pass, demo epoch verifies), and the two-witness differential still
agrees at depth 14.

## v9.64 — 2026-06-04 (uc4 reserve activation works for every reason code)

A multi-agent review of the schema boundary found a HIGH-severity functional
regression in `uc4_activate_reserve`. The v8.15 belt-and-suspenders trigger
`enforce_revocation_velocity_bound` refuses any `UPDATE` that transitions an
`IdentityToken` into `REVOKED` unless the session GUC `polaris.revoke_check_done`
is set, so that the rate-limited `uc8_revoke_token` is the only entry point. But
`uc4_activate_reserve` also transitions the lost token to `REVOKED` whenever the
reason code is `COMPROMISED`, `SUPERSEDED`, or `ADMINISTRATIVE` (the terminal-status
`CASE` maps all three to `REVOKED`), and it never set the GUC. The trigger therefore
aborted the whole procedure with `Direct UPDATE to status=REVOKED is not allowed`,
so three of the five reason codes the UC-4 page offers were unusable. `LOST` and
`STOLEN` map to terminal status `LOST` and dodge the trigger, which is why nothing
caught it.

The fix: `uc4_activate_reserve` now sets `polaris.revoke_check_done` on its REVOKED
branch, opting the sanctioned 1-for-1 reserve swap out of the velocity bound exactly
the way `uc8_revoke_token` does. uc4 is inherently bounded (it consumes one
pre-provisioned reserve and produces one active token per call), so it is not a
mass-revocation vector and the anti-coercion property the bound protects is intact.

- `polaris_sql/05_procedures.sql` — guarded `set_config('polaris.revoke_check_done',
  '1', true)` on the REVOKED branch, before the lost-token `UPDATE`.
- `polaris_web/test_check_constraints.py` — new `TestUC4ReserveActivation` runs uc4
  end to end for all four reason codes and asserts the lost token reaches its correct
  terminal status. The three REVOKED-mapping cases fail against the unfixed schema
  (detection proven) and pass against the fix. Suite is 66 tests, all green.

## v9.63 — 2026-06-04 (reference-clean: no source comment points at a deleted file)

The de-larp and the cleanups deleted a lot, but ~30 source-code comments still cited
the deleted record by path: `sanctum/<date>.md` decision files, the `patterns/`
how-to playbook, `ai-where.sh`, and `test_structural_invariants.py`. Those are dead
references that a reviewer cloning the repo would find pointing at nothing.

Scrubbed them across 27 source files (Python, SQL, JS, HTML, shell):

- `sanctum/<date>-<name>.md` path citations in comments, docstrings, and the
  backup-manifest field became "a recorded decision" (the substance stays; the dead
  path is gone). These only ever appeared in comments and string literals, never in
  executable logic.
- The "Read before editing" / "canonical recipe" header blocks dropped their dead
  `patterns/*.md` and `ai-where.sh` lines, keeping the surviving doc pointers
  (`DEVNOTES/concurrency.md`, `docs/reference/SCALING.md`, `DEVNOTES/atlas-scaling.md`).
- The one `test_structural_invariants.py` reference (in a `test_check_constraints`
  docstring) was reworded to the surviving `pg_constraint` catalog check.

Verified after the scrub: the schema loads (78/78 SQL self-tests), the app imports
and `/dashboard` `/atlas` `/demo` render, `test_check_constraints` 62 OK,
`polaris_checks` 17 ok READY, `ai-link-check` resolves all 222 references. No logic
changed. The tree now references no deleted file anywhere, in docs or in source.

---

## v9.62 — 2026-06-04 (ROADMAP: a forward roadmap, not a ship archive)

`ROADMAP.md` had grown to 862 lines, but only the OPEN-NOW backlog and three gated
deferred items were forward-looking. The other ~770 lines were a shipped-items
archive (R7-* through R16-*, all ✅) that duplicates the CHANGELOG. A roadmap is
where the project is going, not a log of what shipped.

Cut it to ~75 lines: the flagged decision item, the next ships (PQC second witness,
the PQC-posture audit, the GitHub Actions deprecation), the production-scale deferred
items (multi-instance scaling, multi-region, distributed tracing, each gated), and
the explicitly out-of-scope items (OIDC, banking-on-Polaris, cross-platform
launchers). Shipped history stays in the CHANGELOG and the git log.

`ai-link-check` resolves all 222 references; `polaris_checks` 17 ok READY.

---

## v9.61 — 2026-06-04 (polaris_checks: complete the C1-C10 coverage)

The flat invariant layer directly checked C1, C3, C5, and C7; the other
constitutional constraints were enforced in the schema and app but not asserted by
the check layer. Added five checks, so 9 of the 10 constraints are now directly
machine-checked, each with tested detection correctness:

- **C2** — a CHECK constraint forbids `ZERO_KNOWLEDGE` verifications from carrying a
  `token_id`.
- **C4** — the failed-login counter increments atomically in a single UPDATE (no
  TOCTOU read-then-write).
- **C8** — the `/api/atlas/*` endpoints carry hard result-set caps.
- **C9** — concurrency hazards are tested with real threading (`ConcurrencyTests`).
- **C10** — the schema carries no monetary primitives (identity is not money).

C6 (server-side disclosure enforcement) stays covered behaviorally by the
redaction-property test, where it is meaningfully exercised rather than
string-matched.

`polaris_checks` is now 17 checks; each new check provably FAILs on a broken fixture
(`polaris_checks/test_checks.py`, now 13 detection tests). Verified: 17 ok / READY,
all detection tests pass.

---

## v9.60 — 2026-06-04 (ZK anonymity set: from a 16-leaf demo to a full epoch)

The zero-knowledge Merkle-inclusion circuit shipped at `TREE_DEPTH=4` (a 16-leaf
tree) while the schema caps an epoch at 10,000 leaves, so the proof's anonymity set
was at most 16 — far smaller than a real epoch. This raises the circuit to
`TREE_DEPTH=14` (16,384 leaves), which covers the 10,000-leaf cap, so the anonymity
set is now a full epoch.

Plonky2 is a transparent SNARK (FRI-based, no trusted setup), so the change is a
single constant in two files (`polaris_zk/src/lib.rs` and the Python second witness
`polaris_zk/witness2/merkle.py`) plus a recompile — no ceremony, no key
regeneration.

Verified at depth 14: the 7 Rust circuit tests pass, and the independent two-witness
differential (the Python re-checker vs the Rust prover) passes all 27 of its cases
bit-for-bit, including prove-verify roundtrips and tampered-root rejection. That
differential is exactly what would fail if the two implementations disagreed on the
new depth.

Docs updated: the ZK soundness ledger (`DEVNOTES/zk-soundness.md`) no longer lists
tree size as a demo-scale limitation (the not-audited and placeholder-PQC caveats
stand), the ship note, and the ROADMAP backlog item is closed.

---

## v9.59 — 2026-06-04 (professional cleanup: cut the agent-governance scaffolding)

Made the repository a clean, normal software project: removed the apparatus cruft,
fixed the broken tooling, pruned the dev-script sprawl, and cut the remaining
"how-an-AI-built-this" governance scaffolding that made it read as unusual rather
than professional. The thesis is untouched: C1-C10 and the anti-coercion Vocation,
the product, and the `polaris_checks` invariant layer.

**Removed:**

- Apparatus cruft left on disk: `polaris_swarm/` (the orphaned civitas JSON), plus
  `.DS_Store` and `.pytest_cache` (gitignored; were never tracked).
- 15 vestigial / methodology scripts (`scripts/` went 43 to 29): the session
  helpers (`ai-prime`, `ai-help`, `ai-recall`, `ai-snapshot`, `ai-cache-bust`,
  `ai-coverage`, `ai-where`, `ai-journal`), the agent-governance scripts
  (`ai-sanctum`, `ai-propose`, `ai-mission`, `ai-status`, `ai-test-counts`), and
  the `polaris-ai-done-hook` wrapper.
- The agent-governance meta docs: `meta/sanctum-protocol.md`,
  `meta/autonomy-architecture.md`, `meta/freeze-amendment-protocol.md`.

**Fixed:**

- `.pre-commit-config.yaml` was broken: it invoked three deleted scripts (`ai-meta`,
  `ai-coherence`, the structural-invariants suite) and a deleted doc. Rewritten to
  run `polaris_checks` + `ai-link-check` + the real hooks.
- `MISSION.md` (793 to 589 lines): cut the "agent contract" and "agent's
  relationship to this mission" methodology sections and the strategic-posture
  subsection. The constitution (C1-C10, the Vocation, the freeze line, the
  architectural soul, the done-lists) is unchanged.
- `CONTRIBUTING.md`: replaced the Sanctum / risk-class governance with a normal
  change-review process.
- De-methodologized the rest of the doc tree (`CLAUDE`, `SECURITY`, `README`,
  `ROADMAP`, and ~32 docs via two parallel cleanup passes): removed the dead
  Sanctum / risk-class references and the provenance citations to the deleted
  record.
- Corrected two now-false items in the live backlog (the full product suite is in
  CI as of v9.56; PQC issuance is wired as of v9.58).

Verified: `polaris_checks` 12 ok READY, `ai-link-check` resolves all 225
references, every script parses, the pre-commit config is valid YAML.

---

## v9.58 — 2026-06-04 (post-quantum signing wired into issuance)

Closes the one honesty gap the codebase itself flagged as "the most damning
critique" (`pqc_signing.py`'s own docstring): the headline post-quantum claim was,
at the data level, a hardcoded SQL string. The `uc1_issue_and_activate` procedure
wrote `TokenSignature.signature_bytes = 'UC1_ISSUE_PLACEHOLDER_<id>'`, and the
real-signing module was an unused island.

**The wiring.** The `uc1_issue` route now calls the new
`pqc_signing.signature_bytes_for_token(token_value)` and passes the result to the
procedure via a new trailing `p_signature_bytes BYTEA DEFAULT NULL` parameter. So
every token issued through the app gets its signature from the signing module:

- **Default (flag unset, including CI):** a deterministic SHA3-256 binding of the
  token value. Not a cryptographic signature (no private key), but a real binding
  produced by the signing module, single-sourced and reproducible, not a magic
  string.
- **`POLARIS_USE_REAL_PQC=1` + liboqs:** a real ML-DSA-65 (FIPS 204) signature.
- **Flag set but liboqs missing:** the route fails loud (`PQCUnavailableError`),
  never silently downgrading an operator who asked for real PQC.

**Backward-compatible.** The new parameter defaults to NULL, and the procedure
`COALESCE`s to the legacy placeholder string when no signature is supplied, so
every existing SQL caller and test is unchanged (the 12-argument call still works;
the function is dropped and recreated because adding a parameter changes its
signature).

**Guarded.** A new flat check, `polaris_checks.check_pqc_signing_wired`, asserts the
procedure accepts `p_signature_bytes` and the app routes issuance through
`signature_bytes_for_token`, with a detection test that FAILs if either regresses.
A DB-backed `test_app` test issues a token through the route and asserts the stored
`signature_bytes` equals `sha3_256(token_value)`, proving the path end to end.

Verified: schema loads (78/78 SQL self-tests), `test_check_constraints` 62 OK, the
issuance/signature suites green, `polaris_checks` 12 ok READY.

---

## v9.57 — 2026-06-04 (documentation prune: less is more)

The de-larp removed the apparatus *code*; this removes the documentation bloat it
left behind. The repository went from 216 markdown files (~66.7k lines) to 72
(~26k lines) by deleting what is no longer needed to understand, run, or extend
Polaris.

**Deleted (143 files):**

- The build-history audit-of-record: `sanctum/` (68 decision records), `journal/`
  (30 daily logs), and `archive/CHANGELOG-FULL.md` (the 18.8k-line full changelog).
  The complete history remains in the git log.
- The design-and-methodology record: `proposals/` (14 shipped-feature design docs)
  and `patterns/` (the 11-file how-to playbook).
- The apparatus-era meta snapshots: the three `polaris-self-roadmap-*` files,
  `cognitive-architecture-v2`/`v3`, `cold-read-walkthrough-v9.27`,
  `missions-considered`, `lineage`, `sanctum-index`, `arc-b-production`, the
  leftover `brain-map/`, and `cognitive-threat-review-due.txt`.
- `DEVNOTES/prior-art-analysis.md` + `DEVNOTES/plugin-policy.md`, `docs/BACKLOG.md`
  (ROADMAP covers it), `docs/story/STORY.md`, and the over-elaborate compliance/ops
  docs `docs/operator/{SOC2,PENTEST,DR-SINGLE-REGION}.md`.

**Kept:** the constitution (`MISSION.md`), `ROADMAP.md`, `CHANGELOG.md`, `CLAUDE.md`,
`CONTRIBUTING.md`, `SECURITY.md`; the `docs/reference` set, the operator runbooks,
the `DEVNOTES` engineering notes and ship records, the `meta/` constitution-support
docs (constraint-lattice, sanctum-protocol, autonomy-architecture, redaction-proof,
the TLA+ spec), `docs/story/PRINCIPLES.md`, and `docs/THESIS.md`.

**Re-linked:** every broken reference left by the prune was fixed across README,
MISSION, CLAUDE, ROADMAP, the CHANGELOG header, the landing page, and the surviving
`docs/`/`meta/`/`DEVNOTES` index and map files. The landing footer was repointed off
the deleted story doc and onto the real GitHub repo. `ai-link-check --ci` resolves
all 225 remaining references.

---

## v9.56 — 2026-06-03 (residual de-larp sweep + the full product suite goes green in CI)

Two things close here: the residual apparatus references left in the documentation
and dev scripts, and the CI regression that v9.55 introduced.

**Residual de-larp sweep.** v9.55 cut the apparatus code; this sweep cuts its
shadow in the docs and scripts. Deleted 15 more pure-apparatus files with no
surviving purpose: `meta/architect.md`, `meta/anti-architect.md`,
`meta/cognitive-loop.md`, `meta/watcher-predicates.md`,
`meta/foresight-predicate-audit.md`, `meta/swarm-mttr.json`,
`meta/swarm-scorecard.json`, `meta/sanctum-scorecard.json`,
`meta/structural-constants.json`, `meta/claude-90s.md`, `meta/swarm-map/`,
`meta/brain-map/`, plus `scripts/pre-commit-scope-check.sh` +
`meta/scope-rule-baseline.json` (rule-b referenced the deleted `polaris_swarm/`)
and `scripts/test_implants.sh` (smoke-tested the deleted scripts). De-larped the
surviving active-reference surface in place: the active `meta/` docs, the `ai-*`
and `polaris-*` dev/ops scripts, `ROADMAP.md`, and the `docs/` tree (the glossary,
operations runbook, architecture overview, system map, the story, the data model,
and the rest). The dated historical snapshots (the self-roadmaps,
`cognitive-architecture-v2/v3`, the cold-read walkthrough) and the development
record (`journal/`, `sanctum/`, `archive/`, prior `CHANGELOG` entries) are kept
as history.

**CI: the full product suite now runs green.** v9.55's rewritten `ci.yml` added an
"Application + CLI suites" step that ran `test_app` + `test_cli` for the first time
(v9.54's workflow never ran them), and they failed: `reload_sample_data()` shelled
out via `su - postgres -c`, which cannot authenticate against a service-container
Postgres. Fixed by reloading through the `POLARIS_DB_*` connection settings with
`psql` directly (works in CI, on macOS, and on Linux; `POLARIS_TEST_RELOAD_VIA=su`
still forces the legacy path). Added the missing "Apply migrations" CI step so
`webauthn_required_after` exists at test time. Then fixed the long-standing stale
tests the step surfaced: the dashboard / RBAC / substrate-UI tests that GET `/`
while logged in (where `home()` correctly 302-redirects authenticated users to
`/dashboard`), the health-check assertions that expected the old `db` /
`rate_limiter` keys instead of `database` / `redis`, the logout test that pulled
its CSRF token from a redirecting `/`, and the anchor-batch tests whose
`commitment_hash` test data did not satisfy the hex CHECK constraint. `test_app`
(329 tests) and `test_cli` (62 tests) now pass end to end.

---

## v9.55 — 2026-06-03 (the swap · sever the whole apparatus web at once)

scope: cognitive-rebuild · ship_marker: apparatus-swap · vocation: trustworthiness — the product is the thesis; the theater was never load-bearing · pattern20_instance: build-the-replacement-then-swap (v9.54 built the replacement; v9.55 severs the web)

v9.54 built the clean replacement (`polaris_checks/`). v9.55 is the Alexander cut:
with the replacement standing and CI wired onto it, the entire legacy apparatus is
**deleted wholesale in one stroke** — no surgical extraction, no cascade, because
nothing in the product imports it and it all leaves together.

**Deleted (~18,150 LOC + the mythology):**

- `polaris_swarm/`, `polaris_hydra/`, `polaris_foresight/` — the ant swarm, the nine
  HYDRA watchers + CM, the foresight engine.
- `polaris_web/test_structural_invariants.py`, `test_hydra_property.py`,
  `test_hydra_revamp.py` — the ~900 self-referential invariants that asserted the
  apparatus's claims about itself (Sanctum integrity, HYDRA shape, freeze line).
- 36 `ai-swarm-*` / `ai-hydra` / `ai-meta` / `ai-coherence` / `polaris-swarm-*`
  scripts.
- The mythology docs: `meta/civitas.md`, `meta/denarius.md`, `meta/twelfth-legion.md`,
  `meta/ant-predicates.md`, the arc-D/E/F/G files, `DEVNOTES/threat-model-cognitive.md`,
  `DEVNOTES/swarm-tier-vocabulary.md`, and the pheromone/observer/cadence notes.

**Rewired onto the product + the flat layer:**

- `.github/workflows/ci.yml` — product-only: schema load, `polaris_checks` + its
  detection-correctness tests, the CHECK-constraint regression suite, the Hypothesis
  property tests, `test_app` + `test_cli`, link-check, the ZK crate + the independent
  second-witness differential. Every apparatus step removed.
- `scripts/ai-done.sh` — a thin, honest gate: `polaris_checks.run` + link-check, with
  a reminder to run the DB-backed product suites. The HYDRA findings-gate, the swarm
  scorecard, and the `ai-meta`/`ai-coherence`/CM steps are gone.
- `CLAUDE.md`, `README.md`, `MISSION.md` — de-larped to the real product: identity
  tokens, zero-knowledge verification, post-quantum signing, the schema-level
  constraint lattice, and `polaris_checks` as the one invariant layer.

**What stood unchanged through the cut:** the product — `polaris_web/` (Flask app, the
use cases, the atlas API), `polaris_cli/`, `polaris_sql/` (the C1-C10 constraints,
triggers, partial unique indexes), `polaris_zk/` (the Plonky2 SNARK + the Python
second witness). All product test suites stayed green across the swap. The thesis was
always the product; the apparatus was scaffolding, and the scaffolding is down.

---

## v9.54 — 2026-06-03 (polaris_checks · the flat, themeless check layer — the apparatus-rebuild anchor)

scope: cognitive-rebuild · ship_marker: polaris-checks-anchor · vocation: trustworthiness — a check is a check; legibility is honesty · pattern20_instance: build-the-replacement-then-swap (cut the whole knot, do not untie it strand by strand)

VANTA authorized breaking the audit-of-record discipline and redoing the cognitive
layer ("take any radical approach ... like Alexander cutting the knot"). Two surgical
attempts (the de-theme rename and the civitas deletion) were executed and **reverted**:
they proved the apparatus is one self-referential web (code ↔ tests ↔ docs ↔ frozen-AoR
↔ pinned counts) where any single cut cascades endlessly. That entanglement IS the larp.

The Alexander move is not to untie the knot strand by strand — it is to build the clean
replacement and sever the whole web at once. **v9.54 builds the replacement:**

`polaris_checks/` — a flat, themeless module. Each check is a plain `check_*(repo_root)
-> list[Finding]` function mapping to the C1-C10 constitution (CSP/C5, one-active-token/
C3, append-only-AoR/C1, crypto-as-data/C7, FK-discipline, version-canonical, secrets
hygiene, the ZK two-witness, debug-artifact hygiene). No legions, no pheromones, no
treasury, no mythology. ~350 legible LOC doing the conceptual job of ~18k LOC of
apparatus. `python3 -m polaris_checks.run` gates CI directly (exit non-zero on FAIL).

**Detection correctness is TESTED** — each check provably FAILs on a broken fixture
(`polaris_checks/test_checks.py`), the gap the old apparatus never closed. The build
loop itself caught two real bugs in the checks (a version-regex and a CSP false-positive
that would have flagged the acceptable `style-src 'unsafe-inline'`), which the fixtures
now pin.

**Next (the swap):** wire callers onto polaris_checks, then delete the entire old
apparatus (swarm/HYDRA/civitas/legions/soldiers/foresight + their ~400 tests + the
mythology docs) wholesale — the cut with no cascade because it all goes together.

**Tests** (TestWave54V954, 3 cases): polaris_checks present + clean on the repo; the
layer is themeless (no mythology vocabulary); detection tests + CI wiring present.

**Personas.** Architect: build-replacement-then-swap is the correct refactor for a
self-referential web. Anti-Architect: ~350 LOC that a second engineer reads in minutes
vs 18k LOC of in-joke — this is the de-larp. Risk LOW (new module + CI step; nothing
deleted yet). Authorized under the 2026-06-03 heavy-production + take-over directive.

## v9.53 — 2026-06-03 (Apparatus-reduction · remove the orphaned economy tier-counting from HYDRA)

scope: apparatus-reduction · ship_marker: hydra-tier-counting-removed · vocation: trustworthiness — finish the cut; orphaned theater left behind is still theater · pattern20_instance: complete-the-removal (the economy cut in v9.50, finished in its HYDRA consumer)

Completes v9.50's economy removal. HYDRA's `ant_colony_watcher` kept its OWN copy of
the tier thresholds (DENARII_PLEB_MAX/EQUES_MAX), counted ants into
pleb/eques/patrician, and emitted a dead "patrician-class ant(s)" finding that
referenced the F4 Cursus Honorum multiplier retired in v9.50 and never fired (no ant
ever approached the threshold — max balance 50 vs 10,001). v9.53 removes that orphaned
theater.

KEPT (the load-bearing parts the audit flagged): the treasury-roll **integrity probe**
(missing/malformed -> `alert`), which is HYDRA's liveness wire into the ship gate; and
the "skewed strongly negative (post-rebalance)" drift signal, which reads balance
values (not tiers) and reflects the reward ledger v9.50 preserved. HYDRA keeps its name
per VANTA — only the dead economy references inside it are gone.

**Tests** (TestWave53V953, 2 cases): the tier thresholds + pleb/eques/patrician keys
stay removed from the watcher; the roll-integrity alert path survives.

**Personas.** Anti-Architect (reviewer of record): a partial cut that leaves orphaned
references is half-honest; finish it. Architect: complete-the-removal. Risk LOW
(removed a dead finding + orphaned constants; watcher + hydra suites + structural suite
all verified green). Heavy-production authorized.

## v9.52 — 2026-06-03 (Apparatus-reduction Phase 2 · the HYDRA findings-gate now actually gates)

scope: apparatus-reduction · ship_marker: findings-gate-freshness · vocation: trustworthiness — a gate that does not gate is worse than no gate · pattern20_instance: harden-the-real-thing (the part of the apparatus that IS load-bearing, made honest)

Phase 2 of the apparatus-reduction arc: the genuinely product-improving part. The
audit found `ai-done.sh`'s step-14 HYDRA findings-gate grepped the newest
`journal/hydra/*.md` brief by mtime with **no freshness check** — so a long-stale
brief (the audit found an 18-day-old one) reported "0 ALERT" as if it described the
current state. A gate passing vacuously off stale data.

v9.52 adds a freshness guard (portable `find -mtime`, not `stat -f/-c` per gotcha #4):
a brief older than 24h can no longer confirm a clean gate — it warns ("0 ALERT is
NOT confirmed against current state; run ai-hydra.sh --full --save") instead of
falsely passing. The positive path is preserved: a fresh brief with 0 ALERT still
reports ok.

The fix is self-demonstrating: with the genuinely-stale brief on disk, the gate now
honestly WARNS. And a fresh `ai-hydra.sh` run confirms why the honesty matters — the
current state actually carries findings the vacuous gate was hiding (incl. a
`trajectory: ship-rate burst (mission-creep signal)` — the watcher independently
corroborating the v9.51-repaired release-velocity ant).

**Tests** (TestWave52V952, 2 cases): the gate has a freshness check (find -mtime;
stale → NOT confirmed); the fresh-brief positive path still reports ok.

**Personas.** Anti-Architect (reviewer of record): harden the part of the apparatus
that earns its place rather than only cutting. Architect: a measurement that lies is
worse than none. Risk LOW (gate is honest-er; warns don't block; the ship machinery
is verified by running ai-done.sh). Heavy-production authorized.

## v9.51 — 2026-06-03 (Apparatus-reduction Phase 1b · repair the bit-rotted version regexes — repair, not delete)

scope: apparatus-reduction · ship_marker: changelog-ant-regex-repair · vocation: trustworthiness — a dead check wearing live-check costume is its own larping; make it real or remove it · pattern20_instance: verify-before-cut (the audit said delete 5; live verification found 2 functional + 3 fixable)

Phase 1b of the apparatus-reduction arc. The audit flagged "5 bit-rotted ants" for
deletion. Live verification corrected it: `ant_unbumped_version` (hunts stale v8.X
refs — its job) and `ant_sanctum_outcome` (accepts CHANGELOG/journal links) are
**correctly silent and still functional** — deleting them would have cut working
checks. The genuinely bit-rotted three hardcoded `## v8\.` to parse CHANGELOG
headers and silently matched NOTHING once CHANGELOG went all-v9.x:
`ant_changelog_gap`, `ant_release_velocity`, `ant_ship_burst`.

**Repaired, not deleted** — repointed each to a version-agnostic `## v\d+\.` pattern.
This restores real function AND avoids the load-bearing 33-ant count cascade (the
count is pinned across MISSION/ROADMAP/CHANGELOG/sanctum-index). The repair is
self-validating: on the current repo `release_velocity` and `ship_burst` immediately
and correctly fire a **mission-creep signal** — "7 ships landed on 2026-06-03
(threshold 6)" and "median inter-ship gap 0.00d; sustained mission-creep territory."
The swarm now honestly observes its own heavy-production cadence; before, it was dead.

**Tests** (TestWave51V951, 2 cases): the three ants' HEADER_RE matches the current
vMAJOR.MINOR scheme; a regression guard forbids re-anchoring a CHANGELOG-header regex
to a single major.

**Personas.** Anti-Architect (reviewer of record): "repair-not-delete" is the
loyal-opposition refinement — the audit's "delete 5" over-reached; verify each before
cutting. Architect: the bit-rot was itself a form of the larping the arc targets (the
illusion that all 33 ants are live). Risk LOW (regex repair + behavioral test; no
count change). Heavy-production authorized.

## v9.50 — 2026-06-03 (Apparatus-reduction Phase 1a · retire the inert Denarius "Cursus Honorum" economy)

scope: apparatus-reduction · ship_marker: cursus-economy-retired · vocation: trustworthiness — elaborate machinery whose load-bearing output is permanently zero is theater; name it and cut it · pattern20_instance: cut-deeper (the project's own apparatus-DOMINANT signal, acted on)

First ship of the apparatus-reduction arc (Sanctum `2026-06-03-apparatus-reduction`),
opened after VANTA questioned whether the ants/citizens/Roman-tactics layer earns its
place. A function-vs-theme audit confirmed the project's own standing "cut-deeper"
signal (`polaris-sanctum-status.sh` ratio 0.29, APPARATUS-DOMINANT). Scope chosen by
VANTA: **dead-weight + harden + de-theme the swarm layer; HYDRA keeps its name.**

**Phase 1a — the clearest larping instance, removed:** the Denarius "Cursus Honorum"
tier economy was provably inert. Across all operation the maximum ant balance ever
reached was **50 against a 1001 tier threshold**, so every intensity multiplier was
permanently 1.0x, no ant ever rose above pleb, and Sanctum-chair eligibility was never
met. The project's own journal already called it "vestigial" and "empirically broken."

Removed: `multiplier_for` / `property_class` / `is_sanctum_chair_eligible` /
`patrician_ants` / `CURSUS_MULTIPLIER` / the tier thresholds from `civitas/treasury.py`;
the cosmetic Cursus multiplier from `ai_swarm_bloom.py`; the `property_class` display
from `quaestor_treasurer.py`; and **`denarii_scheduler.py`** — the one attempt to make
the economy load-bearing, which was dead (zero non-test callers) AND broken (read JSON
keys that don't exist). Kept: the reward **ledger** (the +10/-1 drift signal + the roll)
as the swarm's activity/liveness record, which HYDRA's ant_colony_watcher reads as an
integrity probe (the load-bearing wire the audit flagged — cut the economy, keep the
liveness signal).

**Tests** (TestWave50V950, 3 cases): the inert Cursus apparatus stays removed; the dead
scheduler stays deleted; the reward ledger + roll (HYDRA's liveness input) survive.
Removed 4 now-orphaned tests (F4 G19 multipliers, F4 G20 chair-eligibility, 2 scheduler
existence tests).

**Constitutional clearance:** C1-C10 + the Vocation never move (the apparatus only
OBSERVES them; grep confirms no core code imports the swarm). Audit-of-record preserved
(forward-only deletion; the treasury-roll history stays).

**Personas.** Anti-Architect is reviewer of record — it pre-named AP8 "Larping" and AP1
"loving the cognitive layer's growth more than the product's"; this cut is the
loyal-opposition position. Architect: cut-deeper, acted on the project's own signal.
Risk MEDIUM (touches the civitas + a HYDRA-read liveness file; verified import-clean +
full structural suite green). Heavy-production authorized.

## v9.49 — 2026-06-03 (Swarm coverage · every ant's scan() contract is tested, not just the E10 cohort)

scope: test-coverage · ship_marker: all-ants-scan-contract · vocation: trustworthiness — an unobserved watcher is an untrusted watcher · pattern20_instance: close-the-coverage-gap (smoke loop over ALL_ANTS, not a subset)

The gap audit found 14 of the 33 ants had no individual behavioral coverage: the
only blanket smoke test looped over the 10-ant ACCELERATION+CONSCIOUSNESS cohort
(`ALL_E10_ANTS`), not `ALL_ANTS`. v9.49 extends the `scan()` contract to every
registered ant.

- `TestWave49V949` instantiates every ant in `ALL_ANTS` with the repo root and
  asserts `scan()` returns a `list[AntFinding]` and does not raise.
- Verified DB-free: all 33 ants' `scan()` pass with no Postgres, so the test is
  CI-safe (no new service dependency). This supersedes the E10-only smoke loop.
- Plus a registry-hygiene guard: no duplicate ant `NAME`s in `ALL_ANTS`.

**Tests** (TestWave49V949, 2 cases): all-33-ant scan() contract; unique ant names.

**Personas.** Architect: close the coverage gap with a structural invariant, not a
one-off. Anti-Architect: kept it DB-free and verified (33/33 pass locally) rather
than blind-adding a fragile suite. Risk LOW (test-only). Heavy-production authorized.

## v9.48 — 2026-06-03 (Honest-accounting · ai-swarm-validate.sh header matches its body)

scope: honest-accounting · ship_marker: swarm-validate-dangling-deadline · vocation: trustworthiness — a script must not claim a computation it does not perform · pattern20_instance: drift→test promotion (dangling-deadline overclaim becomes a standing guard)

`scripts/ai-swarm-validate.sh`'s header claimed it "reports precision + recall per
ant" and "auto-flags PREDICATE_PENDING for sub-threshold ants". The body does
neither: it emits only the EXPECTED-firing matrix and deferred the observed pass
(run_colony() + Pheromone reads -> precision/recall) to "v9.25" — a follow-through
that never landed (we are at v9.48). `observed_*` counts are 0 by construction.

v9.48 rewrites the header to the honest scope (fixture inventory + expected-firing
matrix; observed precision/recall NOT computed) and removes the dangling "v9.25"
version promise from the header, the JSON `note`, and the status print.

**Tests** (TestWave48V948, 2 cases): no dangling "v9.25" version promise survives;
the header states the honest scope. The first is a class-shaped guard against
re-introducing a deadline that has already passed.

**Personas.** Architect: drift→test promotion — same honest-accounting discipline
as v9.47 (PQC ABSTAIN), applied to a swarm script. Anti-Architect: the right fix
was (b) honest header, not (a) implement-the-deferred-feature, under the v9.31
freeze. Risk LOW (docstring + test). Heavy-production authorized.

## v9.47 — 2026-06-03 (Honest-accounting · the PQC verdict is a recorded two-witness ABSTAIN)

scope: crypto-honesty · ship_marker: pqc-lone-verifier-abstain · vocation: trustworthiness — name the gap, do not let a lone verifier ship silently · pattern20_instance: drift→test promotion (the island-claim is now a standing invariant)

The two-witness principle (v9.44) says shipping a lone cryptographic verifier is
a finding, not a feature. The ML-DSA-65 signature verdict (`pqc_signing.verify`)
has a single liboqs impl and no independent second witness. v9.47 records it as
an explicit **ABSTAIN** instance (rule 4) in `DEVNOTES/two-witness-principle.md`
rather than leaving the gap silent.

It also corrects a docstring overclaim: `pqc_signing`'s activation procedure
implied that flag-on (`POLARIS_USE_REAL_PQC=1`) makes issuance write real
signatures. In fact `app.py` never imports the module and the issuance route
(`uc1_issue`) never calls `sign()` — the module is an integration *island*, so
flag-on enables the `sign()`/`verify()` primitive but does not change issuance
behavior. The docstring now says so plainly.

**Tests** (TestWave47V947, 3 cases): PQC verdict recorded as ABSTAIN; docstring
states the wiring status; and an island-guard that FAILS ON PURPOSE if
`pqc_signing` is ever imported by `app.py` — forcing whoever wires it to update
the honesty note and promote the verdict from ABSTAIN to two-witnessed.

**Personas.** Architect: drift→test promotion — the "island" claim becomes a
standing invariant. Anti-Architect: this is exactly the AP8 (larping) discipline
the PQC module itself cites — the honest move is to name the gap, not paper over
it. Risk LOW (docs + test). Heavy-production authorized.

## v9.46 — 2026-06-03 (CI hardening · the ZK two-witness differential now gates CI)

scope: ci-hardening · ship_marker: ci-two-witness-wiring · vocation: trustworthiness — a verifier that never runs in CI is not a safety net · pattern20_instance: close-the-loop (ship a check, then make it gate)

The flagship v9.44 deliverable — `test_zk_second_witness.py`, the differential
that cross-checks the Rust ZK verdict against the independent `witness2`
implementation — never ran in CI, even though CI already builds the exact
`polaris-zk` binary it needs. v9.46 wires it in.

- **pytest** added to `requirements.txt`. The header comment already promised
  it but it was absent, so the pytest-style ZK suites (`witness2/test_witness2.py`,
  `test_zk_second_witness.py`) ImportError'd on a clean install / in CI.
- **CI steps added** (`.github/workflows/ci.yml`): the ZK two-witness
  differential (after the existing prove-verify roundtrip, reusing the built
  binary via `POLARIS_ZK_BINARY`), and the pure HYDRA watcher suites
  (`test_hydra_property`, `test_hydra_revamp`; verified locally 44 pass / 9 skip).
- Refreshed the stale CI header (claimed "273 tests / 7 ZK adversarial tests";
  now descriptive, not a drifting hardcoded count).

**Follow-up (ROADMAP §OPEN NOW):** wire `test_app.py` + `test_cli.py` into CI
once confirmed green against the CI sample DB (deferred: not verifiable from the
local env, which lacks psycopg2).

**Tests** (TestWave46V946, 3 cases): pytest is a declared dependency; CI runs the
ZK two-witness differential + witness2 self-tests; CI runs the HYDRA suites.

**Personas.** Architect: close-the-loop — a shipped check that never gates is
half a ship. Anti-Architect: held the wiring to suites verified locally (ZK +
hydra), refusing to blind-add the DB-backed suites I cannot confirm from here.
Risk LOW (CI config + test). Authorized under the 2026-06-03 heavy-production
directive.

## v9.45 — 2026-06-03 (Repo hygiene · secret-leak gitignore fix · foresight log integrity)

scope: hygiene-security · ship_marker: gitignore-secret-leak · vocation: trustworthiness — operator secrets must not be one `git add` from disclosure · pattern20_instance: drift→test promotion (security regression guard)

Heavy-production session cleanup (Sanctum `2026-06-03-heavy-production-authorization`).
A repo audit surfaced a latent **secret-leak**: `.gitignore` used trailing inline
comments on `polaris.env` (operator secrets) and `.claude/`:

    polaris.env   # v9.34: sourced by polaris-mycelium-wake.sh

git does NOT honor trailing inline comments — the `# ...` becomes part of the
pattern, so `polaris.env` matched nothing and was NOT ignored by the repo. The
file holds operator secrets; a `git add -A` with it present would have committed
them. Only the file's non-existence saved the tree. v9.45 moves the comments to
their own lines above bare patterns. Verified with `git check-ignore`.

**Other hygiene:**
- `.playwright-mcp/` (158 stale browser-console logs) gitignored + removed.
- Foresight acceptance-log path parameterized: `promote_foresight_candidates`
  now takes `acceptance_log_path`, so the idempotency test stops leaking the
  fixture `"Test idempotent candidate xyz123"` into the real empirical-graduation
  tracker (`promotion.py` previously hardcoded `_REPO_ROOT`). Scrubbed the leaked
  FS-FBAEC2B8 entry.

**Tests** (TestWave45V945, 6 cases): security regression guards (polaris.env +
.claude gitignored via `git check-ignore`; no trailing-comment patterns in
.gitignore), .playwright-mcp ignored, acceptance-log path parameterized, no
fixture in the real log.

**Personas.** Architect: drift→test promotion — the secret-leak becomes a
standing invariant, not a one-time fix. Anti-Architect: no scope dissent; pure
hygiene + integrity. Risk class LOW (hygiene + test; security-positive).
Authorized under the 2026-06-03 heavy-production directive.

## v9.44 — 2026-06-03 (Glass bounded-integration · the ZK verdict is two-witnessed · decline the complete rework)

scope: zk-substrate · ship_marker: glass-bounded-integration · vocation: trustworthiness — a cryptographic verdict only one program can produce is a promise, not a proof · pattern20_instance: import-the-method-not-the-chassis (additive cross-check beside the audited substrate)

VANTA proposed reworking Polaris with the Glass language. An adversarial
fit analysis (Sanctum `2026-06-03-glass-bounded-integration`) found the
philosophical rhyme real but the rework wrong: Glass's own ledger says
*"do not use Glass to protect real value"* and it is *"not
production-hardened"*; Polaris's security boundary is the Postgres engine
(C1-C10 as triggers / partial-unique-indexes / CHECK), which Glass's
pure-functional, compile-to-C effect surface cannot host. The
decline-and-surface posture held; VANTA authorized the bounded plan:
*"go ahead with the bounded integration plan."*

**What shipped.** The one genuinely transferable asset. Glass and
`polaris_zk` both live on the Goldilocks field (2^64) with the Poseidon
hash family, which makes a second, independent verifier known-shaped
rather than research. `polaris_zk/witness2/` is a from-scratch Python
Goldilocks + Poseidon + Merkle witness that re-derives the
Merkle-inclusion verdict and must agree with the Rust `verify()`:

- Shares no code with the Rust crate or with Glass; plain `int mod p`,
  not the crate's limbs (the Pentecost discipline, borrowed from Glass).
- Anchored independently on Plonky2's own published Poseidon test vectors
  (all-zeros, 0..11, all -1) in `poseidon_constants.py`.
- Agrees bit-for-bit with the live Rust binary on root computation across
  every cohort size 1..16, and on ACCEPT/REJECT across the honest +
  adversary corpus (nonce / epoch / context / root tamper, multi-field
  replay).
- ABSTAINS, by construction, on proof-byte integrity (that axis stays
  with the Rust decoder) and says so rather than bluffing.

**Docs.** `DEVNOTES/zk-soundness.md` is the honest ledger (demo-scale
`TREE_DEPTH = 4`, placeholder PQC by default, statement-level witness
scope), modeled on Glass's own `docs/soundness.md`.
`DEVNOTES/two-witness-principle.md` makes "every cryptographic verdict
must be two-witnessed" a standing Polaris obligation.

**Tests** (TestWave44V944, 9 cases, no Rust binary needed at CI time):
package presence; 360 Poseidon constants + MDS matrices; Plonky2 vector
self-test; golden root bit-for-bit vs Rust; verdict ACCEPT/REJECT; ledger
+ principle docs honest; Sanctum recorded + indexed; no Glass coupling.
The full Rust-vs-Python differential is
`polaris_web/test_zk_second_witness.py` (18 cases; runs when the binary is
built).

**Personas.** Architect: import the method, not the chassis — the
additive cross-check strengthens C2/C7 without touching the substrate.
Anti-Architect: held the line against chassis replacement (the v9.08
showroom precedent) and against routing identity crypto through an
educational substrate (the Vocation). Risk class: HIGH Sanctum
(adjudicated a complete-rework request); the shipped work is hardening
within the v9.31 freeze envelope. Glass folder untouched; no production
substrate changed.

