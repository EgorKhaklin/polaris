"""test_custody.py — the key custody abstraction (roadmap P1.2).

Three drivers, one contract: raw ML-DSA-65 public key + raw signature over the
SHA3-256 digest, so the two-witness verify path is unchanged whichever custody
signs. Each driver is exercised for real, not mocked:

  FileCustodyTests      the JSON key file, signed via liboqs (needs liboqs).
  AwsKmsCustodyTests    the driver's real botocore wire path (JSON 1.1, SigV4,
                        base64 blobs, SPKI parsing) against a local STAND-IN
                        that implements KMS's DescribeKey/GetPublicKey/Sign and
                        signs with OpenSSL's ML-DSA-65 (cryptography). The only
                        thing faked is the remote service, which cannot be real
                        in CI; the cryptography is real. An opt-in live test
                        runs against a real key when POLARIS_CUSTODY_AWSKMS_LIVE
                        _KEY_ID is set.
  Pkcs11CustodyTests    a real PKCS#11 token (CI: Kryoptic, a software token
                        with ML-DSA, job custody-pkcs11). Runs when
                        POLARIS_CUSTODY_PKCS11_MODULE is set; the CI job also
                        sets POLARIS_CUSTODY_PKCS11_REQUIRE=1 so a skip is a
                        failure there.
  EnvSelectionTests     driver selection, the PIN-never-from-env refusal, the
                        rotation anchors file.

Run: python3 -m unittest test_custody
"""

import base64
import hashlib
import json
import os
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import custody
import pqc_signing

try:
    from cryptography.hazmat.primitives.asymmetric import mldsa as _mldsa
    from cryptography.hazmat.primitives import serialization as _ser
    _MLDSA_OK = hasattr(_mldsa, "MLDSA65PrivateKey")
except Exception:
    _MLDSA_OK = False

_DIGEST = hashlib.sha3_256(b"token-ABC").digest()


def _verify(sig: bytes, pk: bytes, message: bytes = b"token-ABC") -> bool:
    """Verify with whichever independent witnesses this environment has: both
    (liboqs + OpenSSL) when liboqs is present, else OpenSSL alone."""
    if pqc_signing.is_available():
        return pqc_signing.verify_both(message, sig.hex(), pk.hex())
    v = pqc_signing._verify_second_witness(message, sig.hex(), pk.hex())
    assert v is not None, "no ML-DSA verifier available at all"
    return v


class _EnvSnapshot:
    KEYS = ("POLARIS_CUSTODY_DRIVER", "POLARIS_PQC_SIGNING_KEY_FILE", "POLARIS_CUSTODY_PKCS11_MODULE",
            "POLARIS_CUSTODY_PKCS11_TOKEN_LABEL", "POLARIS_CUSTODY_PKCS11_PIN_FILE", "POLARIS_CUSTODY_PKCS11_PIN",
            "POLARIS_CUSTODY_PKCS11_KEY_LABEL", "POLARIS_CUSTODY_AWSKMS_KEY_ID", "POLARIS_CUSTODY_AWSKMS_REGION",
            "POLARIS_CUSTODY_AWSKMS_ENDPOINT_URL", "POLARIS_PQC_TRUST_ANCHORS_FILE", "POLARIS_USE_REAL_PQC",
            "AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_DEFAULT_REGION")

    def __enter__(self):
        self._saved = {k: os.environ.get(k) for k in self.KEYS}
        for k in self.KEYS:
            os.environ.pop(k, None)
        custody.reset()
        return self

    def __exit__(self, *a):
        for k, v in self._saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        custody.reset()
        pqc_signing._PERSISTENT_LOADED = False


# ---------------------------------------------------------------------------
@unittest.skipUnless(pqc_signing.is_available(), "liboqs not installed")
class FileCustodyTests(unittest.TestCase):
    def setUp(self):
        self._env = _EnvSnapshot().__enter__()
        self.kp = pqc_signing.generate_keypair()
        self.kf = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False)
        json.dump(self.kp, self.kf); self.kf.close()

    def tearDown(self):
        os.unlink(self.kf.name)
        self._env.__exit__()

    def test_file_driver_signs_and_both_witnesses_verify(self):
        c = custody.FileCustody(self.kf.name)
        pk = c.public_key()
        self.assertEqual(pk.hex(), self.kp["public_key_hex"])
        sig = c.sign(_DIGEST)
        self.assertEqual(len(sig), custody.SIGNATURE_LEN)
        self.assertTrue(_verify(sig, pk))
        self.assertFalse(_verify(sig, pk, b"token-XYZ"))
        d = c.describe()
        self.assertEqual(d["driver"], "file")
        self.assertEqual(d["public_key_fingerprint"], custody.fingerprint(pk))
        self.assertNotIn(self.kf.name, json.dumps(d), "describe() must not leak the path")

    def test_env_selects_file_driver_and_pqc_signing_routes_through_it(self):
        os.environ["POLARIS_PQC_SIGNING_KEY_FILE"] = self.kf.name
        custody.reset()
        c = custody.get_custody()
        self.assertIsInstance(c, custody.FileCustody)
        r = pqc_signing.sign(b"token-ABC")
        self.assertEqual(r.public_key_hex, self.kp["public_key_hex"])
        self.assertTrue(pqc_signing.verify_both(b"token-ABC", r.signature_hex, r.public_key_hex))
        self.assertEqual(pqc_signing.trust_anchor_public_key_hex(), self.kp["public_key_hex"])
        self.assertEqual(pqc_signing.availability_report()["custody"]["driver"], "file")

    def test_malformed_file_fails_loud(self):
        bad = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False)
        bad.write('{"algorithm": "ML-DSA-65", "secret_key_hex": "zz"}'); bad.close()
        try:
            with self.assertRaises(custody.CustodyError):
                custody.FileCustody(bad.name)
            os.environ["POLARIS_PQC_SIGNING_KEY_FILE"] = bad.name
            custody.reset()
            with self.assertRaises(RuntimeError):
                pqc_signing.sign(b"x")   # never degrades to ephemeral
        finally:
            os.unlink(bad.name)

    def test_digest_length_is_enforced(self):
        c = custody.FileCustody(self.kf.name)
        with self.assertRaises(custody.CustodyError):
            c.sign(b"not-a-digest")

    def test_rotation_anchor_file_keeps_old_key_verifying(self):
        os.environ["POLARIS_PQC_SIGNING_KEY_FILE"] = self.kf.name
        os.environ["POLARIS_USE_REAL_PQC"] = "1"
        custody.reset()
        sig, alg, _pk = pqc_signing.signature_with_key_for_token("token-ABC")
        self.assertEqual(alg, "ML-DSA-65")
        self.assertTrue(pqc_signing.verify_token_signature("token-ABC", sig, alg))
        # Rotate: a NEW current key; the old signature must fail without an anchor
        # for the old key, and verify again once the old key is listed.
        newkp = pqc_signing.generate_keypair()
        nf = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False)
        json.dump(newkp, nf); nf.close()
        af = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False)
        json.dump({"anchors": [{"public_key_hex": self.kp["public_key_hex"], "label": "issuer-2026",
                                "retired": "2026-09-01"}]}, af); af.close()
        try:
            os.environ["POLARIS_PQC_SIGNING_KEY_FILE"] = nf.name
            custody.reset()
            self.assertFalse(pqc_signing.verify_token_signature("token-ABC", sig, alg))
            os.environ["POLARIS_PQC_TRUST_ANCHORS_FILE"] = af.name
            self.assertTrue(pqc_signing.verify_token_signature("token-ABC", sig, alg))
            self.assertEqual(pqc_signing.trust_anchor_public_keys()[0], newkp["public_key_hex"])
            os.environ["POLARIS_PQC_TRUST_ANCHORS_FILE"] = "/nonexistent/anchors.json"
            with self.assertRaises(RuntimeError):
                pqc_signing.trust_anchor_public_keys()
        finally:
            os.unlink(nf.name); os.unlink(af.name)


# ---------------------------------------------------------------------------
class _KmsStandIn:
    """A local AWS KMS (TrentService JSON 1.1) holding ONE ML-DSA-65 key, signing
    with OpenSSL's implementation. Faithful to the real wire shapes boto3 sends
    and expects; wrong-key-spec behaviour is configurable for the negative test."""

    def __init__(self, key_spec="ML_DSA_65", key_usage="SIGN_VERIFY", state="Enabled"):
        self.key_id = "1234abcd-12ab-34cd-56ef-1234567890ab"
        self.arn = f"arn:aws:kms:us-east-1:000000000000:key/{self.key_id}"
        self.key_spec, self.key_usage, self.state = key_spec, key_usage, state
        self.priv = _mldsa.MLDSA65PrivateKey.generate()
        self.pub_raw = self.priv.public_key().public_bytes_raw()
        self.spki = self.priv.public_key().public_bytes(_ser.Encoding.DER, _ser.PublicFormat.SubjectPublicKeyInfo)
        self.calls = []
        standin = self

        class H(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def do_POST(self):
                target = self.headers.get("X-Amz-Target", "")
                body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", "0"))) or b"{}")
                standin.calls.append((target, body))
                if body.get("KeyId") not in (standin.key_id, standin.arn):
                    return self._send(400, {"__type": "NotFoundException", "message": "Key not found"})
                if target.endswith("DescribeKey"):
                    out = {"KeyMetadata": {"KeyId": standin.key_id, "Arn": standin.arn, "KeySpec": standin.key_spec,
                                           "KeyUsage": standin.key_usage, "KeyState": standin.state,
                                           "SigningAlgorithms": ["ML_DSA_SHAKE_256"]}}
                elif target.endswith("GetPublicKey"):
                    out = {"KeyId": standin.arn, "KeySpec": standin.key_spec, "KeyUsage": standin.key_usage,
                           "PublicKey": base64.b64encode(standin.spki).decode(),
                           "SigningAlgorithms": ["ML_DSA_SHAKE_256"]}
                elif target.endswith("Sign"):
                    if body.get("SigningAlgorithm") != "ML_DSA_SHAKE_256" or body.get("MessageType") != "RAW":
                        return self._send(400, {"__type": "InvalidParameterException",
                                                "message": "algorithm/message type"})
                    msg = base64.b64decode(body["Message"])
                    sig = standin.priv.sign(msg)
                    out = {"KeyId": standin.arn, "Signature": base64.b64encode(sig).decode(),
                           "SigningAlgorithm": "ML_DSA_SHAKE_256"}
                else:
                    return self._send(400, {"__type": "UnknownOperationException", "message": target})
                self._send(200, out)

            def _send(self, code, obj):
                data = json.dumps(obj).encode()
                self.send_response(code)
                self.send_header("Content-Type", "application/x-amz-json-1.1")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

        self.server = HTTPServer(("127.0.0.1", 0), H)
        self.url = f"http://127.0.0.1:{self.server.server_port}"
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def close(self):
        self.server.shutdown()
        self.server.server_close()


def _boto3_present():
    try:
        import boto3  # noqa: F401
        return True
    except ImportError:
        return False


@unittest.skipUnless(_MLDSA_OK and _boto3_present(), "needs cryptography with ML-DSA and boto3")
class AwsKmsCustodyTests(unittest.TestCase):
    def setUp(self):
        self._env = _EnvSnapshot().__enter__()
        os.environ["AWS_ACCESS_KEY_ID"] = "AKIATESTONLY"
        os.environ["AWS_SECRET_ACCESS_KEY"] = "test-only-not-a-secret"
        self.kms = _KmsStandIn()

    def tearDown(self):
        self.kms.close()
        self._env.__exit__()

    def test_kms_driver_fetches_spki_and_signs_with_the_real_wire_protocol(self):
        c = custody.AwsKmsCustody(self.kms.key_id, region="us-east-1", endpoint_url=self.kms.url)
        self.assertEqual(c.public_key(), self.kms.pub_raw, "SPKI -> raw ML-DSA-65 public key")
        sig = c.sign(_DIGEST)
        self.assertEqual(len(sig), custody.SIGNATURE_LEN)
        self.assertTrue(_verify(sig, c.public_key()))
        self.assertFalse(_verify(sig, c.public_key(), b"token-XYZ"))
        targets = [t for t, _ in self.kms.calls]
        self.assertTrue(any(t.endswith("DescribeKey") for t in targets))
        self.assertTrue(any(t.endswith("GetPublicKey") for t in targets))
        sign_call = next(b for t, b in self.kms.calls if t.endswith("Sign"))
        self.assertEqual(sign_call["SigningAlgorithm"], "ML_DSA_SHAKE_256")
        self.assertEqual(sign_call["MessageType"], "RAW")
        self.assertEqual(base64.b64decode(sign_call["Message"]), _DIGEST)
        self.assertTrue(c.key_id.startswith("awskms:arn:aws:kms:"))

    def test_wrong_key_spec_is_refused_at_load(self):
        self.kms.key_spec = "RSA_2048"
        with self.assertRaises(custody.CustodyError):
            custody.AwsKmsCustody(self.kms.key_id, region="us-east-1", endpoint_url=self.kms.url)

    def test_disabled_key_is_refused_at_load(self):
        self.kms.state = "Disabled"
        with self.assertRaises(custody.CustodyError):
            custody.AwsKmsCustody(self.kms.key_id, region="us-east-1", endpoint_url=self.kms.url)

    def test_env_selects_kms_and_pqc_signing_routes_through_it(self):
        os.environ.update({"POLARIS_CUSTODY_DRIVER": "awskms", "POLARIS_CUSTODY_AWSKMS_KEY_ID": self.kms.key_id,
                           "POLARIS_CUSTODY_AWSKMS_REGION": "us-east-1",
                           "POLARIS_CUSTODY_AWSKMS_ENDPOINT_URL": self.kms.url})
        custody.reset()
        self.assertIsInstance(custody.get_custody(), custody.AwsKmsCustody)
        self.assertEqual(pqc_signing.trust_anchor_public_key_hex(), self.kms.pub_raw.hex())
        self.assertIsNone(pqc_signing._load_persistent_keypair(), "a KMS key has no exportable secret")
        rep = pqc_signing.availability_report()["custody"]
        self.assertEqual(rep["driver"], "awskms")
        if pqc_signing.is_available():
            os.environ["POLARIS_USE_REAL_PQC"] = "1"
            sig, alg, pkhex = pqc_signing.signature_with_key_for_token("token-ABC")
            self.assertEqual((alg, pkhex), ("ML-DSA-65", self.kms.pub_raw.hex()))
            self.assertTrue(pqc_signing.verify_token_signature("token-ABC", sig, alg))

    @unittest.skipUnless(os.environ.get("POLARIS_CUSTODY_AWSKMS_LIVE_KEY_ID"), "opt-in: needs a real KMS key")
    def test_live_aws_kms(self):
        self._env.__exit__()   # use the real ambient AWS credentials
        c = custody.AwsKmsCustody(os.environ["POLARIS_CUSTODY_AWSKMS_LIVE_KEY_ID"],
                                  region=os.environ.get("AWS_DEFAULT_REGION"))
        sig = c.sign(_DIGEST)
        self.assertTrue(_verify(sig, c.public_key()))


# ---------------------------------------------------------------------------
_P11 = os.environ.get("POLARIS_CUSTODY_PKCS11_MODULE")
_P11_REQUIRE = os.environ.get("POLARIS_CUSTODY_PKCS11_REQUIRE") == "1"


class Pkcs11CustodyTests(unittest.TestCase):
    """Against a real PKCS#11 token (CI: Kryoptic). Needs the module path, a
    token labelled POLARIS_CUSTODY_PKCS11_TOKEN_LABEL (default polaris) with the
    user PIN in POLARIS_CUSTODY_PKCS11_PIN_FILE."""

    def setUp(self):
        if not _P11:
            if _P11_REQUIRE:
                self.fail("POLARIS_CUSTODY_PKCS11_REQUIRE=1 but no POLARIS_CUSTODY_PKCS11_MODULE")
            self.skipTest("no PKCS#11 module configured")
        self.module = _P11
        self.token = os.environ.get("POLARIS_CUSTODY_PKCS11_TOKEN_LABEL", "polaris")
        with open(os.environ["POLARIS_CUSTODY_PKCS11_PIN_FILE"]) as fh:
            self.pin = fh.read().strip()
        # One key per TEST, not per process: the driver refuses a duplicate label
        # by design, and a per-process label made the second setUp trip it (found
        # by running the drill, v9.179).
        self.label = "polaris-test-%d-%s" % (os.getpid(), self._testMethodName)
        self.pk = custody.pkcs11_generate_key(self.module, self.token, self.pin, self.label)

    def test_key_is_generated_in_token_and_signatures_verify_by_both_witnesses(self):
        self.assertEqual(len(self.pk), custody.PUBLIC_KEY_LEN)
        c = custody.Pkcs11Custody(self.module, self.token, self.pin, self.label)
        self.assertEqual(c.public_key(), self.pk)
        sig = c.sign(_DIGEST)
        self.assertEqual(len(sig), custody.SIGNATURE_LEN)
        self.assertTrue(_verify(sig, self.pk))
        self.assertFalse(_verify(sig, self.pk, b"token-XYZ"))
        self.assertEqual(c.describe()["driver"], "pkcs11")

    def test_duplicate_label_is_refused(self):
        with self.assertRaises(custody.CustodyError):
            custody.pkcs11_generate_key(self.module, self.token, self.pin, self.label)

    def test_env_selects_pkcs11_and_pqc_signing_routes_through_it(self):
        pf = tempfile.NamedTemporaryFile("w", delete=False); pf.write(self.pin); pf.close()
        with _EnvSnapshot():
            os.environ.update({"POLARIS_CUSTODY_DRIVER": "pkcs11", "POLARIS_CUSTODY_PKCS11_MODULE": self.module,
                               "POLARIS_CUSTODY_PKCS11_TOKEN_LABEL": self.token,
                               "POLARIS_CUSTODY_PKCS11_PIN_FILE": pf.name,
                               "POLARIS_CUSTODY_PKCS11_KEY_LABEL": self.label})
            custody.reset()
            self.assertIsInstance(custody.get_custody(), custody.Pkcs11Custody)
            self.assertEqual(pqc_signing.trust_anchor_public_key_hex(), self.pk.hex())
            if pqc_signing.is_available():
                os.environ["POLARIS_USE_REAL_PQC"] = "1"
                sig, alg, pkhex = pqc_signing.signature_with_key_for_token("token-ABC")
                self.assertEqual((alg, pkhex), ("ML-DSA-65", self.pk.hex()))
                self.assertTrue(pqc_signing.verify_token_signature("token-ABC", sig, alg))
        os.unlink(pf.name)


# ---------------------------------------------------------------------------
class EnvSelectionTests(unittest.TestCase):
    def test_nothing_configured_means_no_custody(self):
        with _EnvSnapshot():
            self.assertIsNone(custody.get_custody())
            self.assertIsNone(pqc_signing.trust_anchor_public_key_hex())
            self.assertIsNone(pqc_signing.availability_report()["custody"])

    def test_unknown_driver_fails_loud(self):
        with _EnvSnapshot():
            os.environ["POLARIS_CUSTODY_DRIVER"] = "vault"
            with self.assertRaises(custody.CustodyError):
                custody.get_custody()

    def test_pin_in_env_is_refused(self):
        with _EnvSnapshot():
            os.environ.update({"POLARIS_CUSTODY_DRIVER": "pkcs11", "POLARIS_CUSTODY_PKCS11_MODULE": "/x.so",
                               "POLARIS_CUSTODY_PKCS11_PIN_FILE": "/x", "POLARIS_CUSTODY_PKCS11_PIN": "1234"})
            with self.assertRaises(custody.CustodyError) as cm:
                custody.get_custody()
            self.assertIn("PIN_FILE", str(cm.exception))

    def test_incomplete_driver_config_fails_loud(self):
        with _EnvSnapshot():
            os.environ["POLARIS_CUSTODY_DRIVER"] = "awskms"
            with self.assertRaises(custody.CustodyError):
                custody.get_custody()
            os.environ["POLARIS_CUSTODY_DRIVER"] = "pkcs11"
            with self.assertRaises(custody.CustodyError):
                custody.get_custody()

    def test_misconfigured_custody_is_reported_not_raised_in_the_availability_report(self):
        with _EnvSnapshot():
            os.environ["POLARIS_CUSTODY_DRIVER"] = "nope"
            self.assertIn("error", pqc_signing.availability_report()["custody"])


if __name__ == "__main__":
    unittest.main()
