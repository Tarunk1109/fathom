"""Rule-by-rule tests for the Policy Engine — FATHOM §9.1 as amended by D-002.

**Every rule gets two tests.**

A rule that fails to deny is a safety failure. A rule that denies a legitimate adjacent action is
also a failure — it stalls the run and it kills the live demonstration. So each rule is paired: one
case proving it denies what it must, one proving it permits the nearest legitimate neighbour.

The neighbours are not invented. Each is an action FATHOM genuinely needs to take:

- record that a CAPTCHA was encountered (that write *is* the terminal `blocked` evidence)
- fill payment_frequency and down_payment (§8.4 records both on every priced result)
- fill licence_class G1 (§9.6 records it; the PII sweep permits it)
- vary a coverage deductible (§10.2 requires elections to vary while facts stay locked)
- view a declarations page (a document, not a signature)
- run a hypothetical profile against a real quote form (AC-001 permits exactly this)

Over-block tests assert `ALLOW` rather than "not this rule", so a neighbour caught by some *other*
rule fails too. Cross-rule over-blocking is the failure mode that is hardest to see coming.
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from packages.policy import (  # noqa: E402
    CallState,
    FieldValue,
    PolicyEngine,
    ProposedAction,
    RecordingConsent,
    RouteBudget,
    SessionContext,
    fact_hash,
)

REAL = "https://insurer.example.com/quote/step2"
SANDBOX = "http://localhost:8801/quote/step2"

#: Reserved fictional range (555-01xx). Declared once so the sweep needs one pragma, not nine —
#: a narrow allowance in a single place, per the rule in docs/SAFETY.md.
PHONE = "tel:+15555550100"  # pii-sweep: allow PHONE_NANP  reserved fictional number


class PolicyTestCase(unittest.TestCase):
    """Shared fixture. A fresh engine and a scratch audit log per test."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="fathom_policy_test_")
        self.addCleanup(self._tmp.cleanup)
        self.engine = PolicyEngine(audit_path=Path(self._tmp.name) / "audit.jsonl")

    # -- builders -----------------------------------------------------------------------

    def action(self, kind="fill", target=REAL, payload=None, *, profile_id="profile_operator",
               route_id="rt_1", rationale="") -> ProposedAction:
        return ProposedAction(
            kind=kind, target=target, payload=payload, route_id=route_id,
            session_id="ses_test", profile_id=profile_id, rationale=rationale,
        )

    def operator_ctx(self, **overrides) -> SessionContext:
        defaults = dict(
            session_id="ses_test", profile_id="profile_operator",
            hypothetical=False, sandbox_only=False,
            # P-APPROVAL-01 denies by default; these fixtures exercise other rules, so the
            # route under test is pre-approved. TestApprovalRule covers the gate itself.
            approved_routes=frozenset({"rt_1"}),
        )
        defaults.update(overrides)
        return SessionContext(**defaults)

    def hypo_ctx(self, **overrides) -> SessionContext:
        defaults = dict(
            session_id="ses_test", profile_id="profile_hypo_clean",
            hypothetical=True, sandbox_only=False,
            approved_routes=frozenset({"rt_1"}),
        )
        defaults.update(overrides)
        return SessionContext(**defaults)

    # -- assertions ---------------------------------------------------------------------

    def assertDenied(self, action, ctx, rule_id, *, terminal_status=None):
        decision = self.engine.evaluate(action, ctx)
        self.assertEqual(decision.verdict, "DENY",
                         f"expected DENY, got {decision.verdict} from {decision.rule_id}")
        self.assertEqual(decision.rule_id, rule_id,
                         f"expected {rule_id}, got {decision.rule_id}: {decision.explanation}")
        if terminal_status is not None:
            self.assertEqual(decision.terminal_status, terminal_status)
        return decision

    def assertAllowed(self, action, ctx):
        """Assert ALLOW outright — a neighbour caught by any other rule is still over-blocking."""
        decision = self.engine.evaluate(action, ctx)
        self.assertEqual(decision.verdict, "ALLOW",
                         f"over-blocked by {decision.rule_id}: {decision.explanation}")
        return decision


# ======================================================================================
# P-STOP-01
# ======================================================================================

class TestStopRule(PolicyTestCase):
    def test_denies_action_after_stop_request(self):
        ctx = self.operator_ctx(stop_requested=True)
        self.assertDenied(self.action(kind="speak", payload={"text": "one more question"}),
                          ctx, "P-STOP-01")

    def test_permits_recording_the_outcome_after_stop(self):
        """§2.2 requires a terminal status for every route. A stop with no evidence it happened
        would be worse than not stopping."""
        ctx = self.operator_ctx(stop_requested=True)
        self.assertAllowed(self.action(kind="write", target="out/results.jsonl",
                                       payload={"status": "manual_handoff"}), ctx)
        self.assertAllowed(self.action(kind="hangup", target=PHONE), ctx)


# ======================================================================================
# P-SANDBOX-01  — reach, not conduct
# ======================================================================================

class TestSandboxRule(PolicyTestCase):
    def test_denies_sandbox_only_profile_reaching_a_real_destination(self):
        ctx = self.operator_ctx(profile_id="profile_sim_g2", hypothetical=True, sandbox_only=True)
        self.assertDenied(self.action(kind="navigate", target=REAL, profile_id="profile_sim_g2"),
                          ctx, "P-SANDBOX-01")

    def test_permits_hypothetical_profile_on_a_real_quote_form(self):
        """The amendment's whole point: hypothetical is not sandbox_only. AC-001 permits this."""
        ctx = self.hypo_ctx()
        self.assertAllowed(
            self.action(kind="navigate", target=REAL, profile_id="profile_hypo_clean"), ctx)

    def test_permits_sandbox_only_profile_on_the_sandbox(self):
        ctx = self.operator_ctx(profile_id="profile_sim_g2", hypothetical=True, sandbox_only=True)
        self.assertAllowed(
            self.action(kind="navigate", target=SANDBOX, profile_id="profile_sim_g2"), ctx)


# ======================================================================================
# P-HYPO-LICENCE-01
# ======================================================================================

class TestHypotheticalLicenceRule(PolicyTestCase):
    def test_denies_a_licence_number_under_a_hypothetical_profile(self):
        self.assertDenied(
            self.action(payload={"licence_number": "A11112222233333"},  # pii-sweep: allow DL_ONTARIO  synthetic
                        profile_id="profile_hypo_clean"),
            self.hypo_ctx(), "P-HYPO-LICENCE-01")

    def test_permits_licence_class_under_a_hypothetical_profile(self):
        """A clean-record hypothetical still has a licence *class*. Only the number is banned."""
        self.assertAllowed(
            self.action(payload={"licence_class": "G", "licence_years": "10"},
                        profile_id="profile_hypo_clean"),
            self.hypo_ctx())


# ======================================================================================
# P-HYPO-HUMAN-01
# ======================================================================================

class TestHypotheticalHumanRule(PolicyTestCase):
    def test_denies_a_call_under_a_hypothetical_profile(self):
        self.assertDenied(
            self.action(kind="dial", target=PHONE, profile_id="profile_hypo_clean"),
            self.hypo_ctx(), "P-HYPO-HUMAN-01")

    def test_permits_a_call_under_the_real_operator_profile(self):
        """The operator profile carries full voice permissions — that is where broker calls run."""
        ctx = self.operator_ctx()
        self.assertAllowed(self.action(kind="dial", target=PHONE), ctx)


# ======================================================================================
# P-HYPO-STEP-01
# ======================================================================================

class TestHypotheticalStepRule(PolicyTestCase):
    def test_denies_a_purchase_step_and_emits_manual_handoff(self):
        self.assertDenied(
            self.action(kind="click", target="https://insurer.example.com/flow",
                        payload={"label": "Purchase this policy"},
                        profile_id="profile_hypo_clean"),
            self.hypo_ctx(), "P-HYPO-STEP-01", terminal_status="manual_handoff")

    def test_denies_callback_enrolment_under_a_hypothetical_profile(self):
        self.assertDenied(
            self.action(kind="click", target="https://insurer.example.com/flow",
                        payload={"label": "Request a callback from an advisor"},
                        profile_id="profile_hypo_clean"),
            self.hypo_ctx(), "P-HYPO-STEP-01", terminal_status="manual_handoff")

    def test_permits_completing_an_ordinary_quote_form(self):
        """Everything up to a price is a form, and AC-001 asks for as many of them as possible."""
        self.assertAllowed(
            self.action(kind="fill", target="https://insurer.example.com/quote/driver",
                        payload={"annual_km": "12000", "primary_use": "commute"},
                        profile_id="profile_hypo_clean"),
            self.hypo_ctx())

    def test_permits_recording_our_own_consent_receipt(self):
        self.assertAllowed(
            self.action(kind="fill", target="https://insurer.example.com/quote/driver",
                        payload={"consent_receipt": "cr_0004"},
                        profile_id="profile_hypo_clean"),
            self.hypo_ctx())


# ======================================================================================
# P-THIRDPARTY-01
# ======================================================================================

class TestThirdPartyRule(PolicyTestCase):
    def test_denies_an_additional_driver_field(self):
        self.assertDenied(
            self.action(payload={"additional_driver_first_name": "Someone"}),
            self.operator_ctx(), "P-THIRDPARTY-01")

    def test_permits_the_operators_own_identity_field(self):
        ctx = self.operator_ctx(operator_identity={"first_name": fact_hash("Tarun")})
        self.assertAllowed(self.action(payload={"first_name": "Tarun"}), ctx)


# ======================================================================================
# P-LICENCE-01
# ======================================================================================

class TestLicenceRule(PolicyTestCase):
    def test_denies_a_licence_number_that_is_not_the_registered_one(self):
        ctx = self.operator_ctx(registered_licence_hash=fact_hash("REGISTERED-VALUE"))
        self.assertDenied(self.action(payload={"licence_number": "SOMETHING-ELSE"}),
                          ctx, "P-LICENCE-01")

    def test_permits_licence_class_which_is_not_a_licence_number(self):
        """§9.6 records the class and the PII sweep permits it, so the gate must too."""
        ctx = self.operator_ctx(registered_licence_hash=fact_hash("REGISTERED-VALUE"))
        self.assertAllowed(self.action(payload={"licence_class": "G1"}), ctx)


# ======================================================================================
# P-REAL-FACT-01
# ======================================================================================

class TestRealFactRule(PolicyTestCase):
    def test_denies_a_fabricated_fact_under_a_non_hypothetical_profile(self):
        ctx = self.operator_ctx(registered_facts={"licence_class": fact_hash("G1")})
        self.assertDenied(self.action(payload={"licence_class": "G"}), ctx, "P-REAL-FACT-01")

    def test_permits_the_same_fabrication_under_a_hypothetical_profile(self):
        """The mirror of P-HYPO-LICENCE-01: invented facts are the point of a hypothetical."""
        ctx = self.hypo_ctx(registered_facts={"licence_class": fact_hash("G1")})
        self.assertAllowed(
            self.action(payload={"licence_class": "G"}, profile_id="profile_hypo_clean"), ctx)


# ======================================================================================
# P-FACT-01  — applies to every profile
# ======================================================================================

class TestFactLockRule(PolicyTestCase):
    def test_denies_fact_drift_under_a_hypothetical_profile_too(self):
        """Fact-lock is what makes results comparable across insurers. Drift under the clean
        profile would invalidate the comparison and every parity claim resting on it."""
        ctx = self.hypo_ctx(fact_lock={"annual_km": fact_hash("12000")})
        self.assertDenied(
            self.action(payload={"annual_km": "5000"}, profile_id="profile_hypo_clean"),
            ctx, "P-FACT-01")

    def test_permits_varying_a_coverage_election(self):
        """§10.2's boundary: coverage choices vary freely, facts never do."""
        ctx = self.operator_ctx(fact_lock={"annual_km": fact_hash("12000")})
        self.assertAllowed(
            self.action(payload={"collision_deductible": "500", "annual_km": "12000"}), ctx)


# ======================================================================================
# P-PLATE-01
# ======================================================================================

class TestPlateRule(PolicyTestCase):
    def test_denies_a_licence_plate_field_and_emits_blocked(self):
        self.assertDenied(self.action(payload={"licence_plate_number": "ABCD123"}),
                          self.operator_ctx(), "P-PLATE-01", terminal_status="blocked")

    def test_permits_other_vehicle_fields(self):
        """AC-001 item 3 is about the plate specifically, not about vehicle identification."""
        self.assertAllowed(
            self.action(payload={"vehicle_make": "Honda", "vehicle_model": "Civic",
                                 "vehicle_year": "2019"}),
            self.operator_ctx())


# ======================================================================================
# P-PAY-01
# ======================================================================================

class TestPaymentRule(PolicyTestCase):
    def test_denies_a_card_number_field(self):
        self.assertDenied(
            self.action(payload={"card_number": "4111111111111111"}),  # pii-sweep: allow PAYMENT_CARD  synthetic
            self.operator_ctx(), "P-PAY-01")

    def test_denies_a_card_number_hidden_in_an_innocuous_field(self):
        self.assertDenied(
            self.action(payload={"reference": "4111111111111111"}),  # pii-sweep: allow PAYMENT_CARD  synthetic
            self.operator_ctx(), "P-PAY-01")

    def test_permits_quote_payment_terms(self):
        """§8.4 records all four of these on every priced result."""
        self.assertAllowed(
            self.action(payload={"payment_frequency": "monthly", "down_payment": "0",
                                 "instalment_count": "12", "finance_charges": "0"}),
            self.operator_ctx())


# ======================================================================================
# P-SIGN-01
# ======================================================================================

class TestSignatureRule(PolicyTestCase):
    def test_denies_a_declaration_control(self):
        self.assertDenied(
            self.action(kind="click", payload={"label": "I declare the information is true"}),
            self.operator_ctx(), "P-SIGN-01")

    def test_permits_viewing_a_declarations_page(self):
        """A declarations page is a document to read, not a signature to give."""
        self.assertAllowed(
            self.action(kind="click", payload={"label": "View declarations page"}),
            self.operator_ctx())


# ======================================================================================
# P-BIND-01
# ======================================================================================

class TestBindRule(PolicyTestCase):
    def test_denies_a_buy_control(self):
        self.assertDenied(self.action(kind="click", payload={"label": "Buy now"}),
                          self.operator_ctx(), "P-BIND-01")

    def test_permits_getting_a_quote(self):
        self.assertAllowed(self.action(kind="click", payload={"label": "Get my quote"}),
                           self.operator_ctx())

    def test_permits_an_informational_page_containing_a_bind_verb(self):
        self.assertAllowed(
            self.action(kind="click", target="https://insurer.example.com/guides",
                        payload={"label": "How to buy car insurance"}),
            self.operator_ctx())


# ======================================================================================
# P-CAPTCHA-01
# ======================================================================================

class TestCaptchaRule(PolicyTestCase):
    def test_denies_interacting_with_a_bot_check(self):
        self.assertDenied(self.action(kind="click", payload={"label": "I'm not a robot"}),
                          self.operator_ctx(), "P-CAPTCHA-01")

    def test_permits_recording_that_a_captcha_was_encountered(self):
        """That write *is* the terminal `blocked` evidence and the Friction Ledger entry (§10.7).
        Blocking it would destroy the record the refusal is supposed to produce."""
        self.assertAllowed(
            self.action(kind="write", target="out/friction.jsonl",
                        payload={"note": "reCAPTCHA encountered at step 3", "status": "blocked"}),
            self.operator_ctx())


# ======================================================================================
# P-AUTH-01
# ======================================================================================

class TestAuthRule(PolicyTestCase):
    def test_denies_credentials_to_an_unregistered_service(self):
        self.assertDenied(self.action(payload={"password": "hunter2"}),
                          self.operator_ctx(), "P-AUTH-01")

    def test_permits_credentials_to_a_registered_service(self):
        ctx = self.operator_ctx(registered_services=frozenset({"insurer.example.com"}))
        self.assertAllowed(self.action(payload={"password": "hunter2"}), ctx)

    def test_permits_a_contact_email_which_is_not_a_credential(self):
        self.assertAllowed(self.action(payload={"contact_email": "someone@example.org"}),  # pii-sweep: allow EMAIL  synthetic
                           self.operator_ctx())


# ======================================================================================
# P-RECORD-01
# ======================================================================================

class TestRecordRule(PolicyTestCase):
    def test_denies_recording_without_consent(self):
        ctx = self.operator_ctx(call=CallState(disclosure_delivered=True))
        self.assertDenied(self.action(kind="record", target=PHONE),
                          ctx, "P-RECORD-01")

    def test_permits_recording_once_consent_is_granted(self):
        ctx = self.operator_ctx(call=CallState(disclosure_delivered=True,
                                               recording_consent=RecordingConsent.GRANTED))
        self.assertAllowed(self.action(kind="record", target=PHONE), ctx)


# ======================================================================================
# P-DISCLOSE-01
# ======================================================================================

class TestDisclosureRule(PolicyTestCase):
    def test_denies_speaking_before_the_disclosure_prelude(self):
        self.assertDenied(
            self.action(kind="speak", target=PHONE,
                        payload={"text": "I'd like a quote please"}),
            self.operator_ctx(), "P-DISCLOSE-01")

    def test_permits_the_disclosure_prelude_itself(self):
        """The prelude is itself a `speak`. If it could not go first, no call could ever start."""
        self.assertAllowed(
            self.action(kind="speak", target=PHONE,
                        payload={"text": "I am an automated assistant calling for...",
                                 "is_disclosure_prelude": True}),
            self.operator_ctx())

    def test_permits_speaking_after_disclosure(self):
        ctx = self.operator_ctx(call=CallState(disclosure_delivered=True))
        self.assertAllowed(
            self.action(kind="speak", target=PHONE, payload={"text": "Thank you"}),
            ctx)


# ======================================================================================
# P-BUDGET-01
# ======================================================================================

class TestBudgetRule(PolicyTestCase):
    def test_denies_an_attempt_past_the_route_budget(self):
        ctx = self.operator_ctx(budgets={"rt_1": RouteBudget(max_attempts=1, attempts_used=1)})
        self.assertDenied(self.action(kind="navigate", target=REAL), ctx, "P-BUDGET-01")

    def test_permits_an_attempt_within_budget(self):
        ctx = self.operator_ctx(budgets={"rt_1": RouteBudget(max_attempts=2, attempts_used=1)})
        self.assertAllowed(self.action(kind="navigate", target=REAL), ctx)


# ======================================================================================
# P-HUMAN-01  — the ESCALATE path
# ======================================================================================

class TestHumanCheckpointRule(PolicyTestCase):
    def test_escalates_an_identity_verification_request(self):
        ctx = self.operator_ctx(call=CallState(disclosure_delivered=True))
        decision = self.engine.evaluate(
            self.action(kind="speak", target=PHONE,
                        rationale="The representative asked me to verify your identity."),
            ctx)
        self.assertEqual(decision.verdict, "ESCALATE")
        self.assertEqual(decision.rule_id, "P-HUMAN-01")

    def test_does_not_escalate_ordinary_record_keeping(self):
        ctx = self.operator_ctx(call=CallState(disclosure_delivered=True))
        self.assertAllowed(
            self.action(kind="write", target="out/results.jsonl",
                        payload={"consent_receipt_id": "cr_0004"},
                        rationale="Record the consent receipt id for this route."),
            ctx)


# ======================================================================================
# P-APPROVAL-01  — added after INC-001
# ======================================================================================

class TestApprovalRule(PolicyTestCase):
    def test_denies_a_real_destination_on_an_unapproved_route(self):
        """Default deny. A route runs only after a deliberate act, never by omission."""
        ctx = self.operator_ctx(approved_routes=frozenset())
        self.assertDenied(self.action(kind="navigate", target=REAL), ctx, "P-APPROVAL-01")

    def test_permits_a_real_destination_once_the_route_is_approved(self):
        ctx = self.operator_ctx(approved_routes=frozenset({"rt_1"}))
        self.assertAllowed(self.action(kind="navigate", target=REAL), ctx)

    def test_permits_the_sandbox_without_any_approval(self):
        """Approval guards real destinations. Requiring it for the sandbox would push development
        toward live sites, which is the §18 anti-goal."""
        ctx = self.operator_ctx(approved_routes=frozenset())
        self.assertAllowed(self.action(kind="navigate", target=SANDBOX), ctx)

    def test_permits_recording_an_outcome_without_approval(self):
        ctx = self.operator_ctx(approved_routes=frozenset())
        self.assertAllowed(self.action(kind="write", target="out/results.jsonl",
                                       payload={"status": "blocked"}), ctx)


# ======================================================================================
# P-PROFILE-BLEED-01  — added after INC-001
# ======================================================================================

class TestProfileBleedRule(PolicyTestCase):
    def test_denies_a_field_sourced_from_another_profile(self):
        """INC-001 itself: a real-world address dropped into a hypothetical journey."""
        decision = self.assertDenied(
            self.action(payload={"address": FieldValue("a real address",
                                                       "profile_operator")},
                        profile_id="profile_hypo_clean"),
            self.hypo_ctx(), "P-PROFILE-BLEED-01")
        self.assertIn("address", decision.explanation)
        self.assertIn("profile_operator", decision.explanation)
        self.assertIn("profile_hypo_clean", decision.explanation)

    def test_denies_a_payload_mixing_two_profiles(self):
        self.assertDenied(
            self.action(payload={
                "first_name": FieldValue("Synthetic", "profile_sim_g2"),
                "last_name": FieldValue("Also synthetic", "profile_hypo_clean"),
            }, profile_id="profile_hypo_clean"),
            self.hypo_ctx(), "P-PROFILE-BLEED-01")

    def test_permits_a_payload_entirely_from_the_running_profile(self):
        self.assertAllowed(
            self.action(payload={
                "first_name": FieldValue("Synthetic", "profile_hypo_clean"),
                "annual_km": FieldValue("12000", "profile_hypo_clean"),
            }, profile_id="profile_hypo_clean"),
            self.hypo_ctx())

    def test_permits_untagged_fields_while_provenance_is_being_rolled_out(self):
        """Provenance is populated by intake at Milestone 3. Denying every untagged payload today
        would stop the system rather than protect it — see the PARTIAL row in PRIME_DIRECTIVES."""
        self.assertAllowed(self.action(payload={"annual_km": "12000"}), self.operator_ctx())

    def test_denies_untagged_fields_once_the_session_requires_provenance(self):
        ctx = self.operator_ctx(require_provenance=True)
        self.assertDenied(self.action(payload={"annual_km": "12000"}), ctx,
                          "P-PROFILE-BLEED-01")


# ======================================================================================
# P-HYPO-ATTEST-01  — added after INC-001
# ======================================================================================

class TestHypotheticalAttestationRule(PolicyTestCase):
    def test_denies_an_accuracy_acknowledgement_and_emits_manual_handoff(self):
        """The exact control INC-001 ticked."""
        self.assertDenied(
            self.action(kind="click", target="https://insurer.example.com/vehicles",
                        payload={"label": "I confirm the address information is accurate",
                                 "control_type": "checkbox"},
                        profile_id="profile_hypo_clean"),
            self.hypo_ctx(), "P-HYPO-ATTEST-01", terminal_status="manual_handoff")

    def test_denies_a_fraud_acknowledgement(self):
        self.assertDenied(
            self.action(kind="click", target="https://insurer.example.com/vehicles",
                        payload={"label": "I understand that insurance fraud is a criminal offence",
                                 "control_type": "checkbox"},
                        profile_id="profile_hypo_clean"),
            self.hypo_ctx(), "P-HYPO-ATTEST-01", terminal_status="manual_handoff")

    def test_permits_marketing_copy_containing_the_word_accurate(self):
        """A bare adjective is not an attestation. Requiring attestational phrasing keeps the
        rule from firing on half the page."""
        self.assertAllowed(
            self.action(kind="click", target="https://insurer.example.com/start",
                        payload={"label": "Get accurate quotes in 3 minutes"},
                        profile_id="profile_hypo_clean"),
            self.hypo_ctx())

    def test_permits_the_operator_confirming_their_own_real_information(self):
        """Under profile_operator the information genuinely is accurate, so confirming it is
        honest. The rule is about a hypothetical attesting, not about attestation as such."""
        self.assertAllowed(
            self.action(kind="click", target="https://insurer.example.com/vehicles",
                        payload={"label": "I confirm the address information is accurate",
                                 "control_type": "checkbox"}),
            self.operator_ctx())


if __name__ == "__main__":
    unittest.main()
