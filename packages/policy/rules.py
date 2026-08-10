"""The Policy Engine rule set — FATHOM §9.1.

Eighteen rules returning `DENY`, plus `P-HUMAN-01` returning `ESCALATE`.

The thirteen specified in §9.1, plus five added 2026-08-09 by amendment D-002 following the
organizer Q&A (AC-001): `P-HYPO-LICENCE-01`, `P-HYPO-HUMAN-01`, `P-HYPO-STEP-01`,
`P-REAL-FACT-01` and `P-PLATE-01`. `P-SANDBOX-01` survives with narrowed semantics — it reads
`sandbox_only` alone and no longer says anything about hypothetical profiles.

`P-HUMAN-01` is documented as an extension in the same way `COMPUTED` is documented in §8.1: §9.1
states that ESCALATE routes to the human checkpoint queue but names no rule that produces it, and
without one the verdict is unreachable. See OQ-006.

The hypothetical rules, in one line each
----------------------------------------
AC-001 permits a hypothetical driver profile on quote forms and recommends a clean record to
maximise returned rates. It does not permit a hypothetical to carry a licence number, to speak to a
real person, or to make a commitment. Those three prohibitions are `P-HYPO-LICENCE-01`,
`P-HYPO-HUMAN-01` and `P-HYPO-STEP-01`, and they hold at every destination.

`P-REAL-FACT-01` is the mirror: a non-hypothetical profile may not carry an invented fact. Between
them, the two profiles cannot bleed into each other.

**Deterministic. No LLM anywhere in the decision path.** Every rule is a pure function of the
proposed action and the session context. Same inputs, same verdict, every time — which is what
makes the audit log worth anything.

Two failure modes, not one
--------------------------
A rule that fails to deny is a safety failure. A rule that denies a legitimate adjacent action is
also a failure: it stalls the run, and an over-blocking gate kills the live demonstration. Every
rule below is paired in `tests/test_policy_rules.py` with a case proving it denies what it must and
a case proving it permits the nearest legitimate neighbour. The neighbours are not hypothetical —
each one is an action FATHOM genuinely needs to take.

Precedence
----------
Rules are evaluated in the order registered and the first to fire wins, so its `rule_id` is what
the audit log and the UI show. The order is deliberate:

1. `P-STOP-01` — a stop request outranks everything.
2. `P-SANDBOX-01` — a sandbox-only profile must never reach a real destination, whatever it is doing.
3. Profile conduct — `P-HYPO-LICENCE-01`, `P-HYPO-HUMAN-01`, `P-HYPO-STEP-01`. Placed above the
   general rules so a hypothetical profile's denial is reported as a *profile* boundary rather than
   as the generic rule that would also have caught it. `P-HYPO-STEP-01` firing on a purchase
   control instead of `P-BIND-01` is the useful outcome: it carries `manual_handoff`.
4. Identity and fact integrity — `P-THIRDPARTY-01`, `P-LICENCE-01`, `P-REAL-FACT-01`, `P-FACT-01`.
5. `P-PLATE-01` — before the commitment rules, so a plate field is reported as a plate.
6. Commitment — `P-PAY-01`, `P-SIGN-01`, `P-BIND-01`.
7. Access controls — `P-CAPTCHA-01`, `P-AUTH-01`.
8. Call state — `P-RECORD-01`, `P-DISCLOSE-01`.
9. `P-BUDGET-01` last among the denials, so a substantive violation is reported as itself rather
   than as "out of budget".
10. `P-HUMAN-01` last overall: a denial is never downgraded to an escalation.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable, Iterable, Pattern

from .actions import (
    ATTEMPT_CONSUMING_KINDS,
    HUMAN_CONTACT_KINDS,
    LOCAL_KINDS,
    HumanCheckpoint,
    ProposedAction,
    RecordingConsent,
    SessionContext,
    Verdict,
    fact_hash,
    is_sandbox_target,
    target_host,
)


@dataclass(frozen=True)
class Rule:
    rule_id: str
    verdict: Verdict
    directive: str
    summary: str
    evaluate: Callable[[ProposedAction, SessionContext], str | None]

    #: Terminal status the executor records when this rule ends a route (§8.1).
    terminal_status: str | None = None

    def fires(self, action: ProposedAction, ctx: SessionContext) -> str | None:
        """Return an explanation when the rule fires, otherwise None."""
        return self.evaluate(action, ctx)


def _compile(patterns: Iterable[str]) -> tuple[Pattern[str], ...]:
    return tuple(re.compile(p, re.IGNORECASE) for p in patterns)


def _any_match(patterns: tuple[Pattern[str], ...], text: str) -> str | None:
    for pattern in patterns:
        match = pattern.search(text)
        if match:
            return match.group(0)
    return None


# --------------------------------------------------------------------------------------
# P-STOP-01
# --------------------------------------------------------------------------------------

def _stop(action: ProposedAction, ctx: SessionContext) -> str | None:
    if not ctx.stop_requested:
        return None
    if action.kind in LOCAL_KINDS:
        # Ending the call and recording the outcome must survive a stop request. §2.2 requires a
        # terminal status with evidence for every rate source attempted, and a stop request that
        # could not itself be recorded would be a stop request with no evidence it happened.
        return None
    return (
        f"A stop request is active for this session; '{action.kind}' would continue the "
        f"interaction. Only ending the call and recording the outcome remain permitted."
    )


# --------------------------------------------------------------------------------------
# P-SANDBOX-01
# --------------------------------------------------------------------------------------

def _sandbox(action: ProposedAction, ctx: SessionContext) -> str | None:
    """Reach, not conduct. Amended 2026-08-09 (AC-001): reads `sandbox_only` alone.

    This rule no longer says anything about hypothetical profiles. A hypothetical profile with
    `sandbox_only: False` reaches real destinations freely — that is the primary profile.
    """
    if not ctx.sandbox_only:
        return None
    if action.kind in LOCAL_KINDS:
        return None
    if is_sandbox_target(action.target):
        return None
    return (
        f"Profile '{action.profile_id}' is sandbox_only and this target is not the local "
        f"synthetic sandbox. §2.3: a sandbox-only profile may never touch a real destination."
    )


# --------------------------------------------------------------------------------------
# P-HYPO-LICENCE-01
# --------------------------------------------------------------------------------------

def _hypothetical_licence(action: ProposedAction, ctx: SessionContext) -> str | None:
    """No licence number under a hypothetical profile. Non-negotiable.

    The brief bans a fabricated licence number and AC-001 did not address it, so the organizer
    permission to use a hypothetical driver profile does not reach this. There is no vault value
    to check against either — a hypothetical person has no licence, so any value would be invented.
    """
    if not ctx.hypothetical:
        return None
    if action.kind not in {"fill", "submit", "speak"}:
        return None

    for key in action.data_fields():
        name = str(key).lower()
        if _any_match(LICENCE_ATTRIBUTE_PATTERNS, name):
            continue
        if _any_match(LICENCE_NUMBER_PATTERNS, name):
            return (
                f"Field '{name}' submits a driver's licence number under hypothetical profile "
                f"'{action.profile_id}'. Any value would be fabricated. §2.1: never fabricate, "
                f"borrow or alter a licence number — this holds regardless of profile."
            )
    return None


# --------------------------------------------------------------------------------------
# P-HYPO-HUMAN-01
# --------------------------------------------------------------------------------------

def _hypothetical_human(action: ProposedAction, ctx: SessionContext) -> str | None:
    """No real person is spoken to on behalf of someone who does not exist.

    AC-001 permits a hypothetical driver profile on quote forms. It says nothing about voice, and
    misrepresenting a fabricated applicant to a licensed representative is a different act from
    filling a web form. The operator profile carries full voice permissions; this one carries none.
    """
    if not ctx.hypothetical:
        return None
    if action.kind not in HUMAN_CONTACT_KINDS:
        return None
    return (
        f"'{action.kind}' would put hypothetical profile '{action.profile_id}' in front of a real "
        f"person. §2.1: human contact under a hypothetical profile is prohibited. Run this route "
        f"under the operator profile, or record it as unreachable by this channel."
    )


# --------------------------------------------------------------------------------------
# P-HYPO-STEP-01
# --------------------------------------------------------------------------------------

HYPO_BLOCKED_STEP_PATTERNS = _compile([
    # identity verification
    r"\bverify[\s_-]+(?:your[\s_-]+)?identity\b", r"\bidentity[\s_-]+verification\b",
    r"\bconfirm[\s_-]+your[\s_-]+identity\b", r"\bsecurity[\s_-]+question\b",
    r"\bupload[\s_-]+(?:your[\s_-]+)?(?:id|licence|license)\b",
    # consent attestation and declarations
    r"\bconsent\b", r"\bi[\s_-]+(?:declare|certify|attest|agree[\s_-]+that)\b",
    r"\bdeclaration\b", r"\battestation\b", r"\bauthoriz\w*[\s_-]+(?:us[\s_-]+)?to\b",
    # callback enrolment
    r"\brequest[\s_-]+(?:a[\s_-]+)?call(?:back)?\b", r"\bhave[\s_-]+(?:an[\s_-]+)?(?:agent|broker|advisor)[\s_-]+call\b",
    r"\bcall[\s_-]+me\b", r"\bspeak[\s_-]+(?:to|with)[\s_-]+(?:an[\s_-]+)?(?:agent|broker|advisor)\b",
    r"\bbook[\s_-]+(?:a[\s_-]+)?(?:call|appointment)\b",
    # purchase
    r"\b(?:buy|purchase|bind|checkout|check[\s_-]out)\b",
])

#: A declarations page is a document; consent *receipts* are our own record-keeping.
HYPO_STEP_EXCLUSIONS = _compile([
    r"\bdeclarations?[\s_-]+page\b", r"\bconsent[\s_-]+receipt\b",
])


def _hypothetical_step(action: ProposedAction, ctx: SessionContext) -> str | None:
    """Stop the hypothetical at the point a journey stops being a quote form.

    Everything up to a price is a form. Identity, consent, declaration, callback enrolment and
    purchase are commitments made by a person, and there is no person here. Emits
    `manual_handoff` so the route ends with a recorded status rather than an error.
    """
    if not ctx.hypothetical:
        return None
    if action.kind not in {"fill", "submit", "click"}:
        return None

    text = action.control_text() + " " + " ".join(action.field_names())
    if _any_match(HYPO_STEP_EXCLUSIONS, text):
        return None
    hit = _any_match(HYPO_BLOCKED_STEP_PATTERNS, text)
    if hit:
        return (
            f"'{hit}' is an identity, consent, declaration, callback-enrolment or purchase step, "
            f"and profile '{action.profile_id}' is hypothetical. Record manual_handoff and stop. "
            f"AC-001 permits a hypothetical driver on quote forms, not past them."
        )
    return None


# --------------------------------------------------------------------------------------
# P-REAL-FACT-01
# --------------------------------------------------------------------------------------

def _real_fact(action: ProposedAction, ctx: SessionContext) -> str | None:
    """The mirror of P-HYPO-LICENCE-01: a real profile may not carry an invented fact.

    P-FACT-01 keeps facts *consistent* across insurers for every profile. This rule keeps them
    *true* for a non-hypothetical one, by binding every material fact to the vault's registered
    value. Together the two stop the profiles bleeding into each other.
    """
    if ctx.hypothetical:
        return None
    if action.kind not in {"fill", "submit"}:
        return None
    if not ctx.registered_facts:
        return None

    for key, value in action.data_fields().items():
        name = str(key).lower()
        registered = ctx.registered_facts.get(name)
        if registered is None:
            continue
        if fact_hash(value) != registered:
            return (
                f"Field '{name}' submits a value that does not match the operator's registered "
                f"information under non-hypothetical profile '{action.profile_id}'. §2.2: use the "
                f"operator's own real, accurate information for any live interaction."
            )
    return None


# --------------------------------------------------------------------------------------
# P-PLATE-01
# --------------------------------------------------------------------------------------

PLATE_FIELD_PATTERNS = _compile([
    r"\b(?:licen[cs]e|licence|number)?[\s_-]*plate[\s_-]*(?:number|no|num|#)?\b",
    r"\bregistration[\s_-]*(?:number|no|plate)\b",
    r"\bveh(?:icle)?[\s_-]*plate\b",
])

#: A plate *frame*, a plate-recognition feature name, or a template placeholder is not a plate.
PLATE_EXCLUSIONS = _compile([
    r"\bplate[\s_-]*(?:frame|holder|cover)\b", r"\bboiler[\s_-]?plate\b", r"\btemplate\b",
])


def _plate(action: ProposedAction, ctx: SessionContext) -> str | None:
    """AC-001 item 3: plate is not usually mandatory. Skip it; if it is mandatory, record blocked.

    Denying the fill *is* the skip. When the journey will not proceed without it, the executor
    receives this denial and records `blocked` naming the exact field, which is what §2.1 as
    amended requires.
    """
    if action.kind not in {"fill", "submit"}:
        return None

    for key in action.data_fields():
        name = str(key).lower()
        if _any_match(PLATE_EXCLUSIONS, name):
            continue
        if _any_match(PLATE_FIELD_PATTERNS, name):
            return (
                f"Field '{name}' is a licence plate. §2.1: skip optional plate fields. If this "
                f"field is mandatory, record blocked naming '{name}' exactly, and stop the route."
            )
    return None


# --------------------------------------------------------------------------------------
# P-THIRDPARTY-01
# --------------------------------------------------------------------------------------

THIRD_PARTY_FIELD_PATTERNS = _compile([
    r"\b(?:additional|second|secondary|other|occasional|listed)[\s_-]*driver",
    r"\bco[\s_-]?applicant",
    r"\bspouse\b",
    r"\bthird[\s_-]?party\b",
    r"\bnamed[\s_-]?insured[\s_-]?[2-9]\b",
    r"\bdriver[\s_-]?[2-9]\b",
])

IDENTITY_FIELDS = ("first_name", "last_name", "full_name", "middle_name",
                   "date_of_birth", "dob", "sin", "social_insurance_number")


def _third_party(action: ProposedAction, ctx: SessionContext) -> str | None:
    if action.kind not in {"fill", "submit"}:
        return None

    for name in action.field_names():
        hit = _any_match(THIRD_PARTY_FIELD_PATTERNS, name)
        if hit:
            return (
                f"Field '{name}' collects data about a person other than the operator. "
                f"§2.1: intake refuses third-party personal data entirely in this build."
            )

    for key, value in action.data_fields().items():
        canonical = str(key).lower().strip()
        if canonical not in IDENTITY_FIELDS:
            continue
        expected = ctx.operator_identity.get(canonical)
        if expected is None:
            continue
        if fact_hash(value) != expected:
            return (
                f"Identity field '{canonical}' does not match the operator's registered value. "
                f"It therefore describes another person, and consent has not been obtained."
            )
    return None


# --------------------------------------------------------------------------------------
# P-LICENCE-01
# --------------------------------------------------------------------------------------

LICENCE_NUMBER_PATTERNS = _compile([
    r"\blic[ec]n[cs]e[\s_-]*(?:number|no|num|#)\b",
    r"\bdl[\s_-]*(?:number|no|num|#)\b",
    r"\bdriver'?s?[\s_-]*lic[ec]n[cs]e\b",
    r"^lic[ec]n[cs]e$",
])

#: Licence *attributes* are not the licence number. §9.6 records these and the PII sweep permits
#: them, so the gate must too — a rule that blocks the redacted form pushes work outside the gate.
LICENCE_ATTRIBUTE_PATTERNS = _compile([
    r"\bclass\b", r"\bprovince\b", r"\bstate\b", r"\bcountry\b",
    r"\bissue[sd]?\b", r"\bexpir", r"\byears?\b", r"\bstatus\b", r"\btype\b", r"\bsince\b",
])


def _licence(action: ProposedAction, ctx: SessionContext) -> str | None:
    if action.kind not in {"fill", "submit"}:
        return None

    for key, value in action.data_fields().items():
        name = str(key).lower()
        if _any_match(LICENCE_ATTRIBUTE_PATTERNS, name):
            continue
        if not _any_match(LICENCE_NUMBER_PATTERNS, name):
            continue
        if ctx.registered_licence_hash is None:
            return (
                f"Field '{name}' submits a licence number but no operator licence value is "
                f"registered in the vault, so it cannot be verified as the operator's own."
            )
        if fact_hash(value) != ctx.registered_licence_hash:
            return (
                f"Field '{name}' submits a licence number that does not match the operator's "
                f"registered value. §2.1: never fabricate, borrow or alter a licence number."
            )
    return None


# --------------------------------------------------------------------------------------
# P-FACT-01
# --------------------------------------------------------------------------------------

def _fact_drift(action: ProposedAction, ctx: SessionContext) -> str | None:
    if action.kind not in {"fill", "submit"}:
        return None
    if not ctx.fact_lock:
        return None

    for key, value in action.data_fields().items():
        name = str(key).lower()
        locked = ctx.fact_lock.get(name)
        # A field absent from the fact-lock is not a material fact. Coverage elections —
        # deductibles, optional benefits, limits, endorsements — are choices, and §10.2 requires
        # them to vary freely while facts stay immutable. That boundary is this line.
        if locked is None:
            continue
        if fact_hash(value) != locked:
            return (
                f"Field '{name}' diverges from the session fact-lock. §2.1: material facts are "
                f"hashed at session start and may not change across insurers."
            )
    return None


# --------------------------------------------------------------------------------------
# P-PAY-01
# --------------------------------------------------------------------------------------

PAYMENT_FIELD_PATTERNS = _compile([
    r"\b(?:credit|debit)[\s_-]*card\b",
    r"\bcard[\s_-]*(?:number|no|num|holder)\b",
    r"\bcc[\s_-]?(?:num|number)\b",
    r"\bcvv\b", r"\bcvc\b", r"\bcsc\b", r"\bsecurity[\s_-]*code\b",
    r"\bexpiry[\s_-]*(?:date|month|year)?\b", r"\bexp[\s_-]*(?:month|year|date)\b",
    r"\bbilling[\s_-]*(?:address|postal|zip)\b",
    r"\biban\b", r"\brouting[\s_-]*number\b", r"\btransit[\s_-]*number\b",
    r"\binstitution[\s_-]*number\b", r"\bbank[\s_-]*account\b", r"\baccount[\s_-]*number\b",
    r"\bvoid[\s_-]*cheque\b", r"\bpre[\s_-]?authorized[\s_-]*debit\b",
])

#: §8.4 records monthly_amount, down_payment, instalment_count and finance_charges on every priced
#: result. Those are quote terms, not payment instruments, and must remain writable.
PAYMENT_EXCLUSION_PATTERNS = _compile([
    r"\bpayment[\s_-]*(?:frequency|plan|schedule|option|method[\s_-]*preference|type)\b",
    r"\bmonthly[\s_-]*(?:amount|payment|premium)\b",
    r"\bdown[\s_-]*payment\b",
    r"\binstal?ment[\s_-]*count\b",
    r"\bfinance[\s_-]*charges?\b",
    r"\btotal[\s_-]*estimated[\s_-]*cost\b",
    r"\bannual[\s_-]*premium\b",
])

PAY_CONTROL_PATTERNS = _compile([
    r"\bpay[\s_-]*now\b", r"\bproceed[\s_-]*to[\s_-]*payment\b", r"\benter[\s_-]*card\b",
])


def _luhn_valid(value: str) -> bool:
    """Catch a card number submitted through an innocuously named field."""
    digits = [int(c) for c in value if c.isdigit()]
    if not 13 <= len(digits) <= 19:
        return False
    checksum, parity = 0, len(digits) % 2
    for index, digit in enumerate(digits):
        if index % 2 == parity:
            digit *= 2
            if digit > 9:
                digit -= 9
        checksum += digit
    return checksum % 10 == 0


def _payment(action: ProposedAction, ctx: SessionContext) -> str | None:
    if action.kind not in {"fill", "submit", "click"}:
        return None

    hit = _any_match(PAY_CONTROL_PATTERNS, action.control_text())
    if hit:
        return f"Control '{hit}' initiates payment. §2.1: never submit payment information."

    for key, value in action.data_fields().items():
        name = str(key).lower()
        if _any_match(PAYMENT_EXCLUSION_PATTERNS, name):
            continue
        field_hit = _any_match(PAYMENT_FIELD_PATTERNS, name)
        if field_hit:
            return (
                f"Field '{name}' collects payment or banking information. "
                f"§2.1: never submit payment information; hard stop to human checkpoint."
            )
        if isinstance(value, str) and _luhn_valid(value):
            return (
                f"The value submitted to '{name}' is a Luhn-valid card number regardless of the "
                f"field's name. §2.1: never submit payment information."
            )
    return None


# --------------------------------------------------------------------------------------
# P-SIGN-01
# --------------------------------------------------------------------------------------

SIGN_PATTERNS = _compile([
    r"\be[\s_-]?sign(?:ature)?\b",
    r"\bsignature\b",
    r"\bsign[\s_-]+(?:and[\s_-]+submit|here|document|application|now)\b",
    r"\belectronically[\s_-]*sign\b",
    r"\bi[\s_-]+(?:declare|certify|attest|acknowledge[\s_-]+and[\s_-]+agree)\b",
    r"\bdeclaration\b", r"\battestation\b",
    r"\bsubmit[\s_-]+(?:the[\s_-]+)?application\b",
])

#: Authentication is P-AUTH-01's business, and a declarations page is a document to read.
SIGN_EXCLUSION_PATTERNS = _compile([
    r"\bsign[\s_-]?in\b", r"\bsign[\s_-]?up\b", r"\bsigned[\s_-]?in\b", r"\bsigning[\s_-]?in\b",
    r"\bdesign\b", r"\bassign", r"\bdeclarations?[\s_-]+page\b", r"\bdec[\s_-]+page\b",
])


def _signature(action: ProposedAction, ctx: SessionContext) -> str | None:
    if action.kind not in {"click", "submit", "fill"}:
        return None
    text = action.control_text() + " " + " ".join(action.field_names())
    if _any_match(SIGN_EXCLUSION_PATTERNS, text):
        return None
    hit = _any_match(SIGN_PATTERNS, text)
    if hit:
        return (
            f"'{hit}' is a signature, declaration or attestation control. §2.1: never submit an "
            f"e-signature or an application declaration; hard stop to human checkpoint."
        )
    return None


# --------------------------------------------------------------------------------------
# P-BIND-01
# --------------------------------------------------------------------------------------

BIND_PATTERNS = _compile([
    r"\bbind\b",
    r"\bpurchase\b",
    r"\bcheck[\s_-]?out\b",
    r"\bbuy(?:[\s_-]+now)?\b",
    r"\bplace[\s_-]+(?:the[\s_-]+)?order\b",
    r"\bconfirm[\s_-]+(?:order|purchase|policy|and[\s_-]+pay)\b",
    r"\bcomplete[\s_-]+(?:purchase|order|checkout)\b",
    r"\b(?:activate|start)[\s_-]+(?:my[\s_-]+)?policy\b",
    r"\bcancel[\s_-]+(?:my[\s_-]+)?policy\b",
    r"\brenew[\s_-]+(?:my[\s_-]+)?policy\b",
])

#: Informational pages containing a bind verb are not bind controls.
BIND_EXCLUSION_PATTERNS = _compile([
    r"\bhow[\s_-]+to[\s_-]+buy\b", r"\bbuyer'?s?[\s_-]+guide\b", r"\bbuying[\s_-]+guide\b",
    r"\bwhere[\s_-]+to[\s_-]+buy\b", r"\bwhy[\s_-]+buy\b", r"\bbuying[\s_-]+tips\b",
])


def _bind(action: ProposedAction, ctx: SessionContext) -> str | None:
    if action.kind not in {"click", "submit"}:
        return None
    text = action.control_text()
    if _any_match(BIND_EXCLUSION_PATTERNS, text):
        return None
    hit = _any_match(BIND_PATTERNS, text)
    if hit:
        return (
            f"'{hit}' is a bind or purchase-intent control. §2.1: never bind, purchase, renew, "
            f"cancel or modify a policy."
        )
    return None


# --------------------------------------------------------------------------------------
# P-CAPTCHA-01
# --------------------------------------------------------------------------------------

CAPTCHA_PATTERNS = _compile([
    r"\b(?:re|h)?captcha\b", r"\bturnstile\b", r"\bbot[\s_-]*check\b",
    r"\bi'?m[\s_-]+not[\s_-]+a[\s_-]+robot\b", r"\bare[\s_-]+you[\s_-]+human\b",
    r"\bhuman[\s_-]+verification\b", r"\bchallenge[\s_-]?(?:frame|iframe|form)\b",
    r"\bcf[\s_-]?chl\b",
])


def _captcha(action: ProposedAction, ctx: SessionContext) -> str | None:
    # Only interaction is denied. Recording that a CAPTCHA was encountered is how the route gets
    # its terminal `blocked` status and its Friction Ledger entry (§10.7) — blocking the write
    # would destroy the evidence the refusal is supposed to produce.
    if action.kind not in {"fill", "click", "submit"}:
        return None
    text = action.control_text() + " " + " ".join(action.field_names())
    hit = _any_match(CAPTCHA_PATTERNS, text)
    if hit:
        return (
            f"'{hit}' is a CAPTCHA or bot control. §2.1: never bypass one. Record the route as "
            f"blocked and end it."
        )
    return None


# --------------------------------------------------------------------------------------
# P-AUTH-01
# --------------------------------------------------------------------------------------

CREDENTIAL_FIELD_PATTERNS = _compile([
    r"\bpass(?:word|wd|phrase)\b",
    r"\botp\b", r"\bone[\s_-]?time[\s_-]?(?:code|password|passcode)\b",
    r"\b2fa\b", r"\bmfa\b", r"\bverification[\s_-]*code\b", r"\bauth[\s_-]*code\b",
    r"\bsecurity[\s_-]*(?:question|answer)\b",
    r"\busername\b", r"\buser[\s_-]?id\b", r"\bcredential",
    r"\bpin\b",
])

AUTH_CONTROL_PATTERNS = _compile([
    r"\blog[\s_-]?in\b", r"\bsign[\s_-]?in\b", r"\bcreate[\s_-]+(?:an[\s_-]+)?account\b",
])


def _auth(action: ProposedAction, ctx: SessionContext) -> str | None:
    if action.kind not in {"fill", "submit"}:
        return None

    host = target_host(action.target)
    if host and host in ctx.registered_services:
        return None

    for name in action.field_names():
        hit = _any_match(CREDENTIAL_FIELD_PATTERNS, name)
        if hit:
            return (
                f"Field '{name}' is a credential and '{host or action.target}' is not a "
                f"registered service. §2.1: never enter credentials to an unregistered service."
            )

    hit = _any_match(AUTH_CONTROL_PATTERNS, action.control_text())
    if hit and any(_any_match(CREDENTIAL_FIELD_PATTERNS, n) for n in action.field_names()):
        return f"'{hit}' authenticates to an unregistered service."
    return None


# --------------------------------------------------------------------------------------
# P-RECORD-01
# --------------------------------------------------------------------------------------

def _record(action: ProposedAction, ctx: SessionContext) -> str | None:
    if action.kind != "record":
        return None
    if ctx.call.recording_consent is RecordingConsent.GRANTED:
        return None
    return (
        f"Recording consent is {ctx.call.recording_consent.value}, not GRANTED. §2.1: never "
        f"record or transcribe a call without affirmative consent."
    )


# --------------------------------------------------------------------------------------
# P-DISCLOSE-01
# --------------------------------------------------------------------------------------

def _disclose(action: ProposedAction, ctx: SessionContext) -> str | None:
    if action.kind != "speak":
        return None
    if ctx.call.disclosure_delivered:
        return None
    # The prelude is itself a `speak`, so it must be able to go first or no call can ever start.
    if action.payload_items().get("is_disclosure_prelude") is True:
        return None
    return (
        "This call has not delivered the automation disclosure prelude. §2.2: disclose that the "
        "agent is automated at the start of every call, inbound and outbound."
    )


# --------------------------------------------------------------------------------------
# P-BUDGET-01
# --------------------------------------------------------------------------------------

def _budget(action: ProposedAction, ctx: SessionContext) -> str | None:
    budget = ctx.budget_for(action.route_id)
    if budget.expired():
        return (
            f"Route '{action.route_id}' is past its time budget. §9.4: bounded attempts are "
            f"non-negotiable."
        )
    if action.kind in ATTEMPT_CONSUMING_KINDS and budget.exhausted():
        return (
            f"Route '{action.route_id}' has used {budget.attempts_used} of "
            f"{budget.max_attempts} permitted attempts. §9.4: never retry a rejection, CAPTCHA "
            f"or terms restriction."
        )
    return None


# --------------------------------------------------------------------------------------
# P-HUMAN-01  (the ESCALATE path — see OQ-006)
# --------------------------------------------------------------------------------------

CHECKPOINT_PATTERNS: tuple[tuple[HumanCheckpoint, tuple[Pattern[str], ...]], ...] = (
    (HumanCheckpoint.IDENTITY_VERIFICATION, _compile([
        r"\bverify[\s_-]+your[\s_-]+identity\b", r"\bidentity[\s_-]+verification\b",
        r"\bconfirm[\s_-]+your[\s_-]+identity\b", r"\bsecurity[\s_-]+question\b",
        r"\bprove[\s_-]+who[\s_-]+you[\s_-]+are\b",
    ])),
    (HumanCheckpoint.CONSENT_ATTESTATION, _compile([
        r"\bconsent[\s_-]+(?:to|form|attestation)\b", r"\bdo[\s_-]+you[\s_-]+consent\b",
        r"\bgive[\s_-]+(?:your[\s_-]+)?consent\b",
    ])),
    (HumanCheckpoint.THIRD_PARTY_RECORDS_AUTHORIZATION, _compile([
        r"\bauthoriz\w*[\s_-]+(?:us[\s_-]+)?to[\s_-]+(?:pull|obtain|access|order)\b",
        r"\bcredit[\s_-]+(?:check|inquiry|consent)\b",
        r"\bdriver[\s_-]+(?:record|abstract)[\s_-]+(?:check|consent|authorization)\b",
        r"\bmvr\b",
    ])),
    (HumanCheckpoint.COVERAGE_ADVICE, _compile([
        r"\bcoverage[\s_-]+advice\b",
        # Tolerates natural phrasing between the noun and the verb: "what coverage you should
        # choose", "what coverage do I need". A rigid adjacency here misses real requests.
        r"\bwhat[\s_-]+coverage\b[^.?]{0,30}?\b(?:should|need|recommend|advise|choose)\b",
        r"\brecommend[\s_-]+(?:a[\s_-]+)?coverage\b", r"\bwhich[\s_-]+coverage[\s_-]+is[\s_-]+best\b",
        r"\badvise[\s_-]+(?:me[\s_-]+)?(?:on|about)\b", r"\bwhat[\s_-]+(?:do[\s_-]+you[\s_-]+)?recommend\b",
    ])),
)


def _human_checkpoint(action: ProposedAction, ctx: SessionContext) -> str | None:
    declared = action.payload_items().get("human_checkpoint")
    if declared:
        value = declared.value if isinstance(declared, HumanCheckpoint) else str(declared)
        return f"Human checkpoint required: {value}. §9.1: routed to the operator, not refused."

    text = action.control_text() + " " + action.rationale.lower()
    for checkpoint, patterns in CHECKPOINT_PATTERNS:
        hit = _any_match(patterns, text)
        if hit:
            return (
                f"Human checkpoint required: {checkpoint.value} (matched '{hit}'). §2.2: stop "
                f"and escalate to the operator. This is not a refusal — the route stays open."
            )
    return None


# --------------------------------------------------------------------------------------
# Registration
# --------------------------------------------------------------------------------------

DEFAULT_RULES: tuple[Rule, ...] = (
    Rule("P-STOP-01", "DENY", "§2.1 never continue after a request to stop",
         "any action after a stop request", _stop),
    Rule("P-SANDBOX-01", "DENY", "§2.3 sandbox-only profiles never touch a real destination",
         "any real-destination action carrying a sandbox_only profile", _sandbox),
    Rule("P-HYPO-LICENCE-01", "DENY", "§2.1 never submit a licence number under a hypothetical",
         "any driver's licence number submitted under a hypothetical profile",
         _hypothetical_licence),
    Rule("P-HYPO-HUMAN-01", "DENY", "§2.1 no human contact under a hypothetical profile",
         "any voice, callback or human-contact action carrying a hypothetical profile",
         _hypothetical_human),
    Rule("P-HYPO-STEP-01", "DENY", "§2.1 no commitment steps under a hypothetical profile",
         "identity, consent, declaration, callback-enrolment and purchase steps under a "
         "hypothetical profile", _hypothetical_step, terminal_status="manual_handoff"),
    Rule("P-THIRDPARTY-01", "DENY", "§2.1 never enter another person's data without consent",
         "third-party personal data", _third_party),
    Rule("P-LICENCE-01", "DENY", "§2.1 never fabricate, borrow, alter or store another licence",
         "any licence value not matching the vault's registered operator value", _licence),
    Rule("P-REAL-FACT-01", "DENY", "§2.2 use the operator's own real, accurate information",
         "any fabricated material fact submitted under a non-hypothetical profile", _real_fact),
    Rule("P-FACT-01", "DENY", "§2.1 never change material facts to chase a lower price",
         "any submitted value diverging from the session fact-lock, on every profile",
         _fact_drift),
    Rule("P-PLATE-01", "DENY", "§2.1 skip optional plate fields; record blocked if mandatory",
         "submission of a licence plate value", _plate, terminal_status="blocked"),
    Rule("P-PAY-01", "DENY", "§2.1 never submit payment information",
         "payment fields, card numbers, banking fields", _payment),
    Rule("P-SIGN-01", "DENY", "§2.1 never submit an e-signature or application declaration",
         "signature, declaration or attestation controls", _signature),
    Rule("P-BIND-01", "DENY", "§2.1 never bind, purchase, renew, cancel or modify a policy",
         "clicks on bind/purchase/buy/confirm-order controls", _bind),
    Rule("P-CAPTCHA-01", "DENY", "§2.1 never bypass a CAPTCHA or bot control",
         "any interaction with a CAPTCHA or bot check", _captcha),
    Rule("P-AUTH-01", "DENY", "§2.1 never bypass authentication",
         "credential entry to unregistered services", _auth),
    Rule("P-RECORD-01", "DENY", "§2.1 never record without affirmative consent",
         "record while consent state is not GRANTED", _record),
    Rule("P-DISCLOSE-01", "DENY", "§2.2 disclose automation at the start of every call",
         "speak on a fresh call not preceded by the disclosure prelude", _disclose),
    Rule("P-BUDGET-01", "DENY", "§9.4 bounded-attempt policy",
         "actions exceeding the route's attempt or time budget", _budget),
    Rule("P-HUMAN-01", "ESCALATE", "§9.1 human checkpoint queue (documented extension, OQ-006)",
         "identity lookup, consent attestation, coverage advice", _human_checkpoint),
)

#: Returned when no rule fires. Not a rule — a recorded absence of one.
NO_RULE_FIRED = "P-ALLOW-00"

SPECIFIED_DENY_RULE_IDS: frozenset[str] = frozenset({
    "P-BIND-01", "P-SIGN-01", "P-PAY-01", "P-CAPTCHA-01", "P-AUTH-01", "P-FACT-01",
    "P-LICENCE-01", "P-THIRDPARTY-01", "P-SANDBOX-01", "P-BUDGET-01", "P-DISCLOSE-01",
    "P-RECORD-01", "P-STOP-01",
    # Added 2026-08-09 by amendment D-002, following the organizer Q&A (AC-001).
    "P-HYPO-LICENCE-01", "P-HYPO-HUMAN-01", "P-HYPO-STEP-01", "P-REAL-FACT-01", "P-PLATE-01",
})
