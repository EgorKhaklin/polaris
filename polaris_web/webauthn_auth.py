"""
============================================================================
POLARIS — WebAuthn-MFA module (v8.97 / Position B)
============================================================================

Implements WebAuthn registration + assertion for the admin operator role,
per Position B of sanctum/2026-05-14-webauthn-operator-auth.md.

Architecture:
  - Registration ceremony: user is already password-authenticated; the
    server generates random challenge + relying-party options; the
    browser invokes navigator.credentials.create(); the server verifies
    the attestation and persists the credential in OperatorWebauthnCredential.
  - Assertion ceremony: after password succeeds in /login, the server
    generates a challenge bound to the user's enrolled credential IDs;
    the browser invokes navigator.credentials.get(); the server verifies
    the assertion (signature + counter + origin) and completes the login.

Defense-in-depth:
  - Challenges are random 32-byte values, single-use per session
  - Origin-checked via the webauthn library against POLARIS_DOMAIN
  - Counter must be > stored value (CTAP2 replay protection); counter=0
    accepted only when stored counter is also 0 (platform authenticator
    case documented in COSE spec)
  - Hardware-only enforcement via POLARIS_WEBAUTHN_HARDWARE_ONLY=1 env
    knob (default = both platform + hardware allowed)

Sanctum §IV resolutions applied (architect-recommended defaults):
  1. MFA required for admin, optional for operator, not for auditor
  2. Both platform + hardware authenticators allowed (knob to restrict)
  3. Recovery: second-admin pairing (polaris-recover-admin.sh) AND
     printed mnemonic (polaris-generate-recovery-code.sh)
  4. 30-day enrollment deadline for existing admins; new admins enrolled
     at account-creation time
  5. End-to-end + adversarial + recovery drills all green before close

This module returns dicts ready for JSON encoding by the caller; it
never reads or writes session state directly (the route handlers do).
============================================================================
"""

import os
import json
import base64
from datetime import datetime, timedelta, timezone

from webauthn import (
    generate_registration_options,
    verify_registration_response,
    generate_authentication_options,
    verify_authentication_response,
    options_to_json,
)
from webauthn.helpers.structs import (
    AuthenticatorSelectionCriteria,
    UserVerificationRequirement,
    PublicKeyCredentialDescriptor,
    AuthenticatorAttachment,
    ResidentKeyRequirement,
)
from webauthn.helpers.cose import COSEAlgorithmIdentifier


# ----------------------------------------------------------------------------
# Configuration
# ----------------------------------------------------------------------------

def _rp_id():
    """Relying-Party ID — the domain WebAuthn binds the credential to.
    Defaults to POLARIS_DOMAIN; falls back to localhost for dev."""
    domain = os.environ.get('POLARIS_DOMAIN', '').strip()
    if domain:
        # Strip scheme + port if accidentally present
        for prefix in ('https://', 'http://'):
            if domain.startswith(prefix):
                domain = domain[len(prefix):]
        domain = domain.split('/')[0].split(':')[0]
        return domain
    return 'localhost'


def _rp_name():
    return os.environ.get('POLARIS_WEBAUTHN_RP_NAME', 'Polaris')


def _expected_origin():
    """The full origin the assertion must match against."""
    domain = _rp_id()
    if domain == 'localhost':
        # Dev: accept the port the app is listening on
        port = os.environ.get('POLARIS_PORT', '2222')
        return f'http://localhost:{port}'
    return f'https://{domain}'


def _hardware_only():
    """If POLARIS_WEBAUTHN_HARDWARE_ONLY=1, refuse platform authenticators
    (Touch ID / Windows Hello / Android). Default: allow both."""
    return os.environ.get('POLARIS_WEBAUTHN_HARDWARE_ONLY', '').strip() == '1'


# Role policy from §IV.1
ROLES_REQUIRING_WEBAUTHN = {'admin'}
ROLES_OPTIONAL_WEBAUTHN  = {'operator'}
ROLES_EXEMPT_WEBAUTHN    = {'auditor'}


# ----------------------------------------------------------------------------
# Encoding helpers
# ----------------------------------------------------------------------------

def _b64url_encode(raw_bytes):
    """Base64url-encode, no padding-stripping (the spec keeps padding)."""
    return base64.urlsafe_b64encode(raw_bytes).decode('ascii')


def _b64url_decode(s):
    """Decode base64url; pad as needed."""
    s = s.strip()
    pad = (-len(s)) % 4
    return base64.urlsafe_b64decode(s + ('=' * pad))


# ----------------------------------------------------------------------------
# Registration ceremony (called from /auth/webauthn/register/{begin,finish})
# ----------------------------------------------------------------------------

def build_registration_options(user_id, username, existing_credential_ids):
    """Generate the PublicKeyCredentialCreationOptions JSON that the browser
    will pass to navigator.credentials.create().

    Returns a dict with:
      - options_json: a JSON string ready to ship to the browser
      - challenge: the base64url-encoded challenge to persist server-side
                   for the matching /finish call (one-shot)
    """
    # Authenticator selection per §IV.2
    if _hardware_only():
        # Hardware token only (YubiKey class): cross-platform
        selection = AuthenticatorSelectionCriteria(
            authenticator_attachment=AuthenticatorAttachment.CROSS_PLATFORM,
            resident_key=ResidentKeyRequirement.DISCOURAGED,
            user_verification=UserVerificationRequirement.PREFERRED,
        )
    else:
        # Allow both platform + cross-platform; let the user pick
        selection = AuthenticatorSelectionCriteria(
            resident_key=ResidentKeyRequirement.DISCOURAGED,
            user_verification=UserVerificationRequirement.PREFERRED,
        )

    # Exclude credentials already enrolled to this user (prevents accidental
    # double-registration of the same authenticator)
    exclude = [
        PublicKeyCredentialDescriptor(id=_b64url_decode(cid))
        for cid in existing_credential_ids
    ]

    options = generate_registration_options(
        rp_id=_rp_id(),
        rp_name=_rp_name(),
        user_id=str(user_id).encode('utf-8'),
        user_name=username,
        user_display_name=username,
        authenticator_selection=selection,
        exclude_credentials=exclude,
        supported_pub_key_algs=[
            COSEAlgorithmIdentifier.ECDSA_SHA_256,
            COSEAlgorithmIdentifier.EDDSA,
            COSEAlgorithmIdentifier.RSASSA_PKCS1_v1_5_SHA_256,
        ],
        # Timeout is advisory to the browser; we enforce server-side via
        # the challenge's session lifetime instead.
        timeout=60_000,
    )
    return {
        'options_json': options_to_json(options),
        'challenge_b64url': _b64url_encode(options.challenge),
    }


def verify_registration(
    credential_json,
    expected_challenge_b64url,
):
    """Verify the response from navigator.credentials.create().

    Returns a dict ready for INSERT INTO OperatorWebauthnCredential:
      credential_id, public_key (bytes), sign_count, transports,
      attestation_format, aaguid (str or None)

    Raises webauthn.helpers.exceptions.* on invalid attestation.
    """
    verification = verify_registration_response(
        credential=credential_json,
        expected_challenge=_b64url_decode(expected_challenge_b64url),
        expected_rp_id=_rp_id(),
        expected_origin=_expected_origin(),
        require_user_verification=False,
    )

    # The library returns aaguid as a string ("00000000-...") or None
    aaguid = getattr(verification, 'aaguid', None)
    if aaguid is not None:
        aaguid = str(aaguid)
        if aaguid == '00000000-0000-0000-0000-000000000000':
            # Some authenticators don't report an AAGUID; treat as NULL
            aaguid = None

    # Transports may be a list of enum values; collapse to comma-string
    transports_raw = credential_json.get('response', {}).get('transports')
    transports = None
    if transports_raw:
        if isinstance(transports_raw, list):
            transports = ','.join(str(t) for t in transports_raw)[:120]
        else:
            transports = str(transports_raw)[:120]

    fmt = getattr(verification, 'fmt', None)
    if fmt is not None:
        fmt = str(fmt)[:40]

    return {
        'credential_id':       _b64url_encode(verification.credential_id),
        'public_key':          verification.credential_public_key,
        'sign_count':          int(verification.sign_count or 0),
        'transports':          transports,
        'attestation_format':  fmt,
        'aaguid':              aaguid,
    }


# ----------------------------------------------------------------------------
# Assertion ceremony (called from /auth/webauthn/assert/{begin,finish})
# ----------------------------------------------------------------------------

def build_authentication_options(allowed_credential_ids):
    """Generate the PublicKeyCredentialRequestOptions JSON for
    navigator.credentials.get(). Only credentials in allowed_credential_ids
    will be eligible — the server already looked these up by user_id."""
    allow = [
        PublicKeyCredentialDescriptor(id=_b64url_decode(cid))
        for cid in allowed_credential_ids
    ]
    options = generate_authentication_options(
        rp_id=_rp_id(),
        allow_credentials=allow,
        user_verification=UserVerificationRequirement.PREFERRED,
        timeout=60_000,
    )
    return {
        'options_json': options_to_json(options),
        'challenge_b64url': _b64url_encode(options.challenge),
    }


def verify_authentication(
    credential_json,
    expected_challenge_b64url,
    stored_public_key,
    stored_sign_count,
):
    """Verify the response from navigator.credentials.get().

    Returns:
      {'new_sign_count': int}  if verification succeeded — caller should
                               UPDATE OperatorWebauthnCredential SET
                               sign_count=new_sign_count, last_used_at=now()
                               WHERE credential_id=...

    Raises webauthn.helpers.exceptions.* on invalid assertion (caller
    should AuthAuditLog WEBAUTHN_ASSERTION_FAILED).
    """
    verification = verify_authentication_response(
        credential=credential_json,
        expected_challenge=_b64url_decode(expected_challenge_b64url),
        expected_rp_id=_rp_id(),
        expected_origin=_expected_origin(),
        credential_public_key=bytes(stored_public_key),
        credential_current_sign_count=int(stored_sign_count),
        require_user_verification=False,
    )
    return {'new_sign_count': int(verification.new_sign_count or 0)}


# ----------------------------------------------------------------------------
# Login-flow helper (called from security.py:authenticate AFTER password OK)
# ----------------------------------------------------------------------------

def webauthn_status_for_user(conn, user_id, role):
    """Determine what the login flow should do for this user, post-password.

    Returns one of:
      'not_required'   — role is auditor, OR webauthn_required_after is NULL,
                         OR (role is operator AND no credentials enrolled).
                         Login completes immediately.
      'grace_period'   — webauthn_required_after is in the future AND no
                         credential enrolled. Login completes; the response
                         page reminds the user to enroll before deadline.
      'mfa_required'   — credential enrolled. The login route holds the
                         user_id in a partial-auth session and forwards to
                         /auth/webauthn/assert.
      'mfa_overdue'    — webauthn_required_after is in the past AND no
                         credential enrolled. Login REFUSED with operator
                         guidance to contact a second admin for
                         polaris-recover-admin.sh, or to enroll out-of-band.

    The caller (security.py:authenticate) translates this into the right
    response: complete the login / redirect to assert / show grace banner /
    refuse login.
    """
    if role in ROLES_EXEMPT_WEBAUTHN:
        return 'not_required'

    with conn.cursor() as cur:
        cur.execute(
            "SELECT webauthn_required_after FROM AppUser WHERE user_id = %s",
            (user_id,)
        )
        row = cur.fetchone()
        if row is None:
            # User vanished mid-flight (rare race); fail safe.
            return 'mfa_overdue'

        required_after = row['webauthn_required_after']

        cur.execute(
            "SELECT count(*) AS n FROM OperatorWebauthnCredential "
            "WHERE user_id = %s",
            (user_id,)
        )
        cred_count = cur.fetchone()['n']

    now = datetime.now(timezone.utc)

    # Auditor exempt (handled above)
    # Admin: required_after governs; default NULL means not required yet
    # Operator: optional — only enforce if credential enrolled

    if role in ROLES_OPTIONAL_WEBAUTHN:
        # Operator: if they've enrolled a credential, require it; otherwise skip.
        return 'mfa_required' if cred_count > 0 else 'not_required'

    # Admin (role in ROLES_REQUIRING_WEBAUTHN)
    if cred_count > 0:
        return 'mfa_required'

    # No credential enrolled
    if required_after is None:
        return 'not_required'
    if required_after.tzinfo is None:
        required_after = required_after.replace(tzinfo=timezone.utc)
    if now < required_after:
        return 'grace_period'
    return 'mfa_overdue'


def days_until_webauthn_deadline(conn, user_id):
    """Return integer days until the user's webauthn_required_after, or
    None if no deadline. Negative = overdue."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT webauthn_required_after FROM AppUser WHERE user_id = %s",
            (user_id,)
        )
        row = cur.fetchone()
        if row is None or row['webauthn_required_after'] is None:
            return None
        deadline = row['webauthn_required_after']
        if deadline.tzinfo is None:
            deadline = deadline.replace(tzinfo=timezone.utc)
        delta = deadline - datetime.now(timezone.utc)
        return int(delta.total_seconds() // 86400)


def list_credentials_for_user(conn, user_id):
    """Return a list of dicts (one per enrolled credential) for the
    settings page. Does NOT return public_key bytes — those are not
    user-facing."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT credential_id, transports, device_label, "
            "       enrolled_at, last_used_at "
            "FROM OperatorWebauthnCredential "
            "WHERE user_id = %s "
            "ORDER BY enrolled_at DESC",
            (user_id,)
        )
        return [dict(r) for r in cur.fetchall()]


def existing_credential_ids_for_user(conn, user_id):
    """Helper used during registration to populate exclude_credentials."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT credential_id FROM OperatorWebauthnCredential "
            "WHERE user_id = %s",
            (user_id,)
        )
        return [r['credential_id'] for r in cur.fetchall()]


def insert_credential(conn, user_id, cred, device_label=None):
    """INSERT a verified credential. Caller must commit."""
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO OperatorWebauthnCredential ("
            "    credential_id, user_id, public_key, sign_count, "
            "    transports, attestation_format, aaguid, device_label"
            ") VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
            (
                cred['credential_id'],
                user_id,
                cred['public_key'],
                cred['sign_count'],
                cred['transports'],
                cred['attestation_format'],
                cred['aaguid'],
                (device_label[:100] if device_label else None),
            )
        )


def fetch_credential(conn, credential_id):
    """Fetch one credential by its raw id (base64url encoded). Returns
    dict or None."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT credential_id, user_id, public_key, sign_count "
            "FROM OperatorWebauthnCredential WHERE credential_id = %s",
            (credential_id,)
        )
        row = cur.fetchone()
        return dict(row) if row else None


def update_credential_after_use(conn, credential_id, new_sign_count):
    """Mark credential as last-used now() and bump its sign_count.
    Caller must commit."""
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE OperatorWebauthnCredential "
            "SET sign_count = %s, last_used_at = now() "
            "WHERE credential_id = %s",
            (new_sign_count, credential_id)
        )


def delete_credential(conn, user_id, credential_id):
    """Remove a credential. user_id parameter ensures users can only
    delete their own credentials. Returns True if deleted, False if
    not found. Caller must commit."""
    with conn.cursor() as cur:
        cur.execute(
            "DELETE FROM OperatorWebauthnCredential "
            "WHERE user_id = %s AND credential_id = %s",
            (user_id, credential_id)
        )
        return cur.rowcount == 1
