"""polaris_web/pqc_signing.py — real ML-DSA-65 (FIPS 204) signing path.

v9.24 / BIG MISSION Tier 2 #7. Until this module, Polaris's headline
post-quantum claim was rendered by a deterministic string in
`token_value`. The Anti-Architect's AP8 (larping) detector named this
as the most damning critique: "the system's headline claim is post-
quantum signing and it is currently a deterministic string."

This module integrates the FIPS 204 (ML-DSA-65) signing path via
liboqs-python (the Open Quantum Safe project's Python binding to the
liboqs C library). It is **gated behind POLARIS_USE_REAL_PQC=1**
(default OFF) so operators opt in deliberately after verifying their
deployment has the native library installed.

**Activation procedure (operator):**

    1. Install native liboqs (apt-get install liboqs-dev or build from
       https://github.com/open-quantum-safe/liboqs)
    2. pip install oqs (or pip install liboqs-python)
    3. Verify: python3 -c "import polaris_web.pqc_signing as p; print(p.availability_report())"
    4. Set POLARIS_USE_REAL_PQC=1 in production env
    5. This makes the `uc1_issue` route store real ML-DSA-65 signatures in
       `TokenSignature.signature_bytes` (and `sign()` / `verify()` produce
       and check real signatures).

**Wiring status (v9.58): WIRED.** `app.py`'s `uc1_issue` route calls
`signature_bytes_for_token()` and passes the result to
`uc1_issue_and_activate(..., p_signature_bytes := ...)`, so every token
issued through the app gets its `TokenSignature.signature_bytes` from this
module. With the flag unset (default) that is a deterministic SHA3-256
placeholder; with `POLARIS_USE_REAL_PQC=1` + liboqs it is a real ML-DSA-65
signature. The procedure COALESCEs to the legacy placeholder string only for
direct SQL callers that pass no signature, so existing tooling is unaffected.
`polaris_checks.check_pqc_signing_wired` asserts this wiring stays in place.

Per the two-witness principle (`DEVNOTES/two-witness-principle.md`),
the ML-DSA-65 verdict is a **lone verifier** (single liboqs impl, no
independent second witness) and is recorded there as an explicit
ABSTAIN instance until either a second witness is added or the path is
wired and verdict-two-witnessed.

**Honest accounting (per the Anti-Architect's joint resolution):**

This module ships the integration. It does NOT migrate existing
tokens. Pre-v9.24 tokens carry deterministic `token_value` strings;
the verifier accepts them as a legacy class. The migration to
all-real-signatures is a separate operator decision documented in
docs/operator/PQC-MIGRATION.md.

**If `oqs` is not importable**, `is_available()` returns False and
`sign()` raises `PQCUnavailableError`. The flag-off default means
the rest of Polaris is unaffected. With flag-on but oqs missing,
token issuance fails fast (loud) rather than silently falling back
to the deterministic stub.
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from typing import Optional


class PQCUnavailableError(RuntimeError):
    """Raised when POLARIS_USE_REAL_PQC=1 but oqs is not importable."""


class SigningError(RuntimeError):
    """Raised when a produced signature fails its own verification self-check —
    a real signature that does not verify against its key means broken key
    material or liboqs, and must never be persisted."""


# Detect liboqs-python at import time (defer ImportError so module
# always imports — callers introspect via is_available()).
_OQS_AVAILABLE = False
_OQS_IMPORT_ERROR: Optional[str] = None
_OQS_VERSION: Optional[str] = None

try:
    import oqs  # type: ignore
    _OQS_AVAILABLE = True
    _OQS_VERSION = getattr(oqs, "__version__", "unknown")
except ImportError as e:
    _OQS_IMPORT_ERROR = str(e)
    _OQS_AVAILABLE = False


# FIPS 204 algorithm identifier used by liboqs (per OQS naming)
_ALG_NAME = "ML-DSA-65"


@dataclass(frozen=True)
class SigningResult:
    """One signed token's outputs.

    `algorithm_name` ties to the CryptographicAlgorithm table row (C7).
    `public_key_hex` is the verifier's lookup key.
    `signature_hex` is what gets stored alongside token_value.
    `message_hash_hex` is the hash that was signed (sha3_256(token_value)).
    """
    algorithm_name: str
    public_key_hex: str
    signature_hex: str
    message_hash_hex: str


def is_available() -> bool:
    """True iff liboqs-python is importable.

    Cheap; safe to call from request paths to short-circuit.
    """
    return _OQS_AVAILABLE


def is_enabled() -> bool:
    """True iff POLARIS_USE_REAL_PQC=1 AND oqs is available.

    Production check — issuance code uses this as the gate. The flag
    must be set explicitly; we never silently enable.
    """
    flag_set = os.environ.get("POLARIS_USE_REAL_PQC", "0") == "1"
    return flag_set and _OQS_AVAILABLE


def availability_report() -> dict:
    """Structured introspection for operators + CI.

    Used by `scripts/polaris-pqc-status.sh` to render a clear
    operator message.
    """
    return {
        "module_imported": True,
        "oqs_available": _OQS_AVAILABLE,
        "oqs_version": _OQS_VERSION,
        "oqs_import_error": _OQS_IMPORT_ERROR,
        "flag_set": os.environ.get("POLARIS_USE_REAL_PQC", "0") == "1",
        "is_enabled": is_enabled(),
        "algorithm": _ALG_NAME,
        "notes": (
            "Per BIG MISSION v9.24 Sanctum T2#7: real signing ships as "
            "scaffolding behind POLARIS_USE_REAL_PQC=1. Migration of "
            "existing token_value entries is a separate operator decision."
        ),
    }


# Long-lived signing keypair. Production sets POLARIS_PQC_SIGNING_KEY_FILE to a
# JSON file {algorithm, secret_key_hex, public_key_hex} (mode 0600). The private
# key is the issuer's signing key — in a real deployment it belongs in an HSM/KMS;
# this file is the loading MECHANISM the operator points at their custodied
# material. When set, every signature uses the SAME key, so its public key is a
# stable, publishable trust anchor that verifiers check against. When unset
# (dev/test), sign() falls back to an ephemeral per-call keypair, which is NOT
# verifiable against any known anchor and must never be the production path.
_PERSISTENT_KEY_ENV = "POLARIS_PQC_SIGNING_KEY_FILE"
_PERSISTENT_KEYPAIR: Optional[tuple] = None
_PERSISTENT_LOADED = False


def _load_persistent_keypair() -> Optional[tuple]:
    """Return (secret_key_bytes, public_key_bytes) from the configured key file,
    or None if POLARIS_PQC_SIGNING_KEY_FILE is unset. Cached after first load.
    Raises RuntimeError on a malformed/mismatched key file (fail loud — a bad
    signing key must not silently degrade to ephemeral)."""
    global _PERSISTENT_KEYPAIR, _PERSISTENT_LOADED
    if _PERSISTENT_LOADED:
        return _PERSISTENT_KEYPAIR
    _PERSISTENT_LOADED = True
    path = os.environ.get(_PERSISTENT_KEY_ENV)
    if not path:
        _PERSISTENT_KEYPAIR = None
        return None
    try:
        with open(path) as fh:
            data = json.load(fh)
        if data.get("algorithm") != _ALG_NAME:
            raise RuntimeError(
                f"{_PERSISTENT_KEY_ENV} algorithm {data.get('algorithm')!r} != {_ALG_NAME}")
        keypair = (bytes.fromhex(data["secret_key_hex"]), bytes.fromhex(data["public_key_hex"]))
    except (OSError, ValueError, KeyError) as exc:
        raise RuntimeError(f"{_PERSISTENT_KEY_ENV}={path} is unreadable/malformed: {exc}") from exc
    _PERSISTENT_KEYPAIR = keypair
    return keypair


def generate_keypair() -> dict:
    """Generate a fresh ML-DSA-65 keypair for POLARIS_PQC_SIGNING_KEY_FILE.

    Returns {algorithm, secret_key_hex, public_key_hex}. The secret key is the
    issuer's long-lived signing key: write it to a 0600 file (or load it into an
    HSM/KMS) and publish the public key as the verification trust anchor.
    """
    if not _OQS_AVAILABLE:
        raise PQCUnavailableError(
            f"liboqs-python is not importable: {_OQS_IMPORT_ERROR}.")
    import oqs as _oqs  # type: ignore
    with _oqs.Signature(_ALG_NAME) as signer:
        public_key = signer.generate_keypair()
        secret_key = signer.export_secret_key()
    return {
        "algorithm": _ALG_NAME,
        "secret_key_hex": secret_key.hex(),
        "public_key_hex": public_key.hex(),
    }


def sign(message: bytes) -> SigningResult:
    """Sign `message` with ML-DSA-65.

    Uses the long-lived keypair from POLARIS_PQC_SIGNING_KEY_FILE when configured
    (so the public key is a stable trust anchor); otherwise generates an ephemeral
    per-call keypair (the dev/test fallback — not verifiable against a known anchor).

    Raises PQCUnavailableError if oqs is not importable.
    Returns SigningResult with public_key, signature, message hash.
    """
    if not _OQS_AVAILABLE:
        raise PQCUnavailableError(
            f"liboqs-python is not importable: {_OQS_IMPORT_ERROR}. "
            "Install per polaris_web/pqc_signing.py module docstring."
        )

    # Deferred import (mypy/IDE don't see it pre-import)
    import oqs as _oqs  # type: ignore

    # SHA3-256 the message for binding to a fixed-size digest
    digest = hashlib.sha3_256(message).digest()

    keypair = _load_persistent_keypair()
    if keypair is not None:
        secret_key, public_key = keypair
        with _oqs.Signature(_ALG_NAME, secret_key=secret_key) as signer:
            signature = signer.sign(digest)
    else:
        # No persistent key configured — ephemeral keypair (dev/test only).
        with _oqs.Signature(_ALG_NAME) as signer:
            public_key = signer.generate_keypair()
            signature = signer.sign(digest)

    return SigningResult(
        algorithm_name=_ALG_NAME,
        public_key_hex=public_key.hex(),
        signature_hex=signature.hex(),
        message_hash_hex=digest.hex(),
    )


# Label recorded for the dependency-free placeholder so it can never be
# mistaken for a real signature in logs, tests, or operator tooling.
PLACEHOLDER_LABEL = "DETERMINISTIC-PLACEHOLDER-SHA3-256"


def signature_bytes_for_token(token_value: str) -> tuple:
    """Produce the bytes stored in `TokenSignature.signature_bytes` at issuance.

    This is the single entry point the issuance route (`uc1_issue`) calls, so
    token issuance routes through this module rather than writing a hardcoded
    SQL placeholder. Returns `(signature_bytes, algorithm_label)`:

    - **Flag unset (default, including CI):** a deterministic SHA3-256 binding
      of `token_value`. This is NOT a cryptographic signature (there is no
      private key); it is a reproducible placeholder that lets the reference
      implementation run without the native library. Label: `PLACEHOLDER_LABEL`.
    - **`POLARIS_USE_REAL_PQC=1` + liboqs available:** a real ML-DSA-65
      (FIPS 204) signature over `token_value`. Label: `"ML-DSA-65"`.
    - **Flag set but liboqs unavailable:** raises `PQCUnavailableError` (fail
      loud; never silently downgrade an operator who asked for real PQC).

    The caller stores the bytes in `TokenSignature.signature_bytes` and records
    the algorithm in `TokenSignature.algorithm_id` (C7: algorithm by reference).
    """
    sig, label, _pk = signature_with_key_for_token(token_value)
    return sig, label


def signature_with_key_for_token(token_value: str) -> tuple:
    """Like `signature_bytes_for_token`, but also returns the signing PUBLIC KEY.

    Returns `(signature_bytes, algorithm_label, public_key_hex_or_none)`. The
    caller stores the public key WITH the signature (TokenSignature.
    signing_public_key_hex) so verification at use is self-contained — no live
    trust-anchor lookup, and it survives key rotation. For the placeholder path
    the third element is None (there is no key).
    """
    flag_set = os.environ.get("POLARIS_USE_REAL_PQC", "0") == "1"
    if flag_set and not _OQS_AVAILABLE:
        raise PQCUnavailableError(
            "POLARIS_USE_REAL_PQC=1 but liboqs-python is not importable: "
            f"{_OQS_IMPORT_ERROR}. Install per this module's docstring or unset the flag."
        )
    if flag_set:
        # flag_set AND _OQS_AVAILABLE (otherwise we raised above)
        result = sign(token_value.encode("utf-8"))
        # Enforce verification on the issuance path: the signature we just
        # produced MUST verify against its own public key before it is handed to
        # the DB. A real signature that fails to self-verify means broken key
        # material or liboqs — refuse to persist an unverifiable signature rather
        # than silently store something no verifier will ever accept.
        if not verify(token_value.encode("utf-8"), result.signature_hex, result.public_key_hex):
            raise SigningError(
                "produced ML-DSA-65 signature failed self-verification; refusing to issue")
        return bytes.fromhex(result.signature_hex), result.algorithm_name, result.public_key_hex
    # Flag off: deterministic, dependency-free placeholder (not a signature).
    digest = hashlib.sha3_256(token_value.encode("utf-8")).digest()
    return digest, PLACEHOLDER_LABEL, None


def verify_stored_signature(
    token_value: str,
    signature_bytes: bytes,
    signing_public_key_hex: Optional[str],
) -> bool:
    """Verify a stored TokenSignature against its token using the public key
    stored WITH the signature — self-contained, no live trust-anchor lookup.

    - ``signing_public_key_hex`` non-empty: a real ML-DSA-65 signature, verified
      against that key (a genuine authenticity proof). Returns False if liboqs is
      unavailable (a real signature cannot be checked without it).
    - ``signing_public_key_hex`` None/empty: the deterministic SHA3-256
      placeholder; an integrity recompute + constant-time compare (NOT an
      authenticity proof — there is no key).
    """
    if signing_public_key_hex:
        if not _OQS_AVAILABLE:
            return False
        return verify(token_value.encode("utf-8"), signature_bytes.hex(), signing_public_key_hex)
    import hmac
    expected = hashlib.sha3_256(token_value.encode("utf-8")).digest()
    return hmac.compare_digest(signature_bytes, expected)


def verify(
    message: bytes,
    signature_hex: str,
    public_key_hex: str,
) -> bool:
    """Verify a signature against (message, public_key).

    Returns True if the signature is valid. Returns False on any
    verification failure (does NOT raise — verification is a binary
    yes/no for the calling code).

    Raises PQCUnavailableError if oqs is not importable.
    """
    if not _OQS_AVAILABLE:
        raise PQCUnavailableError(
            f"liboqs-python is not importable: {_OQS_IMPORT_ERROR}"
        )

    import oqs as _oqs  # type: ignore

    digest = hashlib.sha3_256(message).digest()
    try:
        public_key = bytes.fromhex(public_key_hex)
        signature = bytes.fromhex(signature_hex)
    except ValueError:
        return False

    try:
        with _oqs.Signature(_ALG_NAME) as verifier:
            return verifier.verify(digest, signature, public_key)
    except Exception:
        return False


def trust_anchor_public_key_hex() -> Optional[str]:
    """The published trust anchor: the persistent signing key's public key (hex).

    This is the key a verifier checks token signatures against. Returns None when
    no persistent key is configured (`POLARIS_PQC_SIGNING_KEY_FILE` unset) — there
    is then no stable, publishable anchor, only per-process ephemeral keys, so a
    real signature cannot be verified at use.
    """
    keypair = _load_persistent_keypair()
    if keypair is None:
        return None
    _secret, public = keypair
    return public.hex()


def verify_token_signature(
    token_value: str,
    signature_bytes: bytes,
    algorithm_label: str,
) -> bool:
    """Verify a stored `TokenSignature` against its token — the use-path check.

    Dispatch on the algorithm recorded WITH the signature (not the current
    process mode), so a token signed under one mode verifies correctly later:

    - ``"ML-DSA-65"`` — a real signature. Verified against the trust-anchor
      public key (`trust_anchor_public_key_hex`). Returns False when no trust
      anchor is configured (cannot prove authenticity without it) or the
      signature does not check out. This is a genuine authenticity proof: only
      the holder of the anchor's private key could have produced it.
    - ``PLACEHOLDER_LABEL`` — the deterministic SHA3-256 binding. Verification is
      an integrity recompute + constant-time compare. This is NOT an authenticity
      proof (there is no key); it only confirms the bytes match `token_value`.
    - anything else — False (unknown signature scheme).
    """
    if algorithm_label == _ALG_NAME:
        anchor = trust_anchor_public_key_hex()
        if not anchor:
            return False
        return verify(token_value.encode("utf-8"), signature_bytes.hex(), anchor)
    if algorithm_label == PLACEHOLDER_LABEL:
        import hmac
        expected = hashlib.sha3_256(token_value.encode("utf-8")).digest()
        return hmac.compare_digest(signature_bytes, expected)
    return False


def smoke_test() -> bool:
    """Roundtrip: sign + verify a known message.

    Returns True if both succeed and verifier accepts. Used by CI
    and by scripts/polaris-pqc-status.sh to confirm working state.
    Returns False on any failure (graceful — caller decides whether
    to escalate).
    """
    if not _OQS_AVAILABLE:
        return False
    msg = b"polaris-pqc-smoke-test-v9.24"
    try:
        result = sign(msg)
        return verify(msg, result.signature_hex, result.public_key_hex)
    except Exception:
        return False
