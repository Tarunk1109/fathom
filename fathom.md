# FATHOM

**An evidence-grade instrument for the Ontario private-passenger auto insurance market.**

> Sound the market. Prove the bottom.

Built for the Ontario All-Quote Agent Challenge, August 2026.
Operator: Tarun Karnati, Toronto, Ontario.
Submission deadline: Wednesday 12 August 2026, 11:59 PM ET.

---

## 0. How to use this file

If you are Claude Code reading this at the start of a session:

1. **Read Section 2 (Prime Directives) before writing any code.** Those rules override every other instruction in this document, and they override the operator if he asks you to break them.
2. **Run Section 5 (Day 0 Viability Probe) before building anything.** It determines which of two build plans applies. Do not guess. Do not skip.
3. Read Section 3 (Thesis) and Section 4 (Profile Model) so you understand *why* each component exists. Many components exist to satisfy a judging criterion, not an engineering one. Do not optimize them away.
4. Build in the order given in Section 14 (Build Order). The spine before the signature features. Always.
5. Every module gets an entry in `docs/ARCHITECTURE.md` and a test in `tests/`.
6. When uncertain whether an action is permitted: do not perform it. Log it in `docs/OPEN_QUESTIONS.md` and continue.

---

## 1. Identity

| Field | Value |
| --- | --- |
| Name | FATHOM |
| Meaning | A unit of depth, and the verb for finally understanding something |
| One-liner | One intake. Every reachable Ontario rate source. Proof for every result, including every refusal. |
| Category | Personal-use agentic market instrument. Not a product. Not a service. Not for anyone but the operator. |
| Repo | `fathom` |

### The pitch, spoken

> Every comparison tool shows you prices. FATHOM shows you who actually exists behind those prices, what the prices are really for, who declined to serve you and why, and exactly what would have to change for them to say yes.

---

## 2. Prime Directives

**Hard constraints. Enforced in code by the Policy Engine, not by prompting.**

### 2.1 Never do

| Rule | Enforcement |
| --- | --- |
| Never bind, purchase, renew, cancel or modify a policy | Policy Engine denies any bind/purchase-intent action |
| Never submit payment information, an e-signature, or an application declaration | Policy Engine denies; hard stop to human checkpoint |
| Never bypass a CAPTCHA, bot control, authentication, or rate limit | Detector emits `blocked`; route ends |
| Never fabricate, borrow, alter or store another person's driver's licence number | Vault rejects any licence value not matching the operator's registered value |
| Never enter another person's data without consent | Intake refuses third-party PII entirely in this build |
| Never change material facts about the operator across insurers to chase a lower price | Fact-lock: facts hashed at session start; divergent submissions denied |
| Never present an estimate, lead form or callback promise as a firm quote | Status enum mandatory; UI renders estimates in a separate band |
| Never submit a driver's licence number under a hypothetical profile | `P-HYPO-LICENCE-01`. Non-negotiable: the brief bans it and the organizer Q&A did not address it |
| Never place a voice, callback or human-contact action under a hypothetical profile | `P-HYPO-HUMAN-01`. The Q&A covered web forms; representing a hypothetical to a real person remains prohibited |
| Never complete identity verification, consent attestation, declaration, callback enrolment or purchase steps under a hypothetical profile | `P-HYPO-STEP-01`; emits `manual_handoff` |
| Never submit a fabricated material fact under a non-hypothetical profile | `P-REAL-FACT-01`. Mirrors `P-HYPO-LICENCE-01`; the two profiles may not bleed into each other |
| Never send a `sandbox_only` profile to a real destination | `P-SANDBOX-01`. Governs real-destination access only; no longer conflated with `hypothetical` |
| Never submit a licence plate. Skip optional plate fields; if a plate is mandatory, record `blocked` with the exact field and stop | `P-PLATE-01` |
| Never misrepresent the caller as a human, broker, agent, or insurer employee | Voice disclosure prelude is non-removable and checksummed |
| Never record or transcribe a call without affirmative consent | Consent state machine gates the recorder; default `NO_AUDIO` |
| Never place repeated calls or continue after a request to stop | One call, one retry only on pre-connection failure |
| Never sell, license, publish for public use, or deploy this as a service | LICENSE and README state personal-use only |
| Never let a real licence number, full address, payment data or raw call audio reach the repo, logs, prompts, traces, screenshots or the submission | Redactor runs before every write; CI greps for PII patterns |
| Never allege that any company violated a law or regulation | Friction Ledger records observations with timestamps only; no legal characterization anywhere in code, UI or submission |

### 2.2 Always do

- Use the operator's own real, accurate information for any live interaction with a real insurer, agent or broker.
- Disclose that the agent is automated at the start of every call, inbound and outbound.
- Stop and escalate to the operator the instant a representative requires consent, identity verification, licensed advice, or a declaration.
- Record a terminal status with evidence for every rate source attempted. `unresolved` stays `unresolved`.
- Keep unresolved records in the denominator of every metric.
- Treat every route identically. No route is favoured, promoted, criticized or omitted for any reason other than an evidenced one.

### 2.3 The hypothetical-profile rule

*Amended 2026-08-09 following the organizer Q&A (AC-001). Supersedes the prior alias and simulation
rule, which barred every non-operator profile from every real destination.*

**Two flags, no longer one concept.**

- `hypothetical` governs **conduct**: licence-number submission, human contact, and step gating.
- `sandbox_only` governs **reach**: whether the profile may touch a real destination at all.

A hypothetical profile **may** complete quote forms at real destinations. The organizers explicitly
permit it and recommend a clean-record profile to maximise returned rates.

A hypothetical profile may **never**: carry a driver's licence number; reach a real human by voice,
callback or any other human-contact channel; or complete identity verification, consent attestation,
a declaration, callback enrolment or a purchase step. Any of those stops the run and records
`manual_handoff`.

A `sandbox_only` profile may never touch a real destination, and must be visibly labelled as a
simulation in every view and in the walkthrough.

**Every hypothetical profile is labelled as hypothetical in every view and in the walkthrough.** The
distinction between a retrieved rate for a hypothetical driver and one for the operator is never
blurred, in the UI or in the submission.

---

## 3. Thesis

*Reframed 2026-08-09 following the organizer Q&A (AC-001). Every evidence, dedup and parity
requirement in this document is unchanged.*

**Primary output: broad, evidenced retrieval across as many rate sources as the agent can reach**,
run agentically under `profile_hypo_clean`, a clean-record hypothetical driver. The organizers
permit any driver profile and require an agentic element — automation is the ask, not a bonus, and
form coverage is a graded outcome.

**Second lens, layered on top: the operator's own G1, no-vehicle profile.** It is the profile the
Ontario market is structurally worst at serving — learner permit only, no owned vehicle, no Canadian
driving history — and it produces the richest distribution of refusals, conditions and stated
reasons available to any participant. Those refusals are what power the Eligibility Frontier.

So FATHOM both **retrieves** and **measures**. The clean profile establishes reach; the operator
profile establishes the boundary. Neither result is ever presented as the other: a rate returned for
a hypothetical driver is labelled as such everywhere it appears.

Four outputs, each of which a conventional participant cannot produce:

1. **A guaranteed price, computed.** The residual market publishes its full rate manual. FATHOM compiles that manual into an executable rater and calculates the operator's premium offline, with zero dependency on any website or human.
2. **The open market's answer, retrieved with proof.** Every reachable rate source ends in an evidenced terminal status. Refusals are first-class results, not errors.
3. **The path forward, derived.** Every decline carries a reason. Inverted, those reasons become an ordered ladder: which single change unlocks which markets.
4. **Which vehicle to buy.** Only a pre-purchase operator has the vehicle as a free variable.

### 3.1 The winning principle

The brief states that a smaller number of trustworthy, comparable quotes with excellent evidence beats a large pile of duplicated or estimated results. FATHOM is designed to lose the volume contest deliberately and win the trust contest decisively.

---

## 4. The Profile Model

**FATHOM is profile-adaptive by design. The operator's situation is an input, not a hardcoded assumption.**

This is architecturally important and it is also the answer to the obvious judge question.

### 4.1 Profile registry

Profiles live in `data/profiles/` as records, not code paths.

*Amended 2026-08-09 following AC-001. `sandbox_only: bool` is replaced by two independent fields.*

```json
{
  "profile_id": "profile_hypo_clean",
  "hypothetical": true,
  "sandbox_only": false,
  "licence_class": "G",
  "vehicle_status": "owned",
  "canadian_history_months": 120,
  "prior_insurance": true,
  "claims": [],
  "convictions": [],
  "residence": "Ontario",
  "licence_number": null,
  "eligible_channels": ["direct_web", "aggregator"],
  "active_modules": ["registry","graph","rater","benefit_probe","parity_measured",
                     "vehicle_inversion","channel_arbitrage","friction"],
  "gated_modules": ["voice","broker_human","frontier"]
}
```

| Profile | `hypothetical` | `sandbox_only` | Role and what activates |
| --- | --- | --- | --- |
| `profile_hypo_clean` | **true** | false | **PRIMARY.** Clean-record hypothetical. Maximises returned rates and unlocks every priced-state module: benefit probe, measured parity, vehicle inversion, channel arbitrage. **No licence number, ever. No voice, no callback, no human contact.** |
| `profile_operator` (real G1, no car) | false | false | Real information. Powers the Eligibility Frontier, friction ledger and broker harvester. **Full voice and human-contact permissions.** Fact-locked to the vault's registered values. |
| `profile_sim_g2` | true | **true** | Sandbox only, unchanged. Never touches a real destination. |

**The two fields are independent.** `hypothetical` governs conduct — licence number, human contact,
step gating. `sandbox_only` governs reach. A profile can be hypothetical and still run against real
quote forms; that is the primary profile. A profile can be sandbox-only for reasons unrelated to
being hypothetical.

The Route Planner reads the active profile and lights up the corresponding modules. **Nothing is
hardcoded to any licence class.**

### 4.2 Why this matters

It proves the system is general rather than built around one person's circumstances, and it gives the operator an honest, confident answer to "what if you had a G2?" that is demonstrated rather than claimed.

**Enforcement:** `P-SANDBOX-01` denies any real-destination action carrying `sandbox_only: true`.
`P-HYPO-LICENCE-01`, `P-HYPO-HUMAN-01` and `P-HYPO-STEP-01` govern `hypothetical: true` regardless
of destination. `P-REAL-FACT-01` binds a non-hypothetical profile to the vault's registered values.

### 4.3 Expected result distributions

**Two distributions, never merged in the UI.**

Under `profile_hypo_clean` (primary), design for a wall of quotes:

- Majority: `quoted_comparable`, `quoted_non_comparable`
- Minority: `estimate_only`, `callback_required`, `blocked`
- Expected: `manual_handoff` wherever a journey reaches an identity, consent, declaration or
  purchase step — that is `P-HYPO-STEP-01` working, not a failure

Under `profile_operator` (second lens), design for evidenced refusal:

- Majority: `ineligible`, `manual_handoff`, `callback_required`, `specialty_only`
- Minority: `estimate_only`, `quoted_non_comparable`
- Rare: `quoted_comparable`
- Guaranteed: exactly one `computed` residual-market premium

Broad retrieval under the clean profile, plus an ordered ladder of what unlocks what under the
operator profile, is the submission. Neither half is presented as the other.

---

## 5. Day 0 Reconnaissance Probe

*Purpose amended 2026-08-09 following AC-001. **Plan A applies.** The probe no longer selects a
build plan — it maps the four routes so the web executor is built against known ground.*

### 5.1 What the probe now answers

1. **Which of the four routes returns a rate under `profile_hypo_clean`?** This sizes the primary
   retrieval surface.
2. **Which expose the post-1-July-2026 accident-benefit election toggles?** This gates the Benefit
   Price Probe (§10.2) per route.
3. **What is each route's quote reference ID grammar?** Fingerprinting signal 2 (§9.3).
4. **What are the operator-profile outcomes?** Still recorded, because every refusal, its exact
   stopping step and its stated reason feed the Eligibility Frontier (§10.3).

### 5.2 Conduct

Record results in `docs/DAY0_PROBE.md`. This is itself submission evidence, so timestamp it and
redact it.

The probe is hand-run reconnaissance for the operator's own benefit. **It is not the submission's
automation, and it never substitutes for it** — AC-001 item 2 is explicit that manual form filling
is not acceptable and an agentic element is required. Everything the probe learns becomes a route
recipe (§11.1) executed by the web executor.

Under `profile_hypo_clean`: no licence number, no plate, and stop at any identity, consent,
declaration, callback-enrolment or purchase step. Under `profile_operator`: the operator's own real
information, per §2.2.

---

## 6. Audience context

Public, professional context only. Use it to choose vocabulary and emphasis, never to flatter.

The judging panel includes senior leadership from a Toronto insurtech whose current public thesis is submission quality and underwriting confidence: reconciling quoted risk data against source-of-truth signals, and producing explainable assessments backed by **reason codes, confidence indicators and evidence status**. They have also publicly framed agentic AI as software interacting with APIs rather than a human interacting with a front end, and have published on the 1 July 2026 accident-benefit changes.

### 6.1 What this implies for FATHOM

| Implication | Action |
| --- | --- |
| They evaluate systems on evidence quality and explainability | Adopt PASS / CAUTION / FAIL assessments with reason codes and evidence status on every result (Section 8.4) |
| Data trustworthiness is their core concern | Lead the walkthrough with fact-lock, not with automation |
| They define agentic AI as API-first, not cursor-first | Frame computer use as a fallback. Never make visible browser clicking the centrepiece. |
| They are practitioners in this exact market | A single invented number ends the submission. Everything provable or explicitly marked unknown. |
| They operate a comparison platform | See 6.2. This is important. |

### 6.2 The neutrality rule

Comparison and aggregator routes are **included in the registry and run exactly like every other route**. Their results are recorded neutrally, with the same evidence standard.

FATHOM never frames its findings as a criticism of comparison platforms. The accurate framing, which the industry itself publishes, is that any panel's output is bounded by its live panel and the applicant's eligibility. FATHOM measures that boundary. It does not editorialize about it.

Omitting a major route would be a more serious error than including one that declines the operator.

---

## 7. Architecture

```
                    ┌──────────────────────────┐
                    │  Profile Registry        │
                    │  + Adaptive Intake       │
                    │  + Encrypted Vault       │
                    └────────────┬─────────────┘
                                 │
                    ┌────────────▼─────────────┐
                    │  POLICY ENGINE           │  ◄── deterministic, non-LLM
                    │  every action passes     │      denies bind/pay/sign/captcha/
                    │  through this gate       │      fact-drift/sandbox-to-real
                    └────────────┬─────────────┘
                                 │
         ┌───────────────────────┼───────────────────────┐
         │                       │                       │
┌────────▼────────┐   ┌──────────▼─────────┐   ┌─────────▼────────┐
│ Market Registry │◄──┤  Route Planner     │   │ Rulebook         │
│ + Rate-Source   │   │  priority, budget, │   │ Compiler         │
│   Graph         │   │  channel, profile  │   │ (offline rater)  │
└─────────────────┘   └──────────┬─────────┘   └─────────┬────────┘
                                 │                       │
         ┌───────────────┬───────┴───────┬───────────────┤
┌────────▼──────┐ ┌──────▼──────┐ ┌──────▼──────┐ ┌──────▼──────┐
│ Web Executor  │ │ Voice       │ │ Broker      │ │ Computed    │
│ (self-healing)│ │ Executor    │ │ Executor    │ │ Result      │
└────────┬──────┘ └──────┬──────┘ └──────┬──────┘ └──────┬──────┘
         └───────────────┴───────┬───────┴───────────────┘
                                 │
                    ┌────────────▼─────────────┐
                    │  Redactor (local model)  │
                    │  then EVIDENCE CHAIN     │
                    │  content-addressed,      │
                    │  hash-chained, verifiable│
                    └────────────┬─────────────┘
                                 │
    ┌───────────┬────────────────┼────────────────┬───────────┐
┌───▼──────┐ ┌──▼─────────┐ ┌────▼──────┐ ┌───────▼──┐ ┌──────▼────┐
│Normalizer│ │Assessment  │ │Eligibility│ │ Vehicle  │ │ Scorecard │
│+ Parity  │ │PASS/CAUTION│ │ Frontier  │ │Inversion │ │ + Metrics │
│  Solver  │ │/FAIL       │ │  Solver   │ │  Engine  │ │           │
└──────────┘ └────────────┘ └───────────┘ └──────────┘ └───────────┘
```

### 7.1 The load-bearing decision

**Everything routes through the Policy Engine.** No executor calls a browser, phone or API directly. Every proposed action is a structured object submitted to the gate, which returns `ALLOW`, `DENY` or `ESCALATE` plus the rule that fired, and appends the decision to the hash-chained audit log.

This is what makes the safety claim demonstrable rather than aspirational, and it is the single most impressive thing to show live.

### 7.2 MCP as the substrate

| MCP server | Exposes |
| --- | --- |
| `fathom-registry` | registry read/write, graph queries, dedup resolution |
| `fathom-evidence` | append artifact, verify chain, fetch redacted artifact |
| `fathom-policy` | evaluate action, list rules, fetch audit log |
| `fathom-vault` | field injection by destination; never returns raw values |
| `fathom-rater` | offline residual-market premium calculation |
| `fathom-routes` | recipe store, replay, healing events |
| `fathom-profiles` | profile registry, active profile, module gating |

---

## 8. Data model

### 8.1 Status enum (from the brief, plus one documented extension)

```python
class TerminalStatus(str, Enum):
    QUOTED_COMPARABLE      = "quoted_comparable"
    QUOTED_NON_COMPARABLE  = "quoted_non_comparable"
    ESTIMATE_ONLY          = "estimate_only"
    CALLBACK_REQUIRED      = "callback_required"
    MANUAL_HANDOFF         = "manual_handoff"
    INELIGIBLE             = "ineligible"
    AFFINITY_RESTRICTED    = "affinity_restricted"
    SPECIALTY_ONLY         = "specialty_only"
    DUPLICATE_RATE_SOURCE  = "duplicate_rate_source"
    NOT_CURRENTLY_WRITING  = "not_currently_writing"
    BLOCKED                = "blocked"
    UNREACHABLE            = "unreachable"
    UNRESOLVED             = "unresolved"      # NEVER auto-converted
    COMPUTED               = "computed"        # FATHOM extension, documented
```

`COMPUTED` is a calculation from a published public rate manual, not a quote from an insurer. It is rendered in its own band, never mixed with retrieved quotes, and always carries manual version, effective date, source URL, rating path and verification pass rate.

### 8.2 Reason code taxonomy

Every non-quoted result carries exactly one reason code. This drives the Eligibility Frontier and gives judges an explainable structure.

```python
class ReasonCode(str, Enum):
    RC_LICENCE_CLASS      = "licence_class_insufficient"      # unlock: obtain_g2 / obtain_g
    RC_NO_VEHICLE         = "no_owned_vehicle"                # unlock: own_vehicle
    RC_NO_HISTORY         = "insufficient_driving_history"    # unlock: accumulate_history
    RC_NO_PRIOR_INSURANCE = "no_prior_insurance_record"       # unlock: hold_policy_12m
    RC_MEMBERSHIP         = "membership_or_group_required"    # unlock: join_group
    RC_BROKER_ONLY        = "licensed_intermediary_required"  # unlock: engage_broker
    RC_PRODUCT_SCOPE      = "product_not_standard_ppa"        # unlock: none
    RC_NOT_WRITING        = "not_writing_new_business"        # unlock: none
    RC_ACCESS_CONTROL     = "access_control_encountered"      # unlock: none
    RC_HUMAN_REQUIRED     = "human_checkpoint_required"       # unlock: operator_action
    RC_UNKNOWN            = "reason_not_stated"               # unlock: unknown
```

`RC_UNKNOWN` is a legitimate value. Never guess a reason to fill the field.

### 8.3 Market registry record

```json
{
  "registry_id": "reg_0041",
  "legal_underwriter": "string",
  "insurer_group": "string",
  "brand_or_program": "string",
  "distribution_type": "direct|agent|broker|aggregator|affinity|MGA_program|mutual|residual",
  "product_scope": "standard_PPA|nonstandard_PPA|high_net_worth|collector|commercial_specialty|unknown",
  "distinct_rate_source_id": "rs_0012",
  "quote_url": "https://...",
  "public_phone_route": "string",
  "licensed_intermediary": "string + regulator evidence",
  "requirements": ["licence","VIN","membership","callback","human"],
  "automation_notes": "terms, CAPTCHA, rate limit, handoff notes",
  "status": "one value from TerminalStatus",
  "reason_code": "one value from ReasonCode",
  "source_url": "authoritative evidence",
  "last_verified_at": "ISO 8601",
  "evidence_artifact": "cid:sha256-...",
  "rate_filing_delta": { "period": "2026Q2", "approved_change_pct": -1.4 },
  "fingerprint": {
    "underwriter_disclosed": "string",
    "quote_id_grammar": "string",
    "form_set_hash": "sha256-...",
    "signals_agreeing": 2
  }
}
```

### 8.4 Quote result record

```json
{
  "result_id": "res_0007",
  "profile_id": "operator",
  "registry_id": "reg_0041",
  "distinct_rate_source_id": "rs_0012",
  "status": "quoted_non_comparable",
  "reason_code": null,
  "channel": "web|voice|broker|computed",

  "assessment": {
    "verdict": "PASS|CAUTION|FAIL",
    "reason_codes": ["coverage_variance_unpriced"],
    "confidence_indicator": "high|medium|low",
    "evidence_status": "verified|partial|absent"
  },

  "price": {
    "annual_premium": 0.0, "monthly_amount": 0.0, "down_payment": 0.0,
    "instalment_count": 0, "finance_charges": 0.0, "taxes_fees": 0.0,
    "total_estimated_cost": 0.0, "currency": "CAD"
  },

  "coverage": {
    "effective_date": "ISO 8601",
    "term_months": 12,
    "third_party_liability_limit": 2000000,
    "dcpd": { "included": true, "deductible": 0, "opcf49_elected": false },
    "own_damage": {
      "collision": { "included": true, "deductible": 1000 },
      "comprehensive": { "included": true, "deductible": 1000 },
      "all_perils": { "included": false },
      "specified_perils": { "included": false }
    },
    "accident_benefits": {
      "medical_rehab_attendant_care": "mandatory_included",
      "income_replacement": "included|excluded|unavailable|unknown",
      "non_earner": "included|excluded|unavailable|unknown",
      "caregiver": "included|excluded|unavailable|unknown",
      "lost_educational_expenses": "included|excluded|unavailable|unknown",
      "expenses_of_visitors": "included|excluded|unavailable|unknown",
      "housekeeping_home_maintenance": "included|excluded|unavailable|unknown",
      "damage_to_personal_items": "included|excluded|unavailable|unknown",
      "death": "included|excluded|unavailable|unknown",
      "funeral": "included|excluded|unavailable|unknown",
      "dependant_care": "included|excluded|unavailable|unknown",
      "indexation": "included|excluded|unavailable|unknown",
      "supplementary_med_rehab_attendant": "included|excluded|unavailable|unknown",
      "catastrophic_impairment": "included|excluded|unavailable|unknown"
    },
    "uninsured_automobile": { "included": true, "limit": null },
    "endorsements": {
      "opcf_20_transportation_replacement": "included|excluded|unavailable|unknown",
      "opcf_27_non_owned": "included|excluded|unavailable|unknown",
      "opcf_43_no_depreciation": "included|excluded|unavailable|unknown",
      "opcf_44r_family_protection": "included|excluded|unavailable|unknown"
    },
    "variance_from_benchmark": ["plain-language list of every difference"]
  },

  "discounts": { "applied": [], "available_not_selected": [], "conditional_on_purchase": [] },

  "validity": {
    "quote_reference_id": "string",
    "expiry_or_guarantee_date": "ISO 8601",
    "verification_may_change_premium": true
  },

  "evidence": {
    "timestamp": "ISO 8601",
    "source_url_or_phone_route": "string",
    "artifact_cid": "cid:sha256-...",
    "chain_index": 41,
    "prev_hash": "sha256-..."
  },

  "twin_reader": { "agreement": true, "reading_a": 0.0, "reading_b": 0.0 },

  "parity": {
    "price_at_benchmark": 0.0,
    "adjustments_applied": [{"item":"income_replacement","delta":0.0,"source":"measured|unavailable"}],
    "parity_confidence": "measured|partial|not_possible"
  },

  "privacy": {
    "fields_disclosed": ["postal_code","birth_year","licence_class"],
    "consent_receipt_id": "cr_0004",
    "retention_deadline": "ISO 8601"
  },

  "decline": {
    "stated_reason_redacted": "string",
    "reason_code": "one value from ReasonCode",
    "unlock_conditions": ["obtain_g2","own_vehicle"]
  }
}
```

**Assessment rules:**

| Verdict | Condition |
| --- | --- |
| `PASS` | exact premium, benchmark coverage matched, evidence verified, twin readers agree |
| `CAUTION` | premium returned but coverage varies, or parity is partial, or readers disagree |
| `FAIL` | no premium available, or evidence absent, or the route could not be completed |

`FAIL` on a route is not a failure of FATHOM. It is a recorded measurement.

### 8.5 Benchmark coverage

Every route requests the same package. Comparison benchmark, not coverage advice.

- $2,000,000 third-party liability
- DCPD included, no OPCF 49
- Mandatory medical, rehabilitation, attendant care
- Every other accident benefit recorded explicitly as included / excluded / unavailable / unknown
- Collision $1,000 deductible, comprehensive $1,000 deductible
- OPCF 44R requested
- No telematics unless separately opted in, always reported as a separate quote
- Same requested effective date across all routes, 12-month term where available

---

## 9. Tier 1: the spine

### 9.1 Policy Engine

Deterministic. No LLM in the decision path.

```python
@dataclass
class ProposedAction:
    kind: Literal["navigate","fill","click","submit","dial","speak","hangup","record","write","fetch"]
    target: str
    payload: dict | None
    route_id: str
    session_id: str
    profile_id: str
    rationale: str

@dataclass
class PolicyDecision:
    verdict: Literal["ALLOW","DENY","ESCALATE"]
    rule_id: str
    explanation: str
    audit_index: int
```

| Rule ID | Denies |
| --- | --- |
| `P-BIND-01` | clicks on bind/purchase/buy/confirm-order controls |
| `P-SIGN-01` | signature, declaration or attestation controls |
| `P-PAY-01` | payment fields, card numbers, banking fields |
| `P-CAPTCHA-01` | any interaction with a CAPTCHA or bot check |
| `P-AUTH-01` | credential entry to unregistered services |
| `P-FACT-01` | any submitted value diverging from the session fact-lock — **every profile**, so results stay comparable across insurers |
| `P-LICENCE-01` | any licence value not matching the vault's registered operator value |
| `P-THIRDPARTY-01` | third-party personal data |
| `P-SANDBOX-01` | any real-destination action carrying a `sandbox_only` profile |
| `P-HYPO-LICENCE-01` | any driver's licence number submitted under a `hypothetical` profile |
| `P-HYPO-HUMAN-01` | any voice, callback or human-contact action carrying a `hypothetical` profile |
| `P-HYPO-STEP-01` | identity verification, consent attestation, declaration, callback enrolment or purchase steps under a `hypothetical` profile — emits `manual_handoff` |
| `P-REAL-FACT-01` | any fabricated material fact submitted under a non-`hypothetical` profile |
| `P-PLATE-01` | submission of a licence plate value — emits `blocked` where the field is mandatory |
| `P-BUDGET-01` | actions exceeding the route's attempt or time budget |
| `P-DISCLOSE-01` | `speak` on a fresh call not preceded by the disclosure prelude |
| `P-RECORD-01` | `record` while consent state is not `GRANTED` |
| `P-STOP-01` | any action after a stop request |

`ESCALATE` routes to the human checkpoint queue: identity lookup, consent attestation, coverage advice.

**Every decision, allow or deny, appends to the hash-chained audit log.**

### 9.2 Adaptive Intake + Vault

- Superset of the OAF 1 fields with data minimization: ask only what the selected route needs.
- **Adaptive ordering:** ask the question that most reduces remaining uncertainty next. A G1 with no vehicle skips the entire vehicle-history and claims-history branches in one move.
- **Fact-lock:** hash every material fact at session start. Divergent submissions denied by `P-FACT-01`. This is the direct answer to data-quality concerns and should be demonstrated early in the walkthrough.
- **Vault:** encrypted at rest, injected only into the destination that needs it, never returned raw, never in prompts or traces.
- **Field Passport UI:** before submission, show exactly which fields go to which route, with per-field veto and a consent receipt.

### 9.3 Market Registry + Rate-Source Graph

Nodes: `legal_underwriter`, `insurer_group`, `consumer_brand`, `distributor`, `program`.
Edges: `underwrites`, `distributes`, `owns`, `same_rate_source_as`.
**Every edge carries evidence.** Unevidenced edges are hypotheses and render dashed.

Seed from the brief's Appendix A: 32 groups, 60 legal entities. Discovery seed only. Every row requires current validation and a `last_verified_at`.

**Fingerprinting.** Assert `same_rate_source_as` only when at least two independent signals agree:

1. Legal underwriter named on the quote or disclosure page
2. Quote reference ID grammar
3. Returned endorsement and form set, hashed
4. Identical premium at identical inputs across two brands

Record `signals_agreeing`. Never assert on one signal.

### 9.4 Route Planner

Selects one channel per rate source, orders the queue, enforces budgets, respects the active profile's module gating.

Priority inputs: rate filing delta, expected information gain (does this route resolve a dedup hypothesis?), channel cost in operator attention, eligibility prior from prior reason codes.

**Bounded-attempt policy, non-negotiable:**

| Channel | Budget |
| --- | --- |
| Web | 1 attempt + 1 retry, transient technical errors only. Never retry a rejection, CAPTCHA or terms restriction. |
| Outbound voice | 1 call in published sales hours + 1 retry only on pre-connection failure |
| Callback | Wait the declared window, then `callback_required` or `unreachable` with timestamps |
| Broker | Ask once for the complete carrier list and all obtained quote outcomes |

### 9.5 Evidence Chain

Content-addressed by `sha256` of redacted bytes. Hash-chained, append-only. **Redact before write; there is no raw-then-clean path.** `verify_chain()` recomputes and reports the first divergence. Exposed via `fathom-evidence` so a judge can verify any single row live.

### 9.6 Redactor (local)

Runs entirely on the operator's machine.

1. **Text:** pattern plus NER for licence numbers, full postal codes, street addresses, VINs, dates of birth, phone numbers, email.
2. **Vision:** a small local model masks the same categories inside screenshots before storage.

Nothing unredacted reaches any cloud API.

### 9.7 Normalizer + Parity Solver

Answers the question no comparison output answers: **what does this cost at equal coverage?**

- **Measured:** a real delta from the Benefit Price Probe. `parity_confidence: measured`.
- **Partial:** some items measured, others unavailable. List exactly which could not be priced.
- **Not possible:** the route cannot offer the item at all.

**Never invent a number to fill a parity gap.** The UI never shows a price without its parity band, and never labels the lowest number "best."

---

## 10. Tier 2: the signature work

### 10.1 The Rulebook Compiler

Takes a publicly published insurance rate manual and produces an executable premium calculator.

**Why it is extraordinary:** the residual market must take anyone, and publishes its full Ontario manual. So the one price guaranteed to be available to a G1 with no history can be *computed* rather than requested.

1. Ingest the current public manual. Record version, effective date, source URL.
2. Structured extraction: rating tables, territories, driver class rules, coverage rate pages, endorsement charges, surcharges, discounts.
3. LLM-assisted compilation into a deterministic Python rater. **The LLM writes the code once. The shipped rater is plain arithmetic. No model call at runtime.**
4. **Self-verification loop:** generate test cases from the manual's own tables and worked examples, run the rater, compare, iterate. Report the pass rate.
5. Emit a `COMPUTED` result with manual version, effective date, source URL, the exact rating path taken, and the verification pass rate.

**Honesty:** labelled `COMPUTED` everywhere, never mixed into the retrieved band, and the submission states plainly that real placement requires a licensed intermediary.

### 10.2 The Benefit Price Probe

*Gated on Day 0 Plan A for the operator profile. Under Plan B it runs in the sandbox under `sim_g2_no_car`, clearly labelled.*

Measures the real dollar cost of each newly-optional accident benefit, per insurer. Ontario made most accident benefits optional on 1 July 2026. Nobody has a per-carrier price curve, because nobody has measured one.

1. Reach a priced state on a route exposing coverage toggles.
2. Record baseline.
3. Toggle exactly one optional benefit. Re-price. Record the delta.
4. Restore. Repeat within the attempt budget.

**Boundaries, enforced:**
- Only **coverage choices** vary: benefits, limits, deductibles, endorsements. These are elections.
- **Facts are fact-locked and immutable.** Age, address, licence class, mileage, vehicle. Varying a fact to chase a lower price is prohibited and blocked by `P-FACT-01`.
- Respect rate limits. If the flow strains, stop and record partial curves.

Output: `out/benefit_price_curves.json`. Call this out in the submission as a novel dataset.

### 10.3 The Eligibility Frontier

Turns every decline into a forward path.

1. Every non-quoted result captures the stated reason, redacted, plus a `ReasonCode`.
2. Map each code to `unlock_conditions`.
3. For each candidate condition, count the distinct rate sources whose codes it would satisfy.
4. Render as an ordered ladder.

> Of 31 verified applicable rate sources: 3 reachable today, 28 closed.
> Obtaining a G2 opens 9. Owning the vehicle opens 7. Twelve months of Canadian history opens 4.
> Six remain closed regardless of any change the operator can make.

**Every count clicks through to the declines that produced it.** No modelling. Pure inversion of evidence.

### 10.4 The Vehicle Inversion Engine

Answers "which car should I buy" instead of "what does my car cost."

1. Ingest public vehicle-risk rankings for popular Canadian vehicles. State clearly that full industry rating group tables are not public and only published rankings are used.
2. Select a realistic candidate set for a first vehicle.
3. Where a route allows re-pricing with a different prospective vehicle, **measure** the difference. Measured beats inferred everywhere.
4. Cross rankings with measured premiums into a ranked shopping list with per-row confidence.

**Honesty:** rankings are an informational tool, not a rating system. Label inferred rows as inferred. Never present a ranking as a premium.

### 10.5 The Rate Filing Radar

The regulator publishes approved rate changes for every Ontario auto insurer. Ingest the latest published set, map each entity to `insurer_group` and `distinct_rate_source_id`, feed the delta into planner priority.

Small build, large impression. The planner looks like it knows something, because it does.

### 10.6 The Channel Arbitrage Detector

Once fingerprinting proves brand A and brokerage B share a `distinct_rate_source_id`, compare premiums returned through each channel at identical coverage and fact-lock, with close timestamps.

If they differ, that is the most interesting finding available, and it falls out of dedup work already required.

**Report the observation with both artifacts. State plainly that channel differences can have legitimate causes such as different programs, panels or commission structures. Do not allege wrongdoing.**

### 10.7 The Friction Ledger

Records every stall, dead end, forced bundle, unanswered callback and abandoned journey with a timestamp and a redacted artifact.

**Framing rule, mandatory:** the ledger reports **friction observed**, with timestamps and evidence. It names no rule as breached, alleges no violation, and accuses no company. The operator is not a regulator. The data speaks; the operator does not editorialize.

### 10.8 The Broker Disclosure Harvester

Ontario law requires a broker to provide an applicant with the names of every insurer with whom the broker holds an automobile broker contract, and all quote information obtained for that applicant. Ontario guidance also requires written confirmation following a telephone quote discussion.

So the voice and email executors always ask two things:

1. "Could you provide the complete list of automobile insurers you hold contracts with?"
2. "Could you send written confirmation of this discussion by email?"

One request can populate 20 or more registry rows with a citable source, and the written confirmation arrives as a hard evidence artifact from a licensed professional.

**Ask once per broker. Never pester. Record the response verbatim, redacted.**

---

## 11. Tier 3: the engineering

### 11.1 Self-Healing Route Recipes

- **First run:** map the site the slow way via accessibility tree plus vision, mapping each question to the canonical schema.
- **Save:** store the successful path as a deterministic recipe with field mappings, waits and assertions.
- **Later runs:** replay. No model calls. Seconds instead of minutes.
- **Drift:** an assertion fails. Re-derive the mapping from the current page, patch the recipe, record a healing event with a before/after diff, continue.

**Demo:** run the same route twice. Four minutes, then twenty seconds. Then break a selector deliberately and watch it repair.

### 11.2 Twin Readers

Two independent extractions of every priced result: one from the structured page representation, one from a vision model reading the screenshot. Agreement sets `confidence_indicator: high`. Disagreement preserves both readings and flags the conflict.

### 11.3 Injection-Resistant Reading

Insurer pages are untrusted input.

- The Planner never receives raw page text.
- A sandboxed Reader extracts only typed, schema-conforming fields with provenance tags, and discards free text.
- Instruction-shaped content is logged as an injection incident and never reaches the Planner.
- The Policy Engine is the backstop: even a fully compromised planner cannot bind, pay or sign.

**Demo:** a local test page carrying an injection payload. Show the incident log and the unchanged plan. Never tamper with a real site.

### 11.4 The Dark Pattern Detector

Flags manipulation patterns in quote journeys: pre-ticked optional add-ons, forced bundling before a price is shown, price changes after contact capture, artificial urgency, fields marked required that are not, and dead ends that only offer a callback.

Feeds the Friction Ledger. Report the observation with the artifact. Do not allege intent.

### 11.5 The Synthetic Insurer Sandbox

Five locally hosted fake insurer sites so real destinations are touched only when necessary:

| Site | Behaviour |
| --- | --- |
| `sandbox-alpha` | Clean flow, returns a price |
| `sandbox-bravo` | CAPTCHA at step 3 |
| `sandbox-charlie` | Never prices, only offers a callback |
| `sandbox-delta` | Intermittent failure, DOM changes between runs |
| `sandbox-echo` | Hidden prompt-injection payload |

This is where reliability numbers come from, and it demonstrates discipline: not hammering live insurer infrastructure to debug a selector.

### 11.6 The Inbound Callback Catcher

A callback arrives. The system answers, delivers the inbound disclosure, identifies the company and the open file, loads preserved context including any quote reference ID and consent state, and resumes the same journey.

### 11.7 The Voice Executor

**Consent state machine:** `UNKNOWN` to `AUTOMATION_DISCLOSED` to `PROCEED_GRANTED` or `HUMAN_REQUESTED`. Parallel `RECORDING: NO_AUDIO` to `GRANTED` or `REFUSED`. The recorder is physically gated on `GRANTED`. Default `NO_AUDIO`.

**Outbound opening:** identify as an automated assistant acting for the operator by legal name, state the purpose, ask whether it is acceptable to continue with an automated assistant, note the operator is available for verification or consent.

**Inbound opening:** thank the caller, identify as an automated assistant receiving the call for the operator by legal name, ask whether to continue or hand to the operator.

**Live escalation:** stop mid-turn and hand to the operator the instant a representative asks for consent, identity verification, a declaration, authorization to pull third-party records, or requests coverage advice.

**Context handoff:** pass any quote reference ID, source URL, partial progress and consent state so the representative continues the same file. Record whether the handoff returned a rate, an eligibility answer, or an exact blocker.

**Never:** spoof caller ID, claim affiliation with the organizer or an insurer, pressure a representative, place repeated calls, continue after a request to stop. If asked about the prototype, answer truthfully and offer to transfer to the operator.

**On refused recording consent:** retain only a structured, non-audio outcome note.

### 11.8 Ask Your Own Findings

A retrieval layer over FATHOM's own verified evidence. Natural-language questions answered only from collected artifacts, every answer citing registry rows and evidence CIDs. Never from model memory.

### 11.9 The Honest Scorecard

FATHOM reports its own error rate: extraction accuracy against a manually verified sample, twin-reader agreement rate, route success rate per channel from sandbox runs, rater verification pass rate, healing events per hundred runs.

Plus the five required coverage metrics with denominators visible:

- Market completion = evidenced terminal statuses ÷ verified applicable rate sources
- Comparable quote yield = `quoted_comparable` ÷ verified applicable rate sources
- Evidence rate = outcomes with valid source, timestamp and redacted artifact ÷ all outcomes
- Duplicate suppression = brands mapped to an existing `distinct_rate_source_id` ÷ total brands
- Freshness = registry records verified in the hackathon window ÷ total records

**Unresolved records stay in every denominator.**

### 11.10 Live Narration Mode

Streams every decision as it is made: planner reasoning, policy verdicts with the rule ID that fired, evidence writes with chain index, healing events, injection incidents.

Judges do not watch a spinner. They watch the system think, and they watch it get stopped.

---

## 12. The UI

Seven views. Clean and plain. Nobody scores the CSS.

1. **Intake + Field Passport.** Which fields go where, per route, per-field veto, consent receipt.
2. **Live Run.** Narration. Route queue, current action, policy verdicts, evidence chain growing.
3. **Results.** Sortable by annual cost, but **coverage differences render above price differences**. Every row shows its PASS / CAUTION / FAIL verdict, reason codes, confidence indicator and evidence status. Estimates and computed results in separate bands. The lowest number is never labelled "best." Every row opens its evidence.
4. **Market Graph.** Brands collapsing into rate sources. Edge evidence on click. Dashed edges for hypotheses.
5. **Eligibility Frontier.** The unlock ladder, each count clicking through to its declines.
6. **Profile Switcher.** Flip between `operator` and the sandbox profiles and watch the planner light up different routes and modules. **Every simulated profile carries a persistent visible SIMULATION banner.**
7. **Scorecard + Friction Ledger.** Metrics with visible denominators, plus the timestamped record of every stall and dead end.

---

## 13. Tech stack

| Layer | Choice | Why |
| --- | --- | --- |
| Core | Python 3.12 | Operator's primary language; best fit for rater, graph, extraction |
| Orchestration | LangGraph | Consent and route flows are literally state machines |
| MCP | FastMCP | Seven servers; operator holds MCP certification |
| Browser | Playwright + vision fallback | Recipes replay on Playwright; vision handles drift and reads prices |
| Voice | Programmable telephony + realtime speech model | Low latency matters for clean escalation |
| Storage | SQLite + content-addressed blob store | Portable, verifiable, no infra to explain |
| Graph | NetworkX in memory, persisted as JSON | The graph is small. Do not introduce a graph database. |
| Redaction | Local NER + small local vision model | Runs on operator hardware; nothing unredacted leaves |
| Tracing | Langfuse | Prior experience; traces PII-free by construction |
| API | FastAPI | Thin. The UI is a client of the MCP layer. |
| Frontend | React + Vite | Seven views, minimal styling |
| Tests | pytest + synthetic sandbox | Reliability numbers come from here |

---

## 14. Build order

**Do not reorder. Do not skip ahead.**

*Amended 2026-08-09 following AC-001. Automation is the ask, not a bonus, and form coverage is a
graded outcome — so the web executor, route recipes and the field ontology mapper move up.*

**The constraint that does not move:** evidence discipline is never traded for form count. The
written brief's judging criteria are unchanged and still reward trustworthy over numerous. A
schema-valid result with an evidence artifact counts; a number scraped without one does not.

### Milestone 0: Day 0 Reconnaissance Probe
Run Section 5 by hand. Write `docs/DAY0_PROBE.md`. **Plan A applies** — this is reconnaissance for
the web executor, not plan selection.

### Milestone 1: the contract
Repo scaffold, LICENSE with personal-use statement, README stating scope, `docs/PRIME_DIRECTIVES.md`, CI check that greps for PII patterns and fails the build on a hit.

### Milestone 2: the gate
Policy Engine with every rule in 9.1. Hash-chained audit log with `verify_chain()`. Unit tests proving each rule denies what it must.
**Checkpoint: demonstrate a denied bind attempt before any browser exists.**

### Milestone 3: the spine
Profile registry. Vault, fact-lock, adaptive intake, Field Passport. Evidence chain plus redactor. Registry seeded from Appendix A, every row unverified.
**Checkpoint: an evidence artifact can be written, redacted and verified.**

### Milestone 4: first blood, then reach
Web executor against `sandbox-alpha`. Then one real route to a real terminal status. Normalizer
producing a schema-valid result with an assessment verdict.
**Then immediately: the field ontology mapper and route recipes (§11.1), and breadth across the
four probed routes under `profile_hypo_clean`.** Form coverage is graded, and every route completed
here is a recipe the later milestones replay for free.
**Checkpoint: minimum demo acceptance is met. Everything after is upside.**

### Milestone 5: the signature
Rulebook Compiler with self-verification. **Highest-value single item. Give it real time.**
Then Benefit Price Probe and Parity Solver, live under `profile_hypo_clean` (Plan A applies).

### Milestone 6: the market
Fingerprinting and dedup. Rate Filing Radar into the planner. Broker Disclosure Harvester by email, then voice. Eligibility Frontier solver.

### Milestone 7: the engineering
Route recipes and self-healing. Twin readers. Full sandbox, all five sites. Injection defense plus the incident demo. Dark pattern detector.

### Milestone 8: the voice
Outbound with disclosure and consent state machine. Live escalation. Written-confirmation and carrier-list asks. Inbound callback catcher if time allows.

### Milestone 9: the submission
Vehicle Inversion. Channel Arbitrage. Honest Scorecard. Live Narration. Profile Switcher. All deliverables in Section 15.

---

## 15. Deliverables

| Deliverable | Location |
| --- | --- |
| GitHub repository plus setup instructions | `README.md` |
| Three to five minute walkthrough | Section 16 script |
| Machine-readable market registry | `out/registry.json` and `out/registry.csv` |
| Redacted run report | `out/run_report.md` |
| Architecture and safety note | `docs/ARCHITECTURE.md`, `docs/SAFETY.md` |
| Known limitations | `docs/LIMITATIONS.md` |
| Day 0 probe record | `docs/DAY0_PROBE.md` |
| Benefit price curves | `out/benefit_price_curves.json` |

### 15.1 Minimum acceptance, verify before submitting

- [ ] At least one permitted route reaches a returned rate or an exact terminal blocker
- [ ] A cross-channel handoff preserving context and disclosing automation, where the journey requires it
- [ ] At least two outcomes in the common schema showing coverage differences
- [ ] Registry distinguishes legal underwriter, group, brand, distributor and rate source
- [ ] Every demonstrated outcome has a timestamp and redacted evidence
- [ ] No real licence number, full address, payment data or unredacted call recording anywhere
- [ ] No route used a fabricated licence number
- [ ] Every hypothetical profile visibly labelled everywhere it appears, and never paired with a licence number, a real human, or an identity, consent, declaration or purchase step
- [ ] Every `sandbox_only` profile visibly labelled, and none touched a real destination
- [ ] Final PII sweep across repo, `out/`, screenshots and the Loom recording

### 15.2 Known limitations, write these honestly

The operator holds a G1 and owns no vehicle, so most standard retail routes correctly return ineligible. The `COMPUTED` result is a calculation from a public manual, not a quote from an insurer, and real placement requires a licensed intermediary. Panel membership changes constantly, which is why every registry row carries a verification timestamp. Some rate sources remain unresolved and are reported as such rather than dropped. Simulated profiles were used only in the local sandbox and never sent to a real destination.

---

## 16. The walkthrough script

Three to five minutes. **Open with strength. Place the adaptation late, as design rather than apology.**

1. **(20s) The premise, stated with confidence.**
   "I hold a G1 and own no car. That is the hardest profile in the Ontario market, so I built a system to measure that market rather than shop it."
2. **(25s) Data trustworthiness first.** Fact-lock. Every material fact hashed at session start; nothing can drift between insurers. Show the hash and the denial that fires if it would.
3. **(40s) The computed price.** The Rulebook Compiler produces the guaranteed-market premium offline, with manual version, rating path and verification pass rate against the manual's own examples. No website, no human, no waiting.
4. **(40s) The market graph.** N brands collapse into M rate sources. Click an edge, see the evidence and how many signals agreed.
5. **(30s) The parity moment.** Two results. One looks cheaper. At equal coverage it is not, and the adjustment was measured. Show the benefit price curve.
6. **(30s) The gate.** The agent proposes submitting an application. The Policy Engine denies it. Rule ID and audit chain index on screen.
7. **(25s) The injection test.** A hostile local page. Incident logged, plan unchanged.
8. **(40s) The frontier.** The unlock ladder. Click a count, drop into the declines that produced it.
9. **(20s) The profile switcher.** "The system is profile-adaptive. My profile routes here. A G2 with no car routes here. A G-class owner routes here. Same architecture, different active modules." Simulation banner visible throughout.
10. **(20s) The scorecard.** Metrics with visible denominators, plus FATHOM's own measured error rate.
11. **(10s) Close.** "A smaller number of trustworthy results with excellent evidence. Both the reach and the uncertainty are legible."

### 16.1 Prepared answers

**"What would you build with more time?"**
> "More verified rate sources. Reach, not features. The architecture is done; the market map is what is incomplete, and I would rather tell you that than pad the count."

**"Why so few quotes?"**
> "Because I am a G1 with no vehicle, and most standard markets correctly decline that risk. Every one of those declines is recorded with its reason and its evidence. That is the measurement."

**"How do we know these numbers are real?"**
> "Pick any row. It opens its evidence: timestamp, source, redacted artifact, and its position in a hash chain you can verify live. The one price I calculated rather than retrieved is labelled `computed` and carries the manual version it came from."

**"Isn't this just a comparison site?"**
> "A comparison output is bounded by its live panel and by what the applicant qualifies for. FATHOM measures that boundary and proves where it sits. It is an instrument, not a storefront."

---

## 17. Repo layout

```
fathom/
├── README.md
├── LICENSE                        # personal use only
├── docs/
│   ├── PRIME_DIRECTIVES.md
│   ├── DAY0_PROBE.md
│   ├── ARCHITECTURE.md
│   ├── SAFETY.md
│   ├── LIMITATIONS.md
│   └── OPEN_QUESTIONS.md
├── packages/
│   ├── policy/                    # deterministic gate + audit chain
│   ├── profiles/                  # profile registry, module gating
│   ├── vault/                     # encrypted store, fact-lock, field injection
│   ├── intake/                    # adaptive questioning, field passport, consent
│   ├── registry/                  # market registry, graph, fingerprinting
│   ├── planner/                   # route selection, priority, budgets
│   ├── executors/
│   │   ├── web/                   # playwright + vision, recipes, healing
│   │   ├── voice/                 # consent state machine, escalation, handoff
│   │   └── broker/                # email + written-confirmation harvesting
│   ├── rater/                     # rulebook compiler + generated rater + tests
│   ├── evidence/                  # content-addressed store, hash chain, verify
│   ├── redactor/                  # local text + vision redaction
│   ├── normalizer/                # schema mapping, assessment, parity solver
│   ├── analysis/                  # frontier, vehicle inversion, arbitrage, dark patterns
│   └── mcp/                       # the seven MCP servers
├── sandbox/                       # five synthetic insurer sites
├── ui/                            # seven views
├── tests/
├── out/
└── data/
    ├── profiles/
    ├── seed/                      # Appendix A regulatory seed
    └── public/                    # rate filing deltas, vehicle rankings, manual extracts
```

---

## 18. Anti-goals

- Building a pretty dashboard before the evidence chain works
- Counting brands as rate sources
- Presenting an estimate, lead form or callback promise as a quote
- Silently dropping unresolved sources from the denominator
- Alleging that any company broke a law or rule. Report friction. Never editorialize.
- Framing the project as a criticism of comparison platforms, or omitting one from the registry
- Retrying a rejection, CAPTCHA or terms restriction
- Calling a representative more than the budget allows
- Hammering live insurer sites during development instead of using the sandbox
- Letting an LLM compute a premium at runtime. It writes the rater once; the shipped rater is arithmetic.
- Sending a `sandbox_only` profile to a real destination, for any reason
- Pairing a hypothetical profile with a licence number, a real human, or an identity, consent, declaration or purchase step
- Presenting a rate retrieved for a hypothetical driver as a rate for the operator, or the reverse
- Trading evidence discipline for form count
- Any raw PII near a prompt, trace, screenshot, log or the repo
- Filling a parity gap with an invented number
- Opening the walkthrough with what could not be done

---

## 19. Glossary

| Term | Meaning |
| --- | --- |
| Legal underwriter | The licensed company named on the policy or rate filing |
| Insurer group | The parent that may contain several legal underwriters |
| Consumer brand | The name the applicant sees |
| Distributor | Direct writer, exclusive agent, independent broker or digital brokerage |
| Aggregator | Comparison or lead platform; only as broad as its live panel |
| MGA or program | Administrator with delegated authority; not automatically a distinct rate source |
| Residual market | Market of last resort, accessed through a licensed intermediary |
| Distinct rate source | The deduplicated unit FATHOM actually counts |
| Fact-lock | Session hash of every material fact; prevents drift across routes |
| Parity | A premium restated at the benchmark coverage package |
| Frontier | The ordered set of changes that unlock closed rate sources |
| Reason code | The structured cause of a non-quoted outcome |

---

## 20. Closing note for the operator

FATHOM is not trying to produce the most quotes. It is trying to produce the most trustworthy account of a fragmented market, from the position of the person that market serves worst.

Two retrieved results, one computed guaranteed price, twenty-eight evidenced declines, and a ladder showing exactly what unlocks what, is a stronger submission than fifty unverified numbers.

Build the gate first. Everything else is downstream of being able to prove you never crossed a line.