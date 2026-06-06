# ENCRYPTION-AT-REST.md: the at-rest data-protection posture

This document states, honestly, what Polaris protects at rest, what it does not,
and why. At rest means data sitting on disk: the live database files, the
write-ahead log (WAL), and backups, as opposed to data in transit (covered by
[`SLOS.md`](SLOS.md)'s sibling, the app<->DB TLS shipped in v9.121) or in use.

> **Honest status (v9.124).** Polaris does **not** encrypt the live database at
> the application layer. At-rest protection of the live data files and WAL is
> **host-level and operator-gated**: it depends on a full-disk / volume
> encryption layer the operator provisions (LUKS / dm-crypt / fscrypt) and a key
> custodian. Backups are already encrypted by Polaris (v9.102); in-transit is
> already encrypted (v9.121). This document is the posture and the operator path,
> not a claim that the live database is encrypted at rest by Polaris.

---

## Table of contents

1. [What is sensitive at rest](#1-what-is-sensitive-at-rest)
2. [What is deliberately NOT stored](#2-what-is-deliberately-not-stored)
3. [What is already protected](#3-what-is-already-protected)
4. [The gap: the live database](#4-the-gap-the-live-database)
5. [Why host-level encryption, not field-level](#5-why-host-level-encryption-not-field-level)
6. [The operator path](#6-the-operator-path)
7. [Cross-references](#7-cross-references)

---

## 1. What is sensitive at rest

Two surfaces in the schema hold data that an at-rest compromise (a stolen disk, a
copied data directory, a leaked volume snapshot) would expose:

| Surface | Column(s) | Why it matters |
|---|---|---|
| Personal data | `Individual.legal_name`, `Individual.date_of_birth` | The only direct PII in the system: the legal name and birth date that bind a token to a person. |
| Quasi-identifier | `Individual.jurisdiction` | An ISO 3166-2 region; low cardinality, but narrows a re-identification set. |
| ZK structural data | `TokenStateEpochLeaf.proof_path` (plaintext `JSONB`), `TokenStateEpochLeaf.leaf_hash` | The per-token Merkle inclusion path within an epoch snapshot. The schema itself flags this: `01_schema.sql` comments "v1 stores proof_path in plaintext; v2 would encrypt under holder key." In aggregate the leaf table maps which tokens were members at which epoch. |

These are the surfaces the posture is about. Everything else in the schema is
either a hash, an opaque identifier, an append-only audit event, or operational
metadata.

---

## 2. What is deliberately NOT stored

The strongest at-rest control is the data that never lands on disk. Polaris is
built on data minimization (see [`PRIVACY.md`](PRIVACY.md)):

- **Biometric and genomic plaintext never enters the database.** The schema
  stores only binding *metadata* (`biometric_binding_type`,
  `biometric_verified`), never the template or sample itself
  (`01_schema.sql`: "the biometric / genomic plaintext never enters the
  database").
- **The ZK design keeps verification zero-knowledge**: a verifier learns a
  yes/no membership answer, not the underlying attributes, so the verification
  path does not accumulate a plaintext attribute store.

A field that is never stored cannot leak from a stolen disk. This is a real part
of the posture, not a footnote.

---

## 3. What is already protected

- **Backups are encrypted at rest (v9.102).** `polaris-backup.sh` encrypts the
  dump with AES-256-CBC / PBKDF2 when `POLARIS_BACKUP_KEY_FILE` is set, and warns
  loudly when it is not; `polaris-restore.sh` fails closed without the key. A
  stolen backup tarball is ciphertext. See [`DR.md`](DR.md).
- **Data in transit is encrypted and verified (v9.121 + v9.131).** Both prod
  hops (app to pgbouncer, pgbouncer to Postgres) run TLS and verify-ca the pinned
  self-signed certs, so the data does not travel the pod network in the clear and
  a MITM presenting a different cert is rejected.
- **Secrets are file-mounted, not in the image or environment**, and disk
  encryption for the secrets mount is already documented as the operator's
  responsibility in [`SECRETS.md`](SECRETS.md).

---

## 4. The gap: the live database

The live PostgreSQL data directory and WAL are **not** encrypted by Polaris. An
attacker who reads the raw data files (a stolen disk, a snapshot of an
unencrypted volume, host-level filesystem access) can read `legal_name`,
`date_of_birth`, and the `proof_path` leaves directly. PostgreSQL has no
transparent built-in data-file encryption; at-rest protection of the live
cluster is a property of the storage layer beneath it.

This is the honest gap. Closing it is host-level work the operator owns
(section 6), not application code.

---

## 5. Why host-level encryption, not field-level

It is tempting to "just encrypt the columns." For Polaris that is the wrong
control, and not for convenience:

- **Field-encrypting `legal_name` / `date_of_birth` breaks C3.** The
  one-identity-per-person invariant is a partial unique index that must compare
  the identifying fields; encrypting them with a non-deterministic scheme defeats
  the index, and a deterministic scheme leaks equality (and reintroduces the
  exact correlation the design avoids).
- **Field-encrypting `proof_path` breaks the ZK second witness.** The Rust prover
  and the independent Python second witness both read the plaintext Merkle path
  to recompute inclusion; encrypting it under an app key would either break the
  two-witness verification or require the app to hold the decryption key beside
  the data, which is no protection against the host-level threat this is about.
- **Volume encryption protects every surface uniformly** (data files, WAL,
  temp files, indexes) against the actual at-rest threat (disk / snapshot theft)
  without distorting the query and ZK semantics the invariants depend on.

So the posture is: protect the whole volume at the host, keep the schema honest
and queryable. The schema's own "v2 would encrypt proof_path under holder key"
note remains a future direction tied to a holder-key custody model, not a v1
control.

---

## 6. The operator path

At-rest encryption of the live cluster is **operator-gated** (it needs a
provisioned host and a key custodian, which are organizational decisions, not
code):

1. **Encrypt the volume that holds the PostgreSQL data directory.** LUKS /
   dm-crypt for a block device, or fscrypt for a directory, on the host (or the
   cloud provider's encrypted-volume equivalent with a customer-managed key).
2. **Custody the volume key** in the same key-management posture as the other
   Polaris secrets (see [`SECRETS.md`](SECRETS.md) on the HSM/KMS paved path).
   The volume key must not live unencrypted on the same host it unlocks.
3. **Keep backups encrypted** (already shipped) and ensure the backup key and the
   volume key have independent custody, so one compromise is not both.
4. **Verify**: a powered-off / detached volume must be ciphertext. Confirm before
   the host handles real data.

Until the operator provisions this, the live database is protected only as well
as the host it runs on. Stating otherwise would overclaim what Polaris ships.

---

## 7. Cross-references

- [`SECRETS.md`](SECRETS.md): secret custody, the HSM/KMS paved path, and disk
  encryption as operator responsibility.
- [`PRIVACY.md`](PRIVACY.md): the data-minimization posture (what is never
  collected or stored).
- [`DR.md`](DR.md): backup encryption and disaster-recovery procedures.
- [`../PRODUCTION-READINESS.md`](../PRODUCTION-READINESS.md): the honest gap
  ledger; this doc closes the at-rest *posture* item and leaves the host
  encryption + key custodian as the operator-gated remainder.
- `polaris_sql/01_schema.sql`: the `Individual` and `TokenStateEpochLeaf` tables,
  including the plaintext-`proof_path` note this posture is grounded in.
