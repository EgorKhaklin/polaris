# Token signatures

**Reader:** an engineer or an assessor. **Job:** How a signature is produced, stored and verified across a rotation.

This file is the canonical write-up for Polaris's token-signature primitive:
where signatures live, how they're verified, and what the
post-quantum-cryptography scaffold (`POLARIS_USE_REAL_PQC`) actually gates.

---

## What `TokenSignature` is

`TokenSignature` is the schema-level binding between an `IdentityToken` and
the cryptographic proof that the issuing agency authorized it. Per C7 (no
hardcoded cryptography), the algorithm choice is data, not code:

```
IdentityToken ── 1:1 ── TokenSignature ── N:1 ── CryptographicAlgorithm
```

Each row in `TokenSignature` records:
- `token_id` — FK to `IdentityToken`
- `algorithm_id` — FK to `CryptographicAlgorithm` (the active algorithm at
  the moment of signing; allows post-issuance algorithm-rotation forensics)
- `signature_bytes` — the actual signature payload
- `signed_at` — timestamp; constrained `<=` `IdentityToken.issued_at` by
  trigger (signatures cannot post-date the tokens they sign)

The 1:1 relation is enforced by a partial unique index on `token_id`. There
is no schema path for a token to exist without a signature.

## Operating modes

The primitive runs in one of two modes, gated by `POLARIS_USE_REAL_PQC`:

- **Flag off (default).** `polaris_web/pqc_signing.py:sign_token` returns
  a deterministic string derived from `(token_value, algorithm_name,
  agency_id)`. NOT post-quantum signed; the value passes the schema's
  byte-length constraint but is verifiable only against itself.
- **Flag on.** `pqc_signing.py` imports `oqs` and signs against
  `liboqs`'s ML-DSA-65 (FIPS 204) implementation. Activation requires
  liboqs native library installed + `pip install oqs`. Operator-side
  activation; see `scripts/polaris-pqc-status.sh` for the readiness probe.

The flag-off default is intentional: real PQC signatures are only
load-bearing if the operator has a key-management plan. Until then, the
deterministic stub preserves the schema's structural invariants (every
token has a row in TokenSignature) without claiming cryptographic
guarantees the deployment can't actually provide.

## Test coverage

| Surface | Tests |
|---|---|
| Schema (table shape, 1:1 unique index, FK ordering trigger) | `polaris_sql/08_tests.sql` |
| `pqc_signing.sign_token` deterministic path | `polaris_web/test_app.py::PQCTests` |
| `pqc_signing.verify_signature` round-trip | `polaris_web/test_app.py::PQCTests` |
| Structural invariant: every IdentityToken has a TokenSignature row | `polaris_web/test_structural_invariants.py` |
| Algorithm-rotation forensics (TokenSignature.algorithm_id preserved across UPDATE CryptographicAlgorithm) | `polaris_sql/08_tests.sql` |

The PQC-flag-on path is not in CI (no liboqs in the test image). It is
covered by `scripts/polaris-pqc-status.sh` invoked manually by the
operator after enabling the flag.

## What this primitive does NOT do

- It does NOT bind the signature to the holder's biometric or device
  (DeviceBinding is a separate table for that).
- It does NOT support multi-signature schemes (see
  `docs/design/multi-sig-migration.md` for the transitional state and
  the deferral of full multi-sig to a future ship).
- It does NOT prove revocation (see `RevocationList` for that surface;
  TokenSignature records the original signing event only).
- It does NOT support delegated signing. Per C10, an agency's signing key
  is held by the agency itself; Polaris records only the resulting
  signature, never the key material.

## Maintenance posture

The primitive is stable. Maintenance work would land in three classes:
1. **PQC migration** — flipping `POLARIS_USE_REAL_PQC=1` in production
   once the operator commissions a KMS.
2. **Algorithm rotation** — adding a new row to `CryptographicAlgorithm`
   and routing new tokens to it; old tokens keep their original
   `algorithm_id`.
3. **Signature-payload size tightening** — current schema constraint is
   `length(signature_bytes) <= 4096`; ML-DSA-65 produces ~3.3KB
   signatures, so 4096 is the tight upper bound. A larger algorithm (e.g.
   ML-DSA-87) would require a schema migration.

## Cross-references

- `polaris_web/pqc_signing.py` — the Python signing surface
- `polaris_sql/01_schema.sql::TokenSignature` — table definition
- `polaris_sql/06_triggers.sql::tg_token_signature_*` — append-only +
  ordering triggers
- `scripts/polaris-pqc-status.sh` — operator readiness probe
- `MISSION.md` §C7 — the constitutional clause this primitive satisfies
