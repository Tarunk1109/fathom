# Day 0 Viability Probe

**Status:** `NOT_YET_RUN`
**Selected plan:** `PENDING` (Plan A / Plan B — do not fill until all four routes are recorded)
**Operator:** Tarun Karnati, Toronto, Ontario
**Probe window:** _(start ISO 8601)_ → _(end ISO 8601)_

Governed by FATHOM §5. This document is itself submission evidence (§15, Deliverables). It is
written to be read by a judge, so it is redacted at the point of writing — there is no
raw-then-clean path here either.

---

## 0. Why this runs before any code

§5 selects the build plan. Under **Plan A** the Benefit Price Probe, measured parity, vehicle
inversion and channel arbitrage are live for the `operator` profile. Under **Plan B** those four
modules run only in the sandbox under `sim_g2_no_car`, and weight shifts to the Rulebook Compiler,
the Rate-Source Graph, the Eligibility Frontier and the Broker Harvester.

Guessing this wrong costs days. §5.3: *do not discover Plan B on day three.*

---

## 1. Probe rules

These are binding for the probe itself, not just for the built system.

| Rule | Detail |
| --- | --- |
| **Manual only** | Hand-driven in an ordinary browser. No Playwright, no agent, no automation of any kind. §5.1. |
| **Real information only** | The operator's own real, accurate data. G1, no owned vehicle, no Canadian history, no prior insurance. §2.2. |
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

### Route 1 — Sonnet

| Field | Value |
| --- | --- |
| Started at (ISO 8601, ET) | |
| Ended at (ISO 8601, ET) | |
| Entry URL | |
| **Reached a priced screen?** | `YES` / `NO` |
| **Exact stopping step** (`page → section → field`) | _(e.g. `Driver details → Licence information → Licence class selector`)_ |
| Stated reason, verbatim, redacted | _(quote exactly; `reason_not_stated` if none — never guess, §8.2)_ |
| Proposed `TerminalStatus` | _(§8.1)_ |
| Proposed `ReasonCode` | _(§8.2)_ |
| Was G1 selectable as licence class? | `YES` / `NO` / `N/A` |
| Was "do not yet own the vehicle" expressible? | `YES` / `NO` / how it was expressed |
| Did it demand a licence number to proceed? | `YES` / `NO` — at which step |
| **Exposed AB election toggles?** (post-1 Jul 2026 optional benefits) | `YES` / `NO` / `NOT_REACHED` |
| Coverage toggles visible before pricing? | `YES` / `NO` |
| CAPTCHA / bot check encountered? | `YES` / `NO` — at which step |
| Contact capture required before price? | `YES` / `NO` |
| Friction observed (§10.7 — observations only, no characterization) | |
| **Quote reference ID + its grammar** (§9.3 signal 2) | _(the ID, plus its shape — e.g. `3 letters + 8 digits`)_ |
| Vehicle substitution, if the exact trim was unavailable | `NONE` / _(what was selected and why)_ |
| Evidence captured | `verbatim_only` (per OQ-004 — no screenshots this cycle) |

### Route 2 — belairdirect

| Field | Value |
| --- | --- |
| Started at (ISO 8601, ET) | |
| Ended at (ISO 8601, ET) | |
| Entry URL | |
| **Reached a priced screen?** | `YES` / `NO` |
| **Exact stopping step** (`page → section → field`) | |
| Stated reason, verbatim, redacted | |
| Proposed `TerminalStatus` | |
| Proposed `ReasonCode` | |
| Was G1 selectable as licence class? | `YES` / `NO` / `N/A` |
| Was "do not yet own the vehicle" expressible? | `YES` / `NO` / how it was expressed |
| Did it demand a licence number to proceed? | `YES` / `NO` — at which step |
| **Exposed AB election toggles?** | `YES` / `NO` / `NOT_REACHED` |
| Coverage toggles visible before pricing? | `YES` / `NO` |
| CAPTCHA / bot check encountered? | `YES` / `NO` — at which step |
| Contact capture required before price? | `YES` / `NO` |
| Friction observed | |
| **Quote reference ID + its grammar** | |
| Vehicle substitution, if the exact trim was unavailable | `NONE` / _(what and why)_ |
| Evidence captured | `verbatim_only` |

### Route 3 — RBC Insurance

| Field | Value |
| --- | --- |
| Started at (ISO 8601, ET) | |
| Ended at (ISO 8601, ET) | |
| Entry URL | |
| **Reached a priced screen?** | `YES` / `NO` |
| **Exact stopping step** (`page → section → field`) | |
| Stated reason, verbatim, redacted | |
| Proposed `TerminalStatus` | |
| Proposed `ReasonCode` | |
| Was G1 selectable as licence class? | `YES` / `NO` / `N/A` |
| Was "do not yet own the vehicle" expressible? | `YES` / `NO` / how it was expressed |
| Did it demand a licence number to proceed? | `YES` / `NO` — at which step |
| **Exposed AB election toggles?** | `YES` / `NO` / `NOT_REACHED` |
| Coverage toggles visible before pricing? | `YES` / `NO` |
| CAPTCHA / bot check encountered? | `YES` / `NO` — at which step |
| Contact capture required before price? | `YES` / `NO` |
| Friction observed | |
| **Quote reference ID + its grammar** | |
| Vehicle substitution, if the exact trim was unavailable | `NONE` / _(what and why)_ |
| Evidence captured | `verbatim_only` |

### Route 4 — Desjardins

| Field | Value |
| --- | --- |
| Started at (ISO 8601, ET) | |
| Ended at (ISO 8601, ET) | |
| Entry URL | |
| **Reached a priced screen?** | `YES` / `NO` |
| **Exact stopping step** (`page → section → field`) | |
| Stated reason, verbatim, redacted | |
| Proposed `TerminalStatus` | |
| Proposed `ReasonCode` | |
| Was G1 selectable as licence class? | `YES` / `NO` / `N/A` |
| Was "do not yet own the vehicle" expressible? | `YES` / `NO` / how it was expressed |
| Did it demand a licence number to proceed? | `YES` / `NO` — at which step |
| **Exposed AB election toggles?** | `YES` / `NO` / `NOT_REACHED` |
| Coverage toggles visible before pricing? | `YES` / `NO` |
| CAPTCHA / bot check encountered? | `YES` / `NO` — at which step |
| Contact capture required before price? | `YES` / `NO` |
| Friction observed | |
| **Quote reference ID + its grammar** | |
| Vehicle substitution, if the exact trim was unavailable | `NONE` / _(what and why)_ |
| Evidence captured | `verbatim_only` |

---

## 6. Substitutions and deviations

| Route replaced | Replaced with | Reason | Timestamp |
| --- | --- | --- | --- |

---

## 7. Result

| Question | Answer |
| --- | --- |
| Routes reaching a priced screen | _( / 4)_ |
| Routes stopping at licence class | |
| Routes stopping at vehicle ownership | |
| Routes stopping at a contact-capture or human gate | |
| Routes exposing AB election toggles at any point | |

### 7.1 Plan selection (§5.2)

| Outcome | Plan | Consequence |
| --- | --- | --- |
| ≥1 route reaches a priced screen | **Plan A** | Full spec. Benefit Price Probe, measured parity, vehicle inversion, channel arbitrage live for `operator`. |
| 0 routes reach a priced screen | **Plan B** | Those four modules run only under `sim_g2_no_car` in the sandbox, visibly labelled. Weight shifts to Rulebook Compiler, Rate-Source Graph, Eligibility Frontier, Broker Harvester. |

**SELECTED PLAN:** `PENDING`

**Justification:** _(one paragraph, citing the route records above)_

### 7.2 Carry-forward

Findings that become inputs to later milestones — fill these in as they emerge, they are not
overhead:

- Registry rows created or corrected by this probe: _(→ Milestone 3)_
- Reason codes observed in the wild: _(→ Eligibility Frontier, §10.3)_
- Friction observations: _(→ Friction Ledger, §10.7)_
- Routes worth a recipe: _(→ Milestone 7, §11.1)_
- AB-toggle availability per carrier: _(→ Benefit Price Probe gating, §10.2)_

---

## 8. Plan B is not a downgrade

Recorded here so it is read before the result is known, not after (§5.3). Under Plan B the
submission still satisfies every minimum acceptance check in §15.1: an exact terminal blocker
satisfies the retrieval check; the `computed` residual result paired with one `estimate_only` or
`quoted_non_comparable` result satisfies the two-outcome coverage-difference check; the broker
voice or email route satisfies cross-channel; market map and evidence are unaffected.

Four clean refusals with exact stopping points and stated reasons is a **complete Day 0**, not a
failed one.
