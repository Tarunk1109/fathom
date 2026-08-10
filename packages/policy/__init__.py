"""FATHOM Policy Engine (§7.1, §9.1).

The deterministic gate every action passes through. No LLM in the decision path.

    from packages.policy import PolicyEngine, ProposedAction, SessionContext

    engine = PolicyEngine()
    decision = engine.evaluate(action, ctx)
    if decision.verdict == "ALLOW":
        ...
"""

from .actions import (
    ATTEMPT_CONSUMING_KINDS,
    HUMAN_CONTACT_KINDS,
    LOCAL_KINDS,
    ActionKind,
    CallState,
    HumanCheckpoint,
    PolicyDecision,
    ProposedAction,
    RecordingConsent,
    RouteBudget,
    SessionContext,
    Verdict,
    fact_hash,
    is_sandbox_target,
)
from .audit import AuditEntry, AuditLog, ChainVerification, GENESIS_HASH, verify_entries
from .engine import CheckpointRequest, PolicyEngine
from .rules import DEFAULT_RULES, NO_RULE_FIRED, SPECIFIED_DENY_RULE_IDS, Rule

__all__ = [
    "ATTEMPT_CONSUMING_KINDS",
    "HUMAN_CONTACT_KINDS",
    "LOCAL_KINDS",
    "ActionKind",
    "AuditEntry",
    "AuditLog",
    "CallState",
    "ChainVerification",
    "CheckpointRequest",
    "DEFAULT_RULES",
    "GENESIS_HASH",
    "HumanCheckpoint",
    "NO_RULE_FIRED",
    "PolicyDecision",
    "PolicyEngine",
    "ProposedAction",
    "RecordingConsent",
    "RouteBudget",
    "Rule",
    "SPECIFIED_DENY_RULE_IDS",
    "SessionContext",
    "Verdict",
    "fact_hash",
    "is_sandbox_target",
    "verify_entries",
]
