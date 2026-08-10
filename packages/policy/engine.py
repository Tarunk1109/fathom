"""The Policy Engine — FATHOM §7.1, §9.1.

Everything routes through here. No executor calls a browser, phone or API directly. Every proposed
action is a structured object submitted to this gate, which returns ALLOW, DENY or ESCALATE plus
the rule that fired, and appends the decision to the hash-chained audit log.

**Deterministic. No LLM in the decision path.** Rules are pure functions of the action and the
session context, evaluated in a fixed order, first match wins. The same action in the same session
always produces the same verdict — which is the only reason the audit log means anything.

The three verdicts are not severity levels; they have different downstream behaviour:

- `ALLOW`     the executor may proceed. Attempt-consuming kinds draw down the route budget here.
- `DENY`      the action is refused. The executor records a terminal status and the route ends.
- `ESCALATE`  the action needs the operator. The route **stays open**, the request joins the human
              checkpoint queue, and nothing is refused. §9.1 names three triggers: identity lookup,
              consent attestation, coverage advice.

Confusing DENY with ESCALATE would either abandon a route that a human could have completed, or
carry on past a point where §2.2 requires a human.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from .actions import (
    ATTEMPT_CONSUMING_KINDS,
    PolicyDecision,
    ProposedAction,
    SessionContext,
)
from .audit import AuditLog, ChainVerification
from .rules import DEFAULT_RULES, NO_RULE_FIRED, Rule


@dataclass(frozen=True)
class CheckpointRequest:
    """An escalation waiting for the operator. The route it came from is not closed."""

    audit_index: int
    session_id: str
    route_id: str
    profile_id: str
    action_kind: str
    explanation: str
    raised_at: str


class PolicyEngine:
    def __init__(
        self,
        audit_log: AuditLog | None = None,
        rules: tuple[Rule, ...] = DEFAULT_RULES,
        audit_path: Path | str | None = None,
    ) -> None:
        if audit_log is not None and audit_path is not None:
            raise ValueError("pass either audit_log or audit_path, not both")
        self.audit = audit_log if audit_log is not None else AuditLog(audit_path)
        self.rules = rules
        self.checkpoint_queue: list[CheckpointRequest] = []

    # ----------------------------------------------------------------------------------

    def evaluate(self, action: ProposedAction, ctx: SessionContext) -> PolicyDecision:
        """Judge one proposed action. Every outcome is appended to the audit chain."""
        verdict, rule_id, explanation, terminal_status = self._first_matching_rule(action, ctx)

        entry = self.audit.append(
            session_id=action.session_id,
            route_id=action.route_id,
            profile_id=action.profile_id,
            action_kind=action.kind,
            target=action.target,
            payload=action.payload,
            rationale=action.rationale,
            verdict=verdict,
            rule_id=rule_id,
            explanation=explanation,
        )

        if verdict == "ALLOW" and action.kind in ATTEMPT_CONSUMING_KINDS:
            # The budget is drawn down by the gate, not by the executor. A budget the caller is
            # trusted to decrement is a budget that is not enforced (§9.4).
            ctx.budget_for(action.route_id).attempts_used += 1

        if verdict == "ESCALATE":
            self.checkpoint_queue.append(CheckpointRequest(
                audit_index=entry.index,
                session_id=action.session_id,
                route_id=action.route_id,
                profile_id=action.profile_id,
                action_kind=action.kind,
                explanation=explanation,
                raised_at=entry.timestamp,
            ))

        return PolicyDecision(
            verdict=verdict,
            rule_id=rule_id,
            explanation=explanation,
            audit_index=entry.index,
            terminal_status=terminal_status,
        )

    def _first_matching_rule(
        self, action: ProposedAction, ctx: SessionContext
    ) -> tuple[str, str, str, str | None]:
        for rule in self.rules:
            explanation = rule.fires(action, ctx)
            if explanation is not None:
                return rule.verdict, rule.rule_id, explanation, rule.terminal_status
        return "ALLOW", NO_RULE_FIRED, "No rule fired.", None

    # ----------------------------------------------------------------------------------

    def verify_chain(self) -> ChainVerification:
        return self.audit.verify_chain()

    def rule_ids(self) -> tuple[str, ...]:
        return tuple(rule.rule_id for rule in self.rules)

    def describe_rules(self) -> list[dict[str, str]]:
        """Exposed for `fathom-policy` (§7.2) so a judge can list the rules without reading code."""
        return [
            {
                "rule_id": rule.rule_id,
                "verdict": rule.verdict,
                "denies": rule.summary,
                "directive": rule.directive,
                "terminal_status": rule.terminal_status or "",
            }
            for rule in self.rules
        ]

    def pending_checkpoints(self) -> list[CheckpointRequest]:
        return list(self.checkpoint_queue)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")
