<div align="center">

<img src="assets/polaris_logo_clean.png" alt="Polaris" width="280">

# POLARIS

### A working national identity infrastructure.

_Cryptographically signed. Audit-of-record by construction. Compulsion-resistant by design._

> _Fixus inter mutabilia._ &nbsp; Fixed amid the mutable.

[![CI](https://img.shields.io/github/actions/workflow/status/EgorKhaklin/polaris-id/ci.yml?branch=main&label=CI&logo=githubactions&logoColor=white&style=flat-square)](https://github.com/EgorKhaklin/polaris-id/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/EgorKhaklin/polaris-id?label=release&color=2b5797&style=flat-square)](https://github.com/EgorKhaklin/polaris-id/releases/latest)
[![License](https://img.shields.io/github/license/EgorKhaklin/polaris-id?color=blue&style=flat-square)](LICENSE)
[![Last commit](https://img.shields.io/github/last-commit/EgorKhaklin/polaris-id?color=success&style=flat-square)](https://github.com/EgorKhaklin/polaris-id/commits/main)

[![Python 3.12](https://img.shields.io/badge/python-3.12-3776AB?logo=python&logoColor=white&style=flat-square)](polaris_web/)
[![PostgreSQL 16](https://img.shields.io/badge/postgres-16-336791?logo=postgresql&logoColor=white&style=flat-square)](polaris_sql/)
[![Rust](https://img.shields.io/badge/rust-nightly-DEA584?logo=rust&logoColor=white&style=flat-square)](polaris_zk/)
[![Plonky2](https://img.shields.io/badge/zk--snark-plonky2-8957e5?style=flat-square)](polaris_zk/src/lib.rs)
[![WebAuthn MFA](https://img.shields.io/badge/auth-WebAuthn%20MFA-1f883d?logo=webauthn&logoColor=white&style=flat-square)](polaris_web/webauthn_auth.py)
[![Apache 2.0](https://img.shields.io/badge/license-Apache%202.0-d63aff?style=flat-square)](LICENSE)

**Now shipping [v9.43](https://github.com/EgorKhaklin/polaris-id/releases/latest)** &nbsp;·&nbsp; 944 structural invariants &nbsp;·&nbsp; 633 cross-references resolved &nbsp;·&nbsp; one double-click to launch

[**System map**](docs/reference/SYSTEM-MAP.md) · [**Conventions**](docs/CONVENTIONS.md) · [**Constitution (MISSION.md)**](MISSION.md) · [**Backlog (ROADMAP.md)**](ROADMAP.md) · [**Audit-of-record (CHANGELOG.md)**](CHANGELOG.md) · [**Agent runbook (CLAUDE.md)**](CLAUDE.md)

[Quickstart](#quickstart)  ·  [The hard parts](#the-hard-parts)  ·  [What you get](#what-you-get)  ·  [The trick](#the-trick)  ·  [Tour](#tour)  ·  [Tests](#tests)  ·  [License](#license)

</div>

---

## What this is

Americans currently carry six to eight credentials that do not talk to each other: driver's license, passport, Social Security card, Real ID, voter registration, health insurance card, and a thickening pile of agency-specific identifiers. Each is a different artifact, signed by a different authority, secured to a different standard, with no shared revocation path and no shared audit trail.

Polaris consolidates them into **one physical token per person**, signed under post-quantum cryptography, with **context-scoped verification** (banking versus voting versus healthcare are different events with different disclosure rules) and **zero-knowledge defaults** (the typical verification stores no token identifier at all).

This repository is a **working reference implementation**: 27 schema tables, 14 stored procedures, a Flask web application that exercises every use case, a Plonky2 ZK-SNARK prover in Rust, WebAuthn-MFA operator authentication, an operational atlas with a live globe, and a self-healing macOS launcher that gets all of it running from a single double-click.

It is not a slide deck. It runs.

The system lives in [`polaris_sql`](polaris_sql/), [`polaris_web`](polaris_web/), [`polaris_cli`](polaris_cli/), [`polaris_zk`](polaris_zk/). The cognitive apparatus lives in [`polaris_swarm`](polaris_swarm/), [`polaris_hydra`](polaris_hydra/), [`polaris_foresight`](polaris_foresight/), [`meta`](meta/), [`sanctum`](sanctum/). Everything under [`archive`](archive/) is frozen history and is not read to understand the system.

---

## The hard parts

Consolidating the cards is the easy half. The interesting half is what happens when an adversary shows up. Polaris answers six of them by construction.

| The threat | What it looks like in practice | How Polaris answers it | Where |
|---|---|---|---|
| **Cryptographic compulsion** | "Sign this transaction or I break your fingers." The holder cannot refuse without injury. | A second secret produces an indistinguishable verification that silently records a DuressEvent. The operator's screen reveals nothing. | [duress-codes](DEVNOTES/ships/duress-codes.md)   UC-12 |
| **Catastrophic loss** | Token lost, holder unidentified, no way to prove who they are without the artifact. | Two-phase recovery ceremony (initiate then complete) gated by four CHECK constraints and an admin-only second key. | [recovery-ceremony](DEVNOTES/ships/recovery-ceremony.md)   UC-9 |
| **Quantum migration** | Today's signing algorithms become broken overnight when a quantum computer arrives. | Multi-signature transitional state: a token can be signed under classical AND post-quantum algorithms simultaneously, with a hard rule that exactly one is active. | [multi-sig-migration](DEVNOTES/ships/multi-sig-migration.md)   UC-6 |
| **Issuer concentration** | One agency can issue tokens that masquerade as any other agency's. | Explicit-only federation: no transitive trust. Every cross-agency verification gates on an active AgencyTrustAttestation row. | [federation](DEVNOTES/ships/federation.md)  UC-10 |
| **Public auditability without privacy loss** | "Prove this token was in the ledger" without revealing which one. | Plonky2 ZK-SNARK over a Merkle commitment. The proof reveals nothing about the leaf. | [zk-snark](DEVNOTES/ships/zk-snark.md)  ‎     UC-11 |
| **Issuer overreach** | An agency revokes tokens at industrial scale outside policy. | Per-agency revocation-rate ceiling enforced by trigger. Sanctioned by the IssuerDiscretionPolicy row, audited by `pg_advisory_xact_lock`. | [issuer-discretion](DEVNOTES/ships/issuer-discretion.md)   UC-8 |

Every row has a defender's claim, an attacker's optimal play, an equilibrium analysis, a documented second-best attack, and an enforcement trace. The walks are canonical (`scripts/ai-adversary.sh C1..C10`).

---

## Quickstart

You need a Mac with [Docker Desktop](https://www.docker.com/products/docker-desktop) installed. That is the only prerequisite.

```bash
git clone <this-repo> polaris
cd polaris
./Polaris.command            # or: ./polaris_mac_launch.sh up
```

The first run pulls Postgres 16, builds the Flask image, loads the schema, runs the SQL self-tests, and opens your browser at `http://localhost:2222`. Subsequent launches take roughly ten seconds.

Sign in with one of three seeded roles:

```
admin     ·  Admin@123!     full access + SQL console + Sanctum tooling
operator  ·  Operator@123!  issue / activate / bind tokens
auditor   ·  Auditor@123!   read-only + warrant audits + duress dashboard
```

Close the browser tab to stop. The launcher is watching the page; when you close it, it tears the stack down automatically.

A full subcommand reference lives in [`docs/operator/INSTALL.md`](docs/operator/INSTALL.md). If anything looks wrong, the launcher carries a read-only diagnostic:

```bash
./polaris_mac_launch.sh doctor
```

---

## What you get

```
                 ┌──────────────────────────────────────────────────┐
                 │              Polaris in numbers                  │
                 │              (current as of v9.43)               │
                 ├──────────────────────────────────────────────────┤
                 │  27 schema tables                                │
                 │  14 stored procedures (UC-1 .. UC-12 + foresight)│
                 │  67 HTTP routes (incl. /auth/webauthn/*)         │
                 │  1,077 Python tests · 909 structural invariants  │
                 │  64 Sanctum strategic-consultation records       │
                 │  9 HYDRA watchers + CM                           │
                 │  33 commander ants + 6 citiz + 9 soldier classes │
                 │  4 constitutional principles + 1 vocation        │
                 │  1 double-click to launch                        │
                 └──────────────────────────────────────────────────┘
```

After login the app lands on the **Dashboard**, which fans out into eight analytical panels covering schema statistics, token status, the authorization matrix, post-quantum migration ratio, verification activity by context, disclosure posture, succession lineage, and the audit trail.

The **Atlas** (`/atlas`) is the operational investigation surface: a live globe with reticles for every verification and lifecycle event, a four-figure HUD (Active Tokens, Anomalies, Post-Quantum percentage, Zero-Knowledge percentage), and click-through into any token's full record including its predecessor chain.

Routes for each use case: `/uc1/issue`, `/uc4/activate-reserve`, `/uc5/bind-device`, `/uc6/migrate-algorithm`, `/uc7/warrant-audit`, `/uc8/revoke-token`, `/uc9/recover-identity`, `/duress`, `/anchors`, `/epochs`, `/federation`, and `/sql` (admin / auditor only).

---

## The trick

Most reference implementations of an identity system are a database schema, an application, a test suite, and a README. Polaris is all four of those plus a **cognitive substrate**: the deliberate architecture that lets an AI agent maintain the system without drifting from its own claims.

The substrate is named in MISSION.md as four principles. The principles, not the implementation:

1. **The Sanctum protocol.** A formal record of every non-routine decision; 59 entries in `sanctum/` to date, indexed at [`meta/sanctum-index.md`](meta/sanctum-index.md).
2. **Audit-of-record.** Ten instances across schema and filesystem (9 schema + 1 filesystem); the system writes evidence at the moment of decision rather than reconstructing it later. See [`DEVNOTES/audit-of-record.md`](DEVNOTES/audit-of-record.md).
3. **Risk classes.** Three tiers (LOW / MEDIUM / HIGH) governing what an agent may do autonomously versus what requires explicit human approval. See [`meta/autonomy-architecture.md`](meta/autonomy-architecture.md).
4. **CM (the meta-constraint).** Six executable self-checks under `scripts/ai-meta.sh` that catch drift between the cognitive layer's claims and the running system.

The current implementation is named, not pinned. As of v8.43, MISSION.md says the four principles may be served by *any* synthesis pattern that preserves them. Today that pattern is **HYDRA**, a nine-watcher introspection swarm at [`polaris_hydra/`](polaris_hydra/) that scans schema, cognitive layer, security, mission state, adversary models, performance, trajectory drift, civitas state, and ant-colony health on demand. The Architect persona at [`meta/architect.md`](meta/architect.md) is the synthesis voice. The 22-pattern catalog at [`scripts/ai-pattern.sh`](scripts/ai-pattern.sh) is the procedural memory.

If a future maintainer replaces HYDRA with something better, the constitution does not need to be amended. The principles are stable; the implementations are substitutable.

The brain map renders all of this as an interactive D3 force-directed graph: ~383 nodes, ~388 edges across seven layers (schema · behavior · cognitive · decision · constitution · observation · knowledge). Run [`scripts/ai-brain-map.sh`](scripts/ai-brain-map.sh) (or [`scripts/ai_brain_map.py`](scripts/ai_brain_map.py)) to regenerate it locally at `meta/brain-map/brain-map.html` — the file is auto-gen state (gitignored per v9.41), so it's produced on demand rather than tracked. Open the result in any browser; nothing is fetched from the network.

---

## Tour

Start at the file that matches what you came here for.

|   |   |   |
|---|---|---|
| **[The story](docs/story/STORY.md)** | **[The system map](docs/reference/SYSTEM-MAP.md)** | **[The principles](docs/story/PRINCIPLES.md)** |
| How Polaris was built between April 30 and May 16, 2026. Nine major versions, 146 ships, two single-day rampages, 59 formal decisions. | A single page that names every meaningful artifact in the repository and what it is for. Use this when you do not know where to start. | The four constitutional principles distilled. Read this before you change anything load-bearing. |
| **[The schema](polaris_sql/01_schema.sql)** | **[The constitution](MISSION.md)** | **[The agent runbook](CLAUDE.md)** |
| 27 tables. Start with `IdentityToken` and follow the foreign keys. Append-only invariants enforced at trigger level on nine of them. | C1 through C10 plus CM. Ten hard constraints the system must never violate, one meta-constraint that guards the layer itself. | If you are an AI agent priming on this project, this is your entry point. |
| **[The Atlas](polaris_web/static/atlas-globe.js)** | **[The ZK prover](polaris_zk/src/lib.rs)** | **[The CHANGELOG](CHANGELOG.md)** |
| The operational globe. 1,318 lines of D3 + custom projection logic. Pan, zoom, drag, hover, click-through, viewport-aware decimation. | Plonky2-backed Merkle-inclusion circuit in Rust. Subprocess CLI consumed by `polaris_web/zk.py`. | The full audit-of-record (108K words; pre-v9.24 archive). The curated last-10-ships index lives at `CHANGELOG.md` (~3.7K words). |

For an exhaustive index of operator and architect documentation, see [`docs/README.md`](docs/README.md).

---

## Tests

Four layers of verification, all run by the launcher's `test` subcommand.

```
┌─────────────────────────────┬────────┬──────────────────────────────────────────────┐
│  Layer                      │  Count │  What it covers                              │
├─────────────────────────────┼────────┼──────────────────────────────────────────────┤
│  Python tests (total)       │ 1,077  │  Every Flask route, every form, the use      │
│                             │        │  cases, rate limiter, atlas API, R6 anti-    │
│                             │        │  revealing posture. Includes property tests  │
│                             │        │  and structural invariants below.            │
│  Hypothesis property tests  │   19   │  Adversarial inputs against C1, C2, C3 and   │
│                             │        │  the M2-12 redaction-proof. Needs hypothesis.│
│  Structural invariants      │  909   │  The cognitive layer's claims about itself:  │
│                             │        │  constraint lattice, pattern catalog, CM,    │
│                             │        │  Sanctum integrity, HYDRA shape, freeze line.│
└─────────────────────────────┴────────┴──────────────────────────────────────────────┘
```

```bash
./polaris_mac_launch.sh test          # full suite, ~60 s
./scripts/ai-test.sh quick            # skip the slow concurrency + property tests
./scripts/ai-done.sh                  # pre-ship gate (incl. CM enforcement)
```

A release is shippable when every layer passes and `ai-done` reports `READY`.

---

## Subcommand reference

```bash
./polaris_mac_launch.sh                # default; same as 'up'
./polaris_mac_launch.sh up             # bring up, watch the browser, open it
./polaris_mac_launch.sh up --detach    # bring up in background and return
./polaris_mac_launch.sh rebuild        # force clean rebuild (no cache)
./polaris_mac_launch.sh stop           # graceful shutdown
./polaris_mac_launch.sh status         # what is running, where
./polaris_mac_launch.sh doctor         # read-only diagnostic
./polaris_mac_launch.sh logs           # tail Flask log (default)
./polaris_mac_launch.sh logs db        # tail Postgres log
./polaris_mac_launch.sh test           # run the test suite
./polaris_mac_launch.sh reset          # drop pgdata, keep image
./polaris_mac_launch.sh nuke           # total wipe: containers + image + volume
./polaris_mac_launch.sh --port 5050    # alternate host port
./polaris_mac_launch.sh --native       # native path; Homebrew, no Docker
./polaris_mac_launch.sh --help         # full help
```

---

## Building the ZK prover (optional)

The Rust source for the Plonky2 prover ships in `polaris_zk/`; the compiled binary does not. The Flask app degrades gracefully without it: every page serves, every UC-1..UC-12 flow works, `/epochs` renders historical epochs from the seed. The binary is only needed to **prove or verify new epoch closures** (`/api/zk/epoch/close`, `/api/zk/verify`).

```bash
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
rustup install nightly
cd polaris_zk && cargo +nightly build --release
```

After the build, `polaris_zk/target/release/polaris-zk` exists; the Flask app finds it via the default path. Override with `POLARIS_ZK_BINARY=/your/path/polaris-zk` if you build elsewhere.

---

## License

Polaris is released under the [Apache License, Version 2.0](LICENSE).

```
Copyright 2026 Egor Khaklin
Licensed under the Apache License, Version 2.0.
```

The license includes an explicit **patent grant** (§3) and **preservation of attribution** (§4). If you build on Polaris — the code, the schema, or the architectural patterns (audit-of-record discipline, constraint lattice, cognitive substrate) — retain `LICENSE` and `NOTICE` and the author attribution per §4. Component-level attributions for Plonky2, D3, TopoJSON, and Flask live in [NOTICE](NOTICE).

The academic project report ([docs/paper/polaris_project_report.pdf](docs/paper/polaris_project_report.pdf) and its TeX source) is part of the same release under the same license.

---

## Attribution

Educational project for **Seton Hill University**, Spring 2026. Notional data only; not a real identity system. All cryptographic algorithm choices reflect current NIST PQC standardization (FIPS 204, FIPS 205) for academic accuracy.

The constitution lives in [MISSION.md](MISSION.md). The build journal lives in [`journal/`](journal/) (indexed at [`journal/INDEX.md`](journal/INDEX.md)). The decision graph lives in [`sanctum/`](sanctum/) (indexed at [`meta/sanctum-index.md`](meta/sanctum-index.md)).

If you read one document after this one, read [docs/story/STORY.md](docs/story/STORY.md).
