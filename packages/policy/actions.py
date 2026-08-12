"""Action, decision and session types for the Policy Engine.

`ProposedAction` and `PolicyDecision` are reproduced field-for-field from FATHOM §9.1.

Both are frozen. A proposal must not change between the moment it is judged and the moment it is
executed, or the audit log records a decision about something other than what happened — and the
audit log is the entire basis of the safety claim (§7.1).

The rules need state that §9.1 does not put on the action: the session fact-lock, the registered
licence value, whether the active profile is `sandbox_only`, route budgets, call consent, and
whether a stop has been requested. That lives in `SessionContext`, which the caller supplies. Keeping
it off `ProposedAction` preserves the specified shape and keeps the action a pure statement of
intent.

`SessionContext` is populated by the profile registry, vault and intake at Milestone 3. Until then
callers build it directly — the gate does not depend on those modules existing.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Literal
from urllib.parse import urlparse

ActionKind = Literal[
    "navigate", "fill", "click", "submit", "dial", "speak", "hangup", "record", "write", "fetch"
]
Verdict = Literal["ALLOW", "DENY", "ESCALATE"]

#: Kinds that consume a route attempt against the §9.4 budget.
#:
#: `submit` was here and was wrong (DL-13). §9.4's "1 attempt + 1 retry" budgets *attempts on a
#: route* — opening the journey again, calling again. A multi-step quote form takes six submits to
#: reach a price, and none of them is a retry. Counting them exhausted the budget mid-journey and
#: reported P-BUDGET-01 for what was ordinary progress. Retrying a *rejection* is still prohibited,
#: by P-STOP-01 and by the planner, not by the step counter.
ATTEMPT_CONSUMING_KINDS: frozenset[str] = frozenset({"navigate", "dial"})

#: Kinds that touch no destination — recording an outcome locally, or ending a call. These stay
#: available after a stop request so a terminal status can still be written (§2.2).
LOCAL_KINDS: frozenset[str] = frozenset({"write", "hangup"})

#: Kinds that put the profile in front of a real person. Denied outright for a hypothetical
#: profile (P-HYPO-HUMAN-01): the organizer Q&A permits a hypothetical on a web form, not on a
#: call with a licensed representative. `hangup` is excluded — ending a call is always permitted.
HUMAN_CONTACT_KINDS: frozenset[str] = frozenset({"dial", "speak", "record"})


# --------------------------------------------------------------------------------------
# §9.1 types, verbatim
# --------------------------------------------------------------------------------------


@dataclass(frozen=True)
class FieldValue:
    """A submitted value tagged with the profile it came from.

    Added after INC-001. A hypothetical profile was populated with a real third-party address
    partway through a hand-driven journey; nothing caught it because provenance did not exist as a
    concept, so there was nothing to compare. Every value the intake produces now carries the
    profile that produced it, and `P-PROFILE-BLEED-01` refuses any payload that resolves to more
    than one.

    Payload values may still be raw. Rules read values through `data_fields()`, which unwraps, so
    provenance is additive rather than a rewrite of every rule.
    """

    value: object
    source_profile_id: str

    def __str__(self) -> str:  # so a raw-string rule sees the value, not the wrapper
        return str(self.value)


def unwrap(value: object) -> object:
    return value.value if isinstance(value, FieldValue) else value


@dataclass(frozen=True)
class ProposedAction:
    kind: ActionKind
    target: str
    payload: dict | None
    route_id: str
    session_id: str
    profile_id: str
    rationale: str

    def payload_items(self) -> dict:
        return self.payload or {}

    def control_text(self) -> str:
        """Text identifying the control being acted on, lowercased.

        Deliberately narrow. Matching every payload value would make a rule fire on a value the
        operator typed into an unrelated field, which is how a gate starts over-blocking.
        """
        payload = self.payload_items()
        parts = [self.target]
        for key in ("label", "text", "selector", "name", "id", "aria_label", "button", "control"):
            value = payload.get(key)
            if isinstance(value, str):
                parts.append(value)
        return " ".join(parts).lower()

    def field_names(self) -> list[str]:
        """Payload keys, plus any explicitly named field. Values are never included."""
        payload = self.payload_items()
        names = [str(key).lower() for key in payload]
        for key in ("field", "name", "input"):
            value = payload.get(key)
            if isinstance(value, str):
                names.append(value.lower())
        return names

    CONTROL_KEYS = frozenset({
        "label", "text", "selector", "name", "id", "aria_label", "button", "control",
        "field", "input", "is_disclosure_prelude", "human_checkpoint", "control_type",
    })

    def data_fields(self) -> dict[str, object]:
        """Submitted data rather than control metadata, with any provenance wrapper removed."""
        return {k: unwrap(v) for k, v in self.payload_items().items()
                if str(k).lower() not in self.CONTROL_KEYS}

    def field_provenance(self) -> dict[str, str]:
        """Field name -> source profile, for values that declare one."""
        return {str(k): v.source_profile_id for k, v in self.payload_items().items()
                if isinstance(v, FieldValue) and str(k).lower() not in self.CONTROL_KEYS}

    def unprovenanced_fields(self) -> list[str]:
        return sorted(str(k) for k, v in self.payload_items().items()
                      if not isinstance(v, FieldValue) and str(k).lower() not in self.CONTROL_KEYS)


@dataclass(frozen=True)
class PolicyDecision:
    verdict: Verdict
    rule_id: str
    explanation: str
    audit_index: int

    #: Additive to the §9.1 shape: the terminal status the executor must record when this
    #: decision ends a route. §2.1 as amended requires P-HYPO-STEP-01 to emit `manual_handoff`
    #: and P-PLATE-01 to emit `blocked`, and a status carried in prose is a status that gets
    #: transcribed wrongly. The four specified fields are unchanged.
    terminal_status: str | None = None


# --------------------------------------------------------------------------------------
# Session state the rules read
# --------------------------------------------------------------------------------------


class RecordingConsent(str, Enum):
    """§11.7. The recorder is physically gated on GRANTED; the default is NO_AUDIO."""

    NO_AUDIO = "NO_AUDIO"
    GRANTED = "GRANTED"
    REFUSED = "REFUSED"


class HumanCheckpoint(str, Enum):
    """The §9.1 escalation triggers, plus the two §2.2 adds."""

    IDENTITY_VERIFICATION = "identity_verification"
    CONSENT_ATTESTATION = "consent_attestation"
    COVERAGE_ADVICE = "coverage_advice"
    DECLARATION_REQUIRED = "declaration_required"
    THIRD_PARTY_RECORDS_AUTHORIZATION = "third_party_records_authorization"


@dataclass
class CallState:
    disclosure_delivered: bool = False
    recording_consent: RecordingConsent = RecordingConsent.NO_AUDIO


@dataclass
class RouteBudget:
    """§9.4 bounded-attempt policy, described there as non-negotiable."""

    max_attempts: int = 2
    attempts_used: int = 0
    deadline: datetime | None = None

    def exhausted(self) -> bool:
        return self.attempts_used >= self.max_attempts

    def expired(self, now: datetime | None = None) -> bool:
        if self.deadline is None:
            return False
        return (now or datetime.now(timezone.utc)) > self.deadline


@dataclass
class SessionContext:
    session_id: str
    profile_id: str

    #: §4.1, amended 2026-08-09 (AC-001). **Two independent flags, no longer one concept.**
    #:
    #: `hypothetical` governs CONDUCT: no licence number (P-HYPO-LICENCE-01), no human contact
    #: (P-HYPO-HUMAN-01), no identity/consent/declaration/callback/purchase step (P-HYPO-STEP-01).
    #: A hypothetical profile may complete quote forms at real destinations — that is the primary
    #: profile, and the organizers explicitly permit it.
    #:
    #: `sandbox_only` governs REACH: whether the profile may touch a real destination at all
    #: (P-SANDBOX-01). Independent of `hypothetical`.
    hypothetical: bool = False
    sandbox_only: bool = False

    #: §9.2 fact-lock: material fact name -> hash of the locked value. Raw values never appear.
    fact_lock: dict[str, str] = field(default_factory=dict)

    #: Hash of the operator's registered licence number. The vault holds the value; the gate
    #: only ever sees a hash, so a licence number cannot leak through the policy layer.
    registered_licence_hash: str | None = None

    #: Identity field name -> hash, for the operator. Read by P-THIRDPARTY-01.
    operator_identity: dict[str, str] = field(default_factory=dict)

    #: Material fact name -> hash of the operator's **registered real** value, from the vault.
    #: Read by P-REAL-FACT-01. Distinct from `fact_lock`, which is the per-session consistency
    #: seal and applies to every profile: fact_lock asks "did this change between insurers?",
    #: registered_facts asks "is this the operator's actual information?".
    registered_facts: dict[str, str] = field(default_factory=dict)

    #: Hosts where the operator holds an account. Credential entry anywhere else is denied.
    registered_services: frozenset[str] = frozenset()

    budgets: dict[str, RouteBudget] = field(default_factory=dict)
    call: CallState = field(default_factory=CallState)
    stop_requested: bool = False

    #: Routes whose intended payload the operator has approved field-by-field (P-APPROVAL-01).
    #: **Empty by default — approval is opt-in, so a route runs only after a deliberate act.**
    #: One approval per route. Populated from `packages/policy/approvals.py`.
    approved_routes: frozenset[str] = frozenset()

    #: When True, a data field with no declared provenance is itself a denial (P-PROFILE-BLEED-01).
    #: Turned on for real destinations once intake tags every field, at Milestone 4.
    require_provenance: bool = False

    def budget_for(self, route_id: str) -> RouteBudget:
        return self.budgets.setdefault(route_id, RouteBudget())


# --------------------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------------------

_WHITESPACE = re.compile(r"\s+")

#: Hosts and suffixes treated as the local synthetic sandbox (§11.5).
SANDBOX_HOSTS: frozenset[str] = frozenset({"localhost", "127.0.0.1", "0.0.0.0", "::1", "[::1]"})
SANDBOX_HOST_SUFFIXES: tuple[str, ...] = (".localhost", ".local", ".sandbox", ".test", ".invalid")
SANDBOX_HOST_PREFIXES: tuple[str, ...] = ("sandbox-", "sandbox.")


def fact_hash(value: object) -> str:
    """Stable hash of a submitted value, for fact-lock and licence comparison.

    Normalised so trivial formatting differences are not read as fact drift: an insurer that
    uppercases a field must not look like the operator changing his answer.
    """
    normalised = _WHITESPACE.sub(" ", str(value).strip().lower())
    return hashlib.sha256(normalised.encode("utf-8")).hexdigest()


def is_sandbox_target(target: str) -> bool:
    """True when the target is the local synthetic sandbox rather than a real destination.

    Fails closed: anything unrecognised is treated as real, so P-SANDBOX-01 denies rather than
    permits when the target cannot be classified.
    """
    if not target:
        return False

    lowered = target.strip().lower()
    if lowered.startswith(("sandbox:", "file:")):
        return True
    if lowered.startswith("tel:") or lowered.startswith("sip:"):
        return False

    parsed = urlparse(lowered if "://" in lowered else f"//{lowered}")
    host = (parsed.hostname or "").strip()
    if not host:
        return False
    if host in SANDBOX_HOSTS:
        return True
    if host.startswith(SANDBOX_HOST_PREFIXES):
        return True
    return host.endswith(SANDBOX_HOST_SUFFIXES)


def target_host(target: str) -> str:
    parsed = urlparse(target if "://" in target else f"//{target}")
    return (parsed.hostname or "").lower()
