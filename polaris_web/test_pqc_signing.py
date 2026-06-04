"""test_pqc_signing.py — unit tests for the post-quantum signing module.

`pqc_signing` is the single entry point `uc1_issue` calls to produce the bytes
stored in `TokenSignature.signature_bytes`. Its load-bearing safety property,
stated in the module docstring, is FAIL LOUD: with `POLARIS_USE_REAL_PQC=1` but
liboqs missing, issuance must raise rather than silently downgrade to the
deterministic placeholder. That path — and the placeholder's determinism and
its non-signature label — had no direct test (only the flag-unset DB integration
test in `test_app` and the static `check_pqc_signing_wired` wiring grep). This
file closes that gap. Pure module behavior; no DB, no liboqs required.

Run: python3 -m unittest test_pqc_signing
"""

import hashlib
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pqc_signing


class PlaceholderPathTests(unittest.TestCase):
    """Flag-off (the default, including CI): a deterministic SHA3-256 binding,
    explicitly labelled so it can never be mistaken for a real signature."""

    def setUp(self):
        self._saved = os.environ.pop('POLARIS_USE_REAL_PQC', None)

    def tearDown(self):
        if self._saved is not None:
            os.environ['POLARIS_USE_REAL_PQC'] = self._saved
        else:
            os.environ.pop('POLARIS_USE_REAL_PQC', None)

    def test_placeholder_is_sha3_256_of_token(self):
        token = 'TKN-CA-2026-000002'
        sig, label = pqc_signing.signature_bytes_for_token(token)
        self.assertEqual(sig, hashlib.sha3_256(token.encode('utf-8')).digest())
        self.assertEqual(label, pqc_signing.PLACEHOLDER_LABEL)

    def test_placeholder_is_deterministic(self):
        a, _ = pqc_signing.signature_bytes_for_token('repeatable-input')
        b, _ = pqc_signing.signature_bytes_for_token('repeatable-input')
        self.assertEqual(a, b)

    def test_distinct_tokens_get_distinct_placeholders(self):
        a, _ = pqc_signing.signature_bytes_for_token('token-A')
        b, _ = pqc_signing.signature_bytes_for_token('token-B')
        self.assertNotEqual(a, b)

    def test_label_marks_placeholder_as_non_signature(self):
        _, label = pqc_signing.signature_bytes_for_token('anything')
        self.assertIn('PLACEHOLDER', label)
        self.assertNotEqual(label, 'ML-DSA-65')

    def test_is_enabled_false_when_flag_unset(self):
        self.assertFalse(pqc_signing.is_enabled())


class FailLoudTests(unittest.TestCase):
    """Flag-on but liboqs unavailable: every entry point MUST raise rather than
    silently downgrade an operator who explicitly asked for real PQC."""

    def setUp(self):
        self._saved_flag = os.environ.get('POLARIS_USE_REAL_PQC')
        self._saved_avail = pqc_signing._OQS_AVAILABLE
        os.environ['POLARIS_USE_REAL_PQC'] = '1'
        pqc_signing._OQS_AVAILABLE = False  # simulate liboqs absent

    def tearDown(self):
        pqc_signing._OQS_AVAILABLE = self._saved_avail
        if self._saved_flag is not None:
            os.environ['POLARIS_USE_REAL_PQC'] = self._saved_flag
        else:
            os.environ.pop('POLARIS_USE_REAL_PQC', None)

    def test_signature_bytes_raises_not_downgrades(self):
        # The dangerous regression would be returning the placeholder digest.
        with self.assertRaises(pqc_signing.PQCUnavailableError):
            pqc_signing.signature_bytes_for_token('TKN-CA-2026-000002')

    def test_sign_raises_when_unavailable(self):
        with self.assertRaises(pqc_signing.PQCUnavailableError):
            pqc_signing.sign(b'message')

    def test_verify_raises_when_unavailable(self):
        with self.assertRaises(pqc_signing.PQCUnavailableError):
            pqc_signing.verify(b'message', 'aa', 'bb')

    def test_is_enabled_false_when_liboqs_missing(self):
        self.assertFalse(pqc_signing.is_enabled())


if __name__ == '__main__':
    unittest.main(verbosity=2)
