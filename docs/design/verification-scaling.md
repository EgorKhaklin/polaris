# Verifying post-quantum signatures at national scale

The benchmark (`polaris_sim`, [BENCHMARK.md](../reference/BENCHMARK.md)) measured
real ML-DSA-65 signature verification at ~745/s on one core. A national
deployment needs thousands per second, sustained through failover and rolling
deploys. This is how Polaris gets there without weakening the guarantee that
matters.

## The two-witness cost, and where it belongs

Every real signature check ran through `verify_both`: two independent
implementations, liboqs AND the OpenSSL/`cryptography` ML-DSA-65 verifier, both
of which must agree. That cross-check is a defense against a bug in one
implementation silently accepting a bad signature. It costs two verifies plus a
digest, ~1.35 ms, so ~745/s per core.

The critical moment for that defense is **issuance**. `signature_with_key_for_token`
two-witnesses the signature it just produced and **refuses to persist it** unless
both implementations accept it. So a stored real signature is, by construction,
known to verify under both liboqs and OpenSSL.

## Single-witness verify-at-use

Because issuance already established two-witness validity, **verification at use**
does not need to re-run both. One witness (liboqs) re-confirms authenticity and
detects any tampering or substitution, at about ten times the rate:

| Path | per core | when used |
|---|---|---|
| Two-witness (`verify_stored_signature(..., witnesses="both")`) | ~745/s | issuance self-check; the strict display path; anywhere maximum rigor is wanted |
| **Single-witness (`witnesses="single"`)** | **~7,800/s** | the verify-AT-USE throughput path |

A tampered or forged signature still fails single-witness verification (liboqs
rejects it); the only thing dropped at use is the redundant second
implementation of the same check. The two-witness path remains available and is
still the default, so nothing silently weakens: a caller opts into `"single"` on
the throughput path.

## Why it scales cleanly

Verification needs **only the public key** stored with the signature. No private
key, no custody driver, no HSM, no KMS is touched (those are issuance-only). Each
verify opens its own liboqs context and holds no shared mutable state. So
verification is embarrassingly parallel:

- **Across gunicorn workers.** Sync workers each verify in their own process; W
  workers deliver ~W x the per-core rate. Use long-lived (preloaded) workers,
  not spawn-per-request, or process start-up dominates.
- **Across HA replicas.** The verify route is replica-routed (a read); add app
  containers/hosts behind the edge and the capacity adds up, with no shared
  secret to coordinate.

Projected fleet capacity on an 8-core node: ~62,000/s single-witness (measured
per-core rate x cores), before adding replicas. Thousands per second is reached
on a single core; tens of thousands per node.

## The verify endpoint

`GET /api/tokens/<id>/verify` (login-gated, replica-routed) cryptographically
verifies a token's active signature at use, single-witness, and returns whether
the signature is authentic, whether the token is currently usable (signature
valid AND status ACTIVE), and the per-signature result. This is the
throughput-oriented verification capability (a seed of the roadmap's P3.4
relying-party verification API); the login-gated `/tokens/<id>` display page
keeps the strict two-witness check since it verifies one signature per view.

## Under HA, failover, and rolling deploys

Verification is stateless and read-only, so it inherits the HA properties the
failover and rolling-deploy drills already prove: a verify request is served by
any healthy replica, routed to a read path, and a rolling deploy replaces
containers one colour at a time behind the edge. Certifying the verification
throughput specifically through an induced failover and a rolling deploy (the
load holds, zero verification errors across the transition) is the next step and
closes the roadmap's P2.9.
