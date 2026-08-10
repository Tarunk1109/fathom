"""Engine-level tests — verdict semantics, precedence, budgets, determinism, coverage.

The rule-by-rule pairs live in `test_policy_rules.py`. This file tests the gate as a whole: that
the three verdicts behave differently downstream, that precedence is what the docstring claims,
that budgets are enforced by the gate rather than trusted to the caller, and that no rule is
registered without tests.
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from packages.policy import (  # noqa: E402
    DEFAULT_RULES,
    SPECIFIED_DENY_RULE_IDS,
    CallState,
    PolicyEngine,
    ProposedAction,
    RouteBudget,
    SessionContext,
)

PHONE = "tel:+15555550100"  # pii-sweep: allow PHONE_NANP  reserved fictional number


class EngineTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="fathom_engine_test_")
        self.addCleanup(self._tmp.cleanup)
        self.engine = PolicyEngine(audit_path=Path(self._tmp.name) / "audit.jsonl")

    def action(self, kind="fill", target="https://insurer.example.com/q", payload=None,
               *, route_id="rt_1", rationale="", profile_id="profile_operator"):
        return ProposedAction(kind=kind, target=target, payload=payload, route_id=route_id,
                              session_id="ses_1", profile_id=profile_id, rationale=rationale)

    def ctx(self, **overrides) -> SessionContext:
        defaults = dict(session_id="ses_1", profile_id="profile_operator",
                        hypothetical=False, sandbox_only=False,
                        call=CallState(disclosure_delivered=True))
        defaults.update(overrides)
        return SessionContext(**defaults)


# ======================================================================================
# ESCALATE is not DENY
# ======================================================================================

class TestEscalateIsNotDeny(EngineTestCase):
    """§9.1's three named triggers, and the behavioural difference.

    Confusing the two verdicts is costly in both directions: treating an escalation as a denial
    abandons a route a human could have finished, and treating a denial as an escalation carries
    on past a point §2.2 says requires a person.
    """

    ESCALATION_TRIGGERS = {
        "identity lookup": "The representative asked me to verify your identity before quoting.",
        "consent attestation": "The representative asked: do you consent to us obtaining that?",
        "coverage advice": "The representative asked what coverage you should choose.",
    }

    def test_each_named_trigger_escalates(self):
        for label, rationale in self.ESCALATION_TRIGGERS.items():
            with self.subTest(trigger=label):
                engine = PolicyEngine(audit_path=Path(self._tmp.name) / f"{len(label)}.jsonl")
                decision = engine.evaluate(
                    self.action(kind="speak", target=PHONE, rationale=rationale), self.ctx())
                self.assertEqual(decision.verdict, "ESCALATE", f"{label}: {decision.explanation}")
                self.assertEqual(decision.rule_id, "P-HUMAN-01")

    def test_escalation_queues_a_checkpoint_and_keeps_the_route_open(self):
        decision = self.engine.evaluate(
            self.action(kind="speak", target=PHONE,
                        rationale=self.ESCALATION_TRIGGERS["identity lookup"]),
            self.ctx())
        queue = self.engine.pending_checkpoints()
        self.assertEqual(len(queue), 1)
        self.assertEqual(queue[0].audit_index, decision.audit_index)
        self.assertEqual(queue[0].route_id, "rt_1")

    def test_denial_does_not_queue_a_checkpoint(self):
        """A denial ends the route. Nothing is waiting for the operator."""
        self.engine.evaluate(self.action(kind="click", payload={"label": "Buy now"}), self.ctx())
        self.assertEqual(self.engine.pending_checkpoints(), [])

    def test_a_denial_is_never_downgraded_to_an_escalation(self):
        """A bind control whose rationale also mentions consent is still a denial."""
        decision = self.engine.evaluate(
            self.action(kind="click", payload={"label": "Confirm purchase"},
                        rationale="The agent asked: do you consent to proceeding with purchase?"),
            self.ctx())
        self.assertEqual(decision.verdict, "DENY")
        self.assertEqual(decision.rule_id, "P-BIND-01")

    def test_terminal_status_is_carried_only_where_a_rule_declares_one(self):
        allowed = self.engine.evaluate(self.action(payload={"annual_km": "12000"}), self.ctx())
        self.assertIsNone(allowed.terminal_status)

        denied = self.engine.evaluate(self.action(payload={"plate_number": "ABCD123"}), self.ctx())
        self.assertEqual(denied.terminal_status, "blocked")


# ======================================================================================
# Budgets are enforced by the gate
# ======================================================================================

class TestBudgetEnforcement(EngineTestCase):
    def test_the_gate_draws_down_the_budget_itself(self):
        """§9.4 calls bounded attempts non-negotiable. A budget the caller is trusted to
        decrement is not a budget."""
        ctx = self.ctx(budgets={"rt_1": RouteBudget(max_attempts=2)})
        self.engine.evaluate(self.action(kind="navigate"), ctx)
        self.assertEqual(ctx.budget_for("rt_1").attempts_used, 1)
        self.engine.evaluate(self.action(kind="navigate"), ctx)
        self.assertEqual(ctx.budget_for("rt_1").attempts_used, 2)

        third = self.engine.evaluate(self.action(kind="navigate"), ctx)
        self.assertEqual(third.verdict, "DENY")
        self.assertEqual(third.rule_id, "P-BUDGET-01")

    def test_a_denied_action_does_not_consume_an_attempt(self):
        ctx = self.ctx(budgets={"rt_1": RouteBudget(max_attempts=2)})
        self.engine.evaluate(
            self.action(kind="submit", payload={"label": "Buy now"}), ctx)
        self.assertEqual(ctx.budget_for("rt_1").attempts_used, 0)

    def test_non_attempt_kinds_do_not_consume_budget(self):
        ctx = self.ctx(budgets={"rt_1": RouteBudget(max_attempts=1)})
        self.engine.evaluate(self.action(kind="fill", payload={"annual_km": "12000"}), ctx)
        self.assertEqual(ctx.budget_for("rt_1").attempts_used, 0)


# ======================================================================================
# Determinism
# ======================================================================================

class TestDeterminism(EngineTestCase):
    def test_the_same_action_always_produces_the_same_verdict(self):
        """No LLM in the decision path. If this ever fails, the audit log is worthless."""
        action = self.action(kind="click", payload={"label": "Buy now"})
        verdicts = {(d.verdict, d.rule_id) for d in
                    (self.engine.evaluate(action, self.ctx()) for _ in range(25))}
        self.assertEqual(verdicts, {("DENY", "P-BIND-01")})

    def test_every_decision_is_appended_to_the_audit_chain(self):
        ctx = self.ctx()
        for _ in range(5):
            self.engine.evaluate(self.action(payload={"annual_km": "12000"}), ctx)
        self.assertEqual(len(self.engine.audit), 5)
        self.assertTrue(self.engine.verify_chain().ok)

    def test_allowed_actions_are_logged_too_not_just_denials(self):
        """§9.1: every decision, allow or deny, appends to the hash-chained audit log."""
        self.engine.evaluate(self.action(payload={"annual_km": "12000"}), self.ctx())
        self.assertEqual(len(self.engine.audit), 1)
        self.assertEqual(self.engine.audit.entries[0].verdict, "ALLOW")


# ======================================================================================
# Rule registry coverage
# ======================================================================================

class TestRuleCoverage(EngineTestCase):
    def test_every_specified_rule_is_registered(self):
        registered = set(self.engine.rule_ids())
        missing = SPECIFIED_DENY_RULE_IDS - registered
        self.assertEqual(missing, set(), f"unregistered rules: {sorted(missing)}")

    def test_exactly_one_rule_escalates(self):
        escalating = [r.rule_id for r in DEFAULT_RULES if r.verdict == "ESCALATE"]
        self.assertEqual(escalating, ["P-HUMAN-01"])

    def test_all_other_rules_deny(self):
        self.assertTrue(all(r.verdict == "DENY" for r in DEFAULT_RULES
                            if r.rule_id != "P-HUMAN-01"))

    def test_every_registered_rule_has_a_denial_and_an_over_block_test(self):
        """Guards the invariant the operator set: two tests per rule, always.

        Reads the rule-tests module for a `Test...` class per rule and at least two test methods
        in it, so adding a rule without its pair fails here rather than in production.
        """
        import test_policy_rules as rule_tests

        source = Path(rule_tests.__file__).read_text(encoding="utf-8")
        for rule in DEFAULT_RULES:
            with self.subTest(rule=rule.rule_id):
                self.assertIn(rule.rule_id, source,
                              f"{rule.rule_id} is registered but has no test")

        case_counts = {
            name: len([m for m in vars(obj) if m.startswith("test_")])
            for name, obj in vars(rule_tests).items()
            if isinstance(obj, type) and name.startswith("Test") and name != "PolicyTestCase"
        }
        thin = {name: count for name, count in case_counts.items() if count < 2}
        self.assertEqual(thin, {}, f"rule test classes with fewer than two cases: {thin}")


if __name__ == "__main__":
    unittest.main()
