# Day 0 Reconnaissance Probe

> **Purpose amended 2026-08-09** following the organizer Q&A (AC-001), amendment D-005.
> **Plan A applies** — this probe no longer selects a build plan. It is reconnaissance that maps
> the four routes so the web executor is built against known ground.
>
> It now answers: which routes return a rate under `profile_hypo_clean`; which expose the
> post-1-July-2026 accident-benefit toggles; what each quote reference ID grammar is; and what the
> operator-profile outcomes are, since those feed the Eligibility Frontier.
>
> **This probe is not the submission's automation and never substitutes for it.** AC-001 item 2 is
> explicit that manual form filling is unacceptable and an agentic element is required. Everything
> learned here becomes a route recipe (§11.1) executed by the web executor.

**Status:** `CLOSED_PARTIAL` — closed 2026-08-09 by operator decision, one route walked of four
**Build plan:** `PLAN A` (fixed by AC-001; no longer selected by this probe)
**Routes walked:** Sonnet (`profile_hypo_clean` pass only)
**Routes deferred to the agent:** belairdirect, RBC Insurance, Desjardins — `reconnaissance_pending`
**Incident:** INC-001, resolved. See `docs/OPEN_QUESTIONS.md`.
**Operator:** Tarun Karnati, Toronto, Ontario
**Probe window:** _(start ISO 8601)_ → _(end ISO 8601)_

Governed by FATHOM §5. This document is itself submission evidence (§15, Deliverables). It is
written to be read by a judge, so it is redacted at the point of writing — there is no
raw-then-clean path here either.

---

## 0. Why this ran before the executor

*Rewritten 2026-08-09 under AC-001. The former plan-selection rationale is obsolete: **Plan A
applies**, and no probe outcome can change that.*

The probe exists to give the web executor known ground: the field taxonomy a real Ontario journey
demands, the step order it demands them in, the interruptions it throws mid-journey, and where a
hypothetical profile hits a wall. One route walked to a hard stop supplies all four. It is
reconnaissance, not retrieval.

---

## 1. Probe rules

These are binding for the probe itself, not just for the built system.

| Rule | Detail |
| --- | --- |
| **Manual only** | Hand-driven in an ordinary browser. No Playwright, no agent, no automation of any kind. §5.1. |
| **One profile per pass, no mixing** | *Added after INC-001.* A pass is run under exactly one profile. Every field comes from that profile. Populating a hypothetical profile with a real-world address, name, phone, email or licence — the operator's or anyone's — is prohibited. |
| **Real information only, under `profile_operator`** | The operator's own real, accurate data. G1, no owned vehicle, no Canadian history, no prior insurance. §2.2. |
| **Fully synthetic, under `profile_hypo_clean`** | *Added after INC-001.* Every field synthetic. No real-world identifier anywhere. No accuracy, truthfulness or fraud-acknowledgement checkbox ticked — emit `manual_handoff` and stop. |
| **One vehicle, genuinely considered** | The same prospective vehicle across all four routes, so the routes are comparable. Not a placeholder. |
| **Stop at the wall** | Record the exact stopping point. Do not work around it, do not retry a rejection, do not attempt a different licence class to "see what happens." |
| **Hard stop before commitment** | No payment, no e-signature, no application declaration, no bind. §2.1. |
| **No CAPTCHA bypass** | If a bot check appears, that *is* the result. Record it as the stopping point. §2.1. |
| **Redact at write time** | See §2 below. |
| **No characterization** | Record what the screen said, verbatim and redacted. No claim that any company breached anything. §2.1, §10.7. |

### 1.1 Account creation

Prefer journeys that price without an account. If a route requires an email or phone number to
continue, that is a recordable finding (contact-capture gate) — note it, and use the operator's real
contact details if continuing. Do not invent contact details.

---

## 2. Redaction rules for this document

Applied as you type, not afterwards.

| Field | Record as |
| --- | --- |
| Driver's licence number | **Never recorded. Not in any form, not partially.** |
| Date of birth | Birth year only |
| Home address | Forward sortation area only (first 3 characters of postal code, e.g. `M5V`) |
| Phone / email | `[REDACTED_CONTACT]` |
| Quote reference ID | Recorded — it is evidence, and it is not PII. Note its grammar (§9.3 fingerprinting signal 2). |
| Screenshots | **None taken this cycle.** Decided under OQ-004. |

**No screenshots for Day 0** (OQ-004, resolved 2026-08-09). The local vision redactor (§9.6) does
not exist until Milestone 3, §2.1 makes an unredacted screenshot a hard failure, and hand-redaction
is not a risk the operator is taking. Verbatim redacted quotes are the sole evidence form for this
probe, and they satisfy the evidence requirement on their own.

Nothing from this probe goes in `out/` yet.

---

## 2a. Two profiles per route

*Added 2026-08-09, amendment D-003/D-005.*

Each route is walked twice where the journey allows it. Record both in the route block.

| Pass | Profile | Conduct |
| --- | --- | --- |
| **A — primary** | `profile_hypo_clean` — clean-record hypothetical | **No licence number, ever. No plate.** Stop at any identity verification, consent attestation, declaration, callback enrolment or purchase step and record `manual_handoff`. **Never speak to a person under this profile.** |
| **B — second lens** | `profile_operator` — the operator's real G1, no vehicle | The operator's own real, accurate information (§2.2). Full human-contact permissions. Produces the refusals that feed the Eligibility Frontier. |

If a route only permits one pass within a sensible time budget, run **pass A** — it is the primary
retrieval surface — and note that pass B was not run.

---

## 3. The prospective vehicle

Fixed for all four routes.

| Field | Value |
| --- | --- |
| Year / Make / Model / Trim | **2019 Honda Civic LX** |
| Ownership status entered | Prospective purchase — not yet owned |
| Annual km | _(fill — enter the real intended figure, then record it here verbatim)_ |
| Primary use | _(fill: commute / pleasure — real intended use)_ |
| Why this vehicle | Genuinely considered first vehicle: high-volume Ontario used-market model, favourable published risk rankings, readily sourced. Selected by the operator 2026-08-09. |

Held constant across all four routes. If a route cannot accept this exact trim, select the nearest
available option and **record the substitution in the route's block** — do not silently vary the
vehicle, and do not vary it to chase a lower price (§10.2, `P-FACT-01`).

---

## 4. The four routes

Selected as **direct writers with a public self-serve Ontario auto quote journey**, which is what §5.1
asks for. Rationale: a direct writer is the shortest path to a priced screen, so if any channel
reaches a price for this profile, it is most likely one of these. A refusal here is also the
cleanest possible evidence, because there is no intermediary between the operator and the
underwriter's own eligibility rules.

| # | Brand | Entry point | Distribution | Notes |
| --- | --- | --- | --- | --- |
| 1 | Sonnet | https://www.sonnet.ca/auto-insurance/ontario | direct | Fully online quote-and-buy; the most likely route to reach a price without a human. |
| 2 | belairdirect | https://www.belairdirect.com/en/car-insurance/ontario.html | direct | Long-running Canadian direct writer with an online journey. |
| 3 | RBC Insurance | https://www.rbcinsurance.com/en-ca/auto-car-insurance/ontario-car-insurance/ | direct | Bank-owned direct writer; advertises an online-quote discount, so the journey is expected to price. |
| 4 | Desjardins | https://www.desjardins.com/en/insurance/auto.html | direct (exclusive agent) | Direct/exclusive-agent model; included for distribution diversity against the three above. |

Confirmed by the operator 2026-08-09 (OQ-002).

If a route above is unreachable or has materially changed, substitute the next unexcluded direct
writer and **record the substitution and the reason** in §6.

### 4.1 Deliberately excluded from Day 0 — carried to the Milestone 3 registry

Excluded because a membership gate returns `RC_MEMBERSHIP`, which would measure group eligibility
rather than plain retail eligibility and pollute the Plan A/B signal. None of these are being
dropped; each is a pending registry row, recorded here so the intent survives to Milestone 3.

| Brand | Pending `distribution_type` | Why excluded from Day 0 | Milestone 3 note |
| --- | --- | --- | --- |
| Onlia | `broker` | Not a direct writer. | Public sources describe it as a **RIBO-licensed brokerage**. Row requires a populated `licensed_intermediary` field with regulator evidence before it is trusted (OQ-003). **Flagged as an early Broker Disclosure Harvester target (§10.8)** — a brokerage row is worth more as a carrier-list source than as a quote route. |
| TD Insurance | `direct` (affinity-weighted) | Large share of Ontario volume is affinity/group; likely `RC_MEMBERSHIP`. | Standard registry row. Capture the affinity/group condition explicitly in `requirements`. |
| CAA Insurance | `affinity` | Membership-conditioned; a refusal would reflect membership, not licence class. | Standard registry row. `requirements` includes `membership`. |
| Aggregators / comparison platforms | `aggregator` | Day 0 is specifically about direct-writer journeys. | Run exactly like every other route, neutrally, at Milestone 4+ (§6.2). Omitting one would be the more serious error. |

---

## 5. Per-route record

Fill one block per route, in the order run. All four blocks are written out below — do not compress
them.

**On the two stopping fields.** They are deliberately separate and both are required:

- **Exact stopping step** — *where* the journey halted. The specific page, section and field, in
  `page → section → field` form. This is the mechanical location, and it is what makes the result
  reproducible.
- **Stated reason, verbatim, redacted** — *what the journey said*. Quoted exactly. If nothing was
  said, write `reason_not_stated` and let it stand; `RC_UNKNOWN` is a legitimate value and §8.2
  forbids guessing a reason to fill the field.

A route can halt with a precise stopping step and no stated reason at all. That is a complete,
usable record.

### Route 1 — Sonnet · pass A · `profile_hypo_clean`

**WALKED. Terminal status: `blocked`.**

| Field | Value |
| --- | --- |
| Profile | `profile_hypo_clean` (hypothetical, clean record) |
| Entry URL | https://www.sonnet.ca/auto-insurance/ontario |
| **Reached a priced screen?** | **NO** |
| **Exact stopping step** | `Driver details → Your Information → Driver's licence number` |
| Field characteristics at the stop | **Mandatory.** Marked case sensitive. Carries a "Why do we need this?" explanatory link. |
| Stated reason, verbatim, redacted | No refusal message was displayed. The journey did not decline the applicant — it required a value the profile cannot supply. Recorded as a structural block, not a decline. |
| **Terminal status** | `blocked` |
| **Reason code** | `RC_HYPO_LICENCE_REQUIRED` *(new — see §7.2)* |
| Why blocked | A hypothetical profile cannot supply a driver's licence number under `P-HYPO-LICENCE-01`, and the field cannot be skipped. |
| Was G1 selectable as licence class? | Not reached — the number is demanded at the same step |
| Did it demand a licence number to proceed? | **YES** — `Driver details → Your Information` |
| **Exposed AB election toggles?** | `NOT_REACHED` |
| Coverage toggles visible before pricing? | `NOT_REACHED` |
| CAPTCHA / bot check encountered? | NO, up to the stopping step |
| Contact capture required before price? | Not reached |
| **Quote reference ID + grammar** | **None issued before the block.** No reference ID exists for this route yet. |
| Vehicle substitution | `NONE` — 2019 Honda Civic LX accepted |
| Evidence captured | `verbatim_only` (OQ-004) |

#### 1.1 Journey order observed

The step sequence, which becomes the route recipe skeleton (§11.1):

```
Province → Get started → Vehicles → Driver details → Other drivers → Assign drivers
```

The licence-number wall sits at step 4 of 6. Everything before it is reachable by a hypothetical
profile, which means the vehicle and coverage taxonomy on this route is harvestable even though the
price is not.

#### 1.2 automation_notes — carried to the registry row and the executor

| Observation | Consequence for the executor |
| --- | --- |
| **Address-validation modal on the Vehicles step.** Text begins "Heads up!", references a "mixed use residence", offers `Cancel` / `Okay`. | **A naive executor hangs here.** Modals are a first-class executor case, not an exception path (§11.1, operator constraint 1). Log every modal encountered with its text. |
| **Fraud-acknowledgement checkbox on the Vehicles step**, tied to address accuracy. | Denied under a hypothetical profile by `P-HYPO-ATTEST-01`. Emit `manual_handoff`, do not tick, do not work around. |
| Licence-number field is mandatory and case sensitive | Structural block for `profile_hypo_clean`. The `profile_operator` pass may pass this step, which is why pass B is still worth running by the agent. |

#### 1.3 What this route still owes

- **Pass B (`profile_operator`) not run.** Deferred to the agent. The operator holds a real G1 and
  can supply a real licence number, so this route may reach further under that profile — and its
  refusal, wherever it lands, is a Frontier row.

---

### Route 2 — belairdirect

**`reconnaissance_pending`** — deferred to the agent, under supervision, with the gate live.

Not walked by hand. This is a deliberate deferral under the §7.3 decision, **not** an unresolved
route and **not** a failure. It carries no terminal status because no attempt has been made; it
enters the registry as a route awaiting its first agentic attempt.

---

### Route 3 — RBC Insurance

**`reconnaissance_pending`** — deferred to the agent, under supervision, with the gate live.

---

### Route 4 — Desjardins

**`reconnaissance_pending`** — deferred to the agent, under supervision, with the gate live.

---
## 6. Substitutions and deviations

| Route replaced | Replaced with | Reason | Timestamp |
| --- | --- | --- | --- |

---

## 7. Result

| Measure | Value | Denominator note |
| --- | --- | --- |
| Routes walked by hand | **1** of 4 | Sonnet, `profile_hypo_clean` pass only |
| Routes reaching a priced screen | **0** of 1 walked | Not 0 of 4 — three routes were never attempted |
| Routes blocked at a mandatory licence-number field | **1** of 1 walked | Sonnet |
| Routes exposing AB election toggles | **0** of 1 walked | Never reached on the only route walked |
| Quote reference IDs obtained | **0** | None issued before the block |
| Routes `reconnaissance_pending` | **3** | belairdirect, RBC, Desjardins |

**`reconnaissance_pending` is not `unresolved`.** An unresolved route is one FATHOM attempted and
could not resolve, and §2.2 keeps those in every denominator. These three were never attempted.
They are pending work, and they are reported as pending rather than folded into a failure count
they did not earn. When the agent walks them, whatever comes back — including `unresolved` — enters
the denominators properly.

### 7.1 Findings (§5.1 as amended)

| Question | Answer |
| --- | --- |
| **1. Which routes returned a rate under `profile_hypo_clean`?** | None of the one walked. Sonnet blocks at a mandatory, case-sensitive driver's licence number field on `Driver details → Your Information`, which a hypothetical profile cannot supply under `P-HYPO-LICENCE-01`. |
| **2. Which exposed the post-1-Jul-2026 AB election toggles?** | Unknown. Sonnet's block sits at step 4 of 6, before any coverage screen. §10.2 gating stays open for all four routes. |
| **3. Quote reference ID grammar, per route** | None obtained. Sonnet issues no reference before the block. Fingerprinting signal 2 (§9.3) has no data yet, so dedup will lean on signals 1, 3 and 4 until the agent runs. |
| **4. Operator-profile outcomes** | Not run. Pass B was deferred with the other routes. The Eligibility Frontier has no rows from Day 0. |

**Summary.** One route was walked and it produced a hard structural result rather than a price: the
Sonnet journey demands a driver's licence number, mandatory and case sensitive, at
`Driver details → Your Information`, four steps into a six-step flow, and that field cannot be
skipped. Under `profile_hypo_clean` that is a terminal `blocked`, not a decline — the journey never
assessed the applicant, it required a value the profile is forbidden to hold. The walk also yielded
the three things the executor actually needed: the step order
(`Province → Get started → Vehicles → Driver details → Other drivers → Assign drivers`), a
mid-journey address-validation modal that will hang a naive executor, and a fraud-acknowledgement
checkbox tied to address accuracy. Probing was closed here by operator decision (§7.3) after
INC-001. Three routes remain `reconnaissance_pending` and will be walked by the agent under
supervision with the gate live.

### 7.2 New reason code

`RC_HYPO_LICENCE_REQUIRED` — *"a mandatory driver's licence number field cannot be satisfied by a
hypothetical profile"*. Added to the §8.2 taxonomy.

It is distinct from `RC_LICENCE_CLASS`, which means the market declined the applicant's licence
class. This code means the market never assessed the applicant at all: the journey demanded a
credential the profile is prohibited from holding. Its unlock is `run_under_operator_profile`, not
`obtain_g2` — which is exactly the kind of distinction the Eligibility Frontier exists to keep
straight, and folding the two together would put a false row on the unlock ladder.

### 7.3 Decision — manual probing ends here

**Decided by the operator 2026-08-09. Three routes deferred to the agent.**

Recorded because a partially-run probe needs its reasoning attached, or it reads later as an
abandonment:

1. **AC-001 items 2 and 4 are explicit** that manual form filling is not what is being judged and
   that an agentic element is required. Hand-walking three more journeys spends hours on work that
   does not count toward the submission.
2. **It repeats the exposure that produced INC-001.** Every additional hand-run pass is another
   opportunity for profile bleed, and the gate cannot protect a journey it is not in.
3. **Sonnet already yielded what the executor needed** — field taxonomy, journey order, a known
   mid-journey modal, and one confirmed terminal status.

belairdirect, RBC Insurance and Desjardins are walked by the agent, **under supervision, with the
gate live, and with the full intended payload approved field-by-field before any real destination is
touched** (operator constraint 2, enforced by `P-APPROVAL-01`).

### 7.4 Carry-forward

| Destination | Carried |
| --- | --- |
| **Milestone 3 — registry** | Sonnet row: `distribution_type: direct`, `status: blocked`, `reason_code: RC_HYPO_LICENCE_REQUIRED`, with the journey order and both `automation_notes` observations. Three rows created as `reconnaissance_pending`. |
| **Milestone 3 — profiles** | `profile_hypo_clean` must carry a synthetic value for every field this journey demands, and must be *unable* to carry a licence number. Per-field provenance is required so `P-PROFILE-BLEED-01` has something to read. |
| **Milestone 4 — executor** | **Modals are a first-class case.** The Sonnet address-validation modal is the proof. Log every modal encountered, with its text. |
| **Milestone 4 — executor** | Fraud/accuracy acknowledgement checkboxes are denied under a hypothetical profile (`P-HYPO-ATTEST-01`) → `manual_handoff`. |
| **§8.2 taxonomy** | `RC_HYPO_LICENCE_REQUIRED` added. |
| **§10.2 gating** | Undetermined for all four routes. No AB toggle was reached. |
| **§9.3 fingerprinting** | Signal 2 (reference ID grammar) has no data. Dedup leans on signals 1, 3 and 4 until the agent runs. |
| **§10.7 Friction Ledger** | Sonnet: mandatory case-sensitive licence field at step 4 of 6; mid-journey address-validation modal. Observations only, no characterization. |

---

## 8. What counts as a complete probe

*Rewritten 2026-08-09; the former "Plan B is not a downgrade" section is obsolete under AC-001.*

A complete Day 0 is **four routes mapped**, not four rates returned. Under `profile_hypo_clean` a
returned rate is the expected outcome and sizes the retrieval surface. Under `profile_operator` a
clean refusal with an exact stopping step and a stated reason is exactly as useful — it is a row in
the Eligibility Frontier.

A route that stops at an identity, consent, declaration, callback-enrolment or purchase step under
the hypothetical profile is **`manual_handoff`, correctly recorded**. That is `P-HYPO-STEP-01`
doing its job, not a route that failed.
