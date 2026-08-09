"""Tests for the PII sweep (FATHOM §0.5: every module gets a test).

Uses stdlib `unittest` only — §13 puts pytest in the stack, but that decision belongs to the
milestone that uses it. These tests are pytest-compatible when it arrives.

Every fixture below is synthetic and every fixture line carries an inline allow-pragma, which
both keeps the sweep green on its own test suite and exercises the pragma mechanism.

    python3 -m unittest discover -s tests -v      # or:  make test
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

import pii_sweep  # noqa: E402


def rule_ids(line: str) -> set[str]:
    return {f.rule_id for f in pii_sweep.scan_line("fixture", 1, line)}


class TestDriverLicence(unittest.TestCase):
    def test_hyphenated_ontario_format_is_caught(self):
        line = "licence: A12345678901234"  # pii-sweep: allow DL_ONTARIO  synthetic fixture
        self.assertIn("DL_ONTARIO", rule_ids(line))

    def test_spaced_and_hyphenated_variants_are_caught(self):
        line = "K1234-56789-01234"  # pii-sweep: allow DL_ONTARIO  synthetic fixture
        self.assertIn("DL_ONTARIO", rule_ids(line))

    def test_licence_class_alone_is_not_a_licence_number(self):
        self.assertNotIn("DL_ONTARIO", rule_ids("licence_class: G1, no owned vehicle"))


class TestPostalCode(unittest.TestCase):
    def test_full_postal_code_is_caught(self):
        line = "postal: K1A 0B1"  # pii-sweep: allow PC_FULL_POSTAL  synthetic fixture
        self.assertIn("PC_FULL_POSTAL", rule_ids(line))

    def test_fsa_only_is_permitted(self):
        """§9.6 and the Day 0 redaction rules record the FSA, so it must not trip."""
        self.assertNotIn("PC_FULL_POSTAL", rule_ids("forward sortation area: M5V"))


class TestVin(unittest.TestCase):
    def test_vin_is_caught(self):
        line = "vin 1HGCM82633A004352"  # pii-sweep: allow VIN  synthetic fixture
        self.assertIn("VIN", rule_ids(line))

    def test_lowercase_hex_hash_is_not_a_vin(self):
        line = "artifact_cid: cid:sha256-3f9a2b7c1d4e5f60718293a4b5c6d7e8"
        self.assertNotIn("VIN", rule_ids(line))

    def test_all_letter_token_is_not_a_vin(self):
        self.assertNotIn("VIN", rule_ids("BENCHMARKCOVERAGE"))


class TestPhone(unittest.TestCase):
    def test_phone_is_caught(self):
        line = "call 416-555-0132"  # pii-sweep: allow PHONE_NANP  synthetic fixture
        self.assertIn("PHONE_NANP", rule_ids(line))

    def test_iso_timestamp_is_not_a_phone_number(self):
        self.assertNotIn("PHONE_NANP", rule_ids("last_verified_at: 2026-08-09T14:22:05-04:00"))

    def test_invalid_area_code_is_rejected(self):
        self.assertNotIn("PHONE_NANP", rule_ids("range 012-345-6789"))

    def test_repeated_digits_are_rejected(self):
        self.assertNotIn("PHONE_NANP", rule_ids("placeholder 000-000-0000"))


class TestEmail(unittest.TestCase):
    def test_email_is_caught(self):
        line = "reply to broker@example.com"  # pii-sweep: allow EMAIL  synthetic fixture
        self.assertIn("EMAIL", rule_ids(line))

    def test_redaction_token_is_clean(self):
        self.assertNotIn("EMAIL", rule_ids("contact: [REDACTED_CONTACT]"))


class TestPaymentCard(unittest.TestCase):
    def test_luhn_valid_number_is_caught(self):
        line = "card 4111111111111111"  # pii-sweep: allow PAYMENT_CARD  synthetic test number
        self.assertIn("PAYMENT_CARD", rule_ids(line))

    def test_luhn_invalid_digit_run_is_ignored(self):
        self.assertNotIn("PAYMENT_CARD", rule_ids("sequence 1234567890123456"))


class TestStreetAddress(unittest.TestCase):
    def test_street_address_is_caught(self):
        line = "123 Fake Street"  # pii-sweep: allow STREET_ADDRESS  synthetic fixture
        self.assertIn("STREET_ADDRESS", rule_ids(line))

    def test_prose_is_not_an_address(self):
        self.assertNotIn("STREET_ADDRESS", rule_ids("The operator resides in Ontario."))


class TestDateOfBirth(unittest.TestCase):
    def test_labelled_dob_is_caught(self):
        line = "DOB: 1999-01-31"  # pii-sweep: allow DOB_LABELLED  synthetic fixture
        self.assertIn("DOB_LABELLED", rule_ids(line))

    def test_birth_year_alone_is_permitted(self):
        """The Day 0 redaction rules record birth year only, so it must not trip."""
        self.assertNotIn("DOB_LABELLED", rule_ids("birth_year: 1999"))


class TestAllowPragma(unittest.TestCase):
    def test_bare_pragma_allows_every_rule(self):
        self.assertEqual(rule_ids("broker@example.com  # pii-sweep: allow"), set())

    def test_scoped_pragma_allows_only_its_rule(self):
        # Built by concatenation so the source line itself does not carry a literal address.
        line = "K1A 0B1 and broker@" + "example.com  # pii-sweep: allow PC_FULL_POSTAL"
        found = rule_ids(line)
        self.assertNotIn("PC_FULL_POSTAL", found)
        self.assertIn("EMAIL", found)

    def test_pragma_accepts_a_rule_list(self):
        """A line can legitimately trip two rules; narrowing beats weakening a rule."""
        line = "K1A 0B1 and broker@" + "example.com  # pii-sweep: allow PC_FULL_POSTAL,EMAIL"
        self.assertEqual(rule_ids(line), set())

    def test_pragma_does_not_swallow_a_trailing_reason(self):
        line = "K1A 0B1  # pii-sweep: allow PC_FULL_POSTAL  documented synthetic fixture"
        self.assertEqual(rule_ids(line), set())


class TestMasking(unittest.TestCase):
    def test_mask_never_reveals_the_value(self):
        """The sweep must not leak PII into CI logs — that is the failure it prevents."""
        secret = "A12345678901234"  # pii-sweep: allow DL_ONTARIO  synthetic fixture
        masked = pii_sweep.mask(secret)
        self.assertNotIn(secret, masked)
        self.assertNotIn(secret[2:], masked)
        self.assertTrue(masked.startswith(secret[:2]))

    def test_findings_report_masked_values_only(self):
        line = "licence: A12345678901234"  # pii-sweep: allow DL_ONTARIO  synthetic fixture
        for finding in pii_sweep.scan_line("fixture", 1, line):
            self.assertNotIn("12345678901234", finding.as_text())


class TestScanSurface(unittest.TestCase):
    def test_binary_extensions_are_flagged_not_skipped(self):
        """§15.1 requires screenshots to be reviewed; silence would imply false coverage."""
        self.assertIn(".png", pii_sweep.BINARY_EXTENSIONS)
        self.assertIn(".wav", pii_sweep.BINARY_EXTENSIONS)

    def test_git_directory_is_excluded(self):
        self.assertIn(".git", pii_sweep.EXCLUDED_DIRS)

    def test_out_and_docs_are_not_excluded(self):
        """The operator's requirement: the sweep covers the repo, out/ and docs/."""
        self.assertNotIn("out", pii_sweep.EXCLUDED_DIRS)
        self.assertNotIn("docs", pii_sweep.EXCLUDED_DIRS)


class TestRepositoryIsClean(unittest.TestCase):
    def test_live_repository_passes_its_own_sweep(self):
        root = Path(__file__).resolve().parent.parent
        report = pii_sweep.sweep(root)
        self.assertTrue(
            report.clean,
            "repository contains PII-shaped content:\n"
            + "\n".join(f.as_text() for f in report.findings),
        )


if __name__ == "__main__":
    unittest.main()
