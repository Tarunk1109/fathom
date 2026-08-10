"""Audit chain tests — integrity, and the guarantee that no PII reaches the log.

Two separate promises are being tested.

**Integrity.** The chain detects any edit, reorder or removal. A judge is invited to verify it
live (§16), so a check that has never been shown to fail is not evidence of anything.

**No PII.** The log stores payload field *names* and a digest, never values; targets lose their
query strings; caller rationale is scrubbed. §2.1 forbids PII reaching the repo or logs, and an
append-only file is the worst possible place to discover a leak — there is no clean way to remove
it afterwards. The final test writes a deliberately PII-laden action and then runs the real PII
sweep over the resulting file.
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from packages.policy import (  # noqa: E402
    GENESIS_HASH,
    AuditLog,
    CallState,
    PolicyEngine,
    ProposedAction,
    SessionContext,
)
from packages.policy.audit import DEFAULT_AUDIT_PATH  # noqa: E402
from tools import pii_sweep  # noqa: E402


class AuditTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="fathom_audit_test_")
        self.addCleanup(self._tmp.cleanup)
        self.path = Path(self._tmp.name) / "audit.jsonl"
        self.engine = PolicyEngine(audit_path=self.path)

    def ctx(self) -> SessionContext:
        return SessionContext(session_id="ses_1", profile_id="profile_operator",
                              call=CallState(disclosure_delivered=True))

    def fill(self, km: int) -> ProposedAction:
        return ProposedAction(
            kind="fill", target="https://insurer.example.com/q",
            payload={"annual_km": str(km)}, route_id="rt_1",
            session_id="ses_1", profile_id="profile_operator",
            rationale="Fill the mileage field.",
        )

    def bind_attempt(self) -> ProposedAction:
        return ProposedAction(
            kind="click", target="https://insurer.example.com/q",
            payload={"label": "Buy now"}, route_id="rt_1",
            session_id="ses_1", profile_id="profile_operator",
            rationale="Complete the journey.",
        )

    def record(self, n: int = 3) -> None:
        ctx = self.ctx()
        for index in range(n):
            self.engine.evaluate(self.fill(12000 + index), ctx)

    def record_mixed(self) -> None:
        """allow, allow, DENY, allow — index 2 is a denial.

        The tamper tests edit index 2, so it must differ from what the tampering writes.
        A log of uniform ALLOWs lets an "edit" to ALLOW change nothing, and the test then
        passes without exercising anything.
        """
        ctx = self.ctx()
        self.engine.evaluate(self.fill(12000), ctx)
        self.engine.evaluate(self.fill(12001), ctx)
        self.engine.evaluate(self.bind_attempt(), ctx)
        self.engine.evaluate(self.fill(12002), ctx)
        assert self.engine.audit.entries[2].verdict == "DENY"


# ======================================================================================
# Chain construction
# ======================================================================================

class TestChainConstruction(AuditTestCase):
    def test_first_entry_links_to_genesis(self):
        self.record(1)
        self.assertEqual(self.engine.audit.entries[0].prev_hash, GENESIS_HASH)

    def test_each_entry_links_to_its_predecessor(self):
        self.record(4)
        entries = self.engine.audit.entries
        for previous, current in zip(entries, entries[1:]):
            self.assertEqual(current.prev_hash, previous.entry_hash)

    def test_an_intact_chain_verifies(self):
        self.record(5)
        result = self.engine.verify_chain()
        self.assertTrue(result.ok, result.describe())
        self.assertEqual(result.entries_checked, 5)

    def test_the_chain_survives_a_reload_from_disk(self):
        self.record(4)
        self.assertTrue(AuditLog(self.path).verify_chain().ok)

    def test_appending_continues_an_existing_chain(self):
        self.record(2)
        reopened = PolicyEngine(audit_log=AuditLog(self.path))
        reopened.evaluate(ProposedAction(
            kind="click", target="https://insurer.example.com/q",
            payload={"label": "Buy now"}, route_id="rt_1", session_id="ses_1",
            profile_id="profile_operator", rationale="",
        ), self.ctx())
        self.assertEqual(len(reopened.audit), 3)
        self.assertTrue(reopened.verify_chain().ok)


# ======================================================================================
# Tamper detection
# ======================================================================================

class TestTamperDetection(AuditTestCase):
    def rewrite(self, index: int, **changes) -> None:
        lines = self.path.read_text(encoding="utf-8").splitlines()
        record = json.loads(lines[index])
        record.update(changes)
        lines[index] = json.dumps(record, ensure_ascii=False, sort_keys=True)
        self.path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def test_editing_a_verdict_is_detected(self):
        self.record_mixed()
        self.rewrite(2, verdict="ALLOW", rule_id="P-ALLOW-00")
        result = AuditLog(self.path).verify_chain()
        self.assertFalse(result.ok)
        self.assertEqual(result.first_bad_index, 2)

    def test_editing_an_explanation_is_detected(self):
        self.record(3)
        self.rewrite(1, explanation="nothing to see here")
        self.assertFalse(AuditLog(self.path).verify_chain().ok)

    def test_removing_an_entry_is_detected(self):
        self.record(4)
        lines = self.path.read_text(encoding="utf-8").splitlines()
        del lines[1]
        self.path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        result = AuditLog(self.path).verify_chain()
        self.assertFalse(result.ok)
        self.assertEqual(result.first_bad_index, 1)

    def test_reordering_entries_is_detected(self):
        self.record(4)
        lines = self.path.read_text(encoding="utf-8").splitlines()
        lines[1], lines[2] = lines[2], lines[1]
        self.path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        self.assertFalse(AuditLog(self.path).verify_chain().ok)

    def test_recomputing_the_hash_after_an_edit_still_breaks_the_link(self):
        """The strongest case: an attacker who edits an entry *and* fixes its own hash still
        breaks every following prev_hash, which is the point of chaining."""
        self.record_mixed()
        lines = self.path.read_text(encoding="utf-8").splitlines()
        record = json.loads(lines[2])
        record["verdict"] = "ALLOW"
        from packages.policy.audit import AuditEntry
        resealed = AuditEntry.from_dict({**record, "entry_hash": ""})
        record["entry_hash"] = resealed.compute_hash()
        lines[2] = json.dumps(record, ensure_ascii=False, sort_keys=True)
        self.path.write_text("\n".join(lines) + "\n", encoding="utf-8")

        result = AuditLog(self.path).verify_chain()
        self.assertFalse(result.ok)
        self.assertEqual(result.first_bad_index, 3)


# ======================================================================================
# No PII in the log
# ======================================================================================

class TestNoPiiInAuditLog(AuditTestCase):
    #: Deliberately hostile payload. Every value here is synthetic.
    HOSTILE_PAYLOAD = {
        "licence_number": "A11112222233333",   # pii-sweep: allow DL_ONTARIO  synthetic
        "postal_code": "K1A 0B1",              # pii-sweep: allow PC_FULL_POSTAL  synthetic
        "vin": "1HGCM82633A004352",            # pii-sweep: allow VIN  synthetic
        "contact_phone": "416-555-0132",       # pii-sweep: allow PHONE_NANP  reserved fictional
        "contact_email": "someone@example.org",  # pii-sweep: allow EMAIL  reserved example domain
        "card_number": "4111111111111111",     # pii-sweep: allow PAYMENT_CARD  synthetic test number
        "home_address": "123 Fake Street",     # pii-sweep: allow STREET_ADDRESS  synthetic
    }

    def hostile_action(self) -> ProposedAction:
        return ProposedAction(
            kind="submit",
            target="https://insurer.example.com/apply?quoteRef=ABC123&applicant=redactme",
            payload=dict(self.HOSTILE_PAYLOAD),
            route_id="rt_1", session_id="ses_1", profile_id="profile_operator",
            rationale=(f"Submit for {self.HOSTILE_PAYLOAD['postal_code']} "
                       f"on {self.HOSTILE_PAYLOAD['contact_phone']}."),
        )

    def test_no_payload_value_reaches_the_log(self):
        self.engine.evaluate(self.hostile_action(), self.ctx())
        written = self.path.read_text(encoding="utf-8")
        for value in self.HOSTILE_PAYLOAD.values():
            with self.subTest(value=value[:2]):
                self.assertNotIn(value, written)

    def test_field_names_are_kept_because_structure_is_not_pii(self):
        self.engine.evaluate(self.hostile_action(), self.ctx())
        entry = self.engine.audit.entries[0]
        self.assertIn("licence_number", entry.payload_fields)
        self.assertEqual(len(entry.payload_digest), 64)

    def test_query_strings_are_stripped_from_targets(self):
        """Insurer journeys carry quote references and session tokens in the query string."""
        self.engine.evaluate(self.hostile_action(), self.ctx())
        target = self.engine.audit.entries[0].target_safe
        self.assertNotIn("?", target)
        self.assertNotIn("redactme", target)
        self.assertTrue(target.startswith("https://insurer.example.com/apply"))

    def test_caller_rationale_is_scrubbed(self):
        self.engine.evaluate(self.hostile_action(), self.ctx())
        rationale = self.engine.audit.entries[0].rationale_redacted
        self.assertIn("[REDACTED:", rationale)
        self.assertNotIn(self.HOSTILE_PAYLOAD["postal_code"], rationale)
        self.assertNotIn(self.HOSTILE_PAYLOAD["contact_phone"], rationale)

    def test_the_written_log_passes_the_real_pii_sweep(self):
        """The end-to-end promise: a hostile action produces a log file that passes CI."""
        self.engine.evaluate(self.hostile_action(), self.ctx())
        report = pii_sweep.sweep(self.path.parent)
        self.assertTrue(report.clean,
                        "audit log contains PII:\n"
                        + "\n".join(f.as_text() for f in report.findings))


# ======================================================================================
# The sweep covers the audit log's real location
# ======================================================================================

class TestAuditPathIsSwept(AuditTestCase):
    def test_default_audit_path_lives_inside_the_swept_tree(self):
        repo_root = Path(__file__).resolve().parent.parent
        self.assertTrue(DEFAULT_AUDIT_PATH.is_relative_to(repo_root))

    def test_no_ancestor_of_the_audit_path_is_excluded_from_the_sweep(self):
        repo_root = Path(__file__).resolve().parent.parent
        parts = DEFAULT_AUDIT_PATH.relative_to(repo_root).parts[:-1]
        for part in parts:
            with self.subTest(directory=part):
                self.assertNotIn(part, pii_sweep.EXCLUDED_DIRS)

    def test_the_audit_log_extension_is_swept_as_text(self):
        self.assertNotIn(DEFAULT_AUDIT_PATH.suffix.lower(), pii_sweep.BINARY_EXTENSIONS)


if __name__ == "__main__":
    unittest.main()
