# Open Questions

Per FATHOM §0.6: when uncertain whether an action is permitted, do not perform it — log it here and
continue. Also used for decisions deferred pending evidence.

| # | Opened | Question | Blocking | Status | Resolution |
| --- | --- | --- | --- | --- | --- |
| OQ-001 | 2026-08-09 | Prospective vehicle for the Day 0 probe (year/make/model/trim, annual km, primary use). Must be a genuinely considered candidate, not a placeholder — §5.1. Only the operator can supply this. | Milestone 0 | RESOLVED 2026-08-09 | **2019 Honda Civic LX.** Annual km and primary use still entered live by the operator and recorded verbatim. |
| OQ-002 | 2026-08-09 | Confirm the four Day 0 direct-writer routes (Sonnet, belairdirect, RBC Insurance, Desjardins) and the exclusion rationale for Onlia / TD / CAA recorded in `DAY0_PROBE.md` §4. | Milestone 0 | RESOLVED 2026-08-09 | Confirmed as written. TD / CAA / Onlia deferred to registry rows at Milestone 3. |
| OQ-003 | 2026-08-09 | Onlia is described in public sources as a RIBO-licensed brokerage rather than a direct writer. Needs a `licensed_intermediary` field with regulator evidence at Milestone 3 before its registry row is trusted. | Milestone 3 | OPEN | |
| OQ-004 | 2026-08-09 | Day 0 screenshots: whether to capture at all this cycle. The local vision redactor (§9.6) does not exist until Milestone 3, so any Day 0 screenshot must be redacted by hand or not taken. | Milestone 0 | RESOLVED 2026-08-09 | **Verbatim redacted quotes only. No screenshots for Day 0.** Operator's rationale: the vision redactor does not exist until Milestone 3, §2.1 makes an unredacted screenshot a hard failure, and hand-redaction is not a risk worth taking. A verbatim redacted quote satisfies the evidence requirement on its own. |
| OQ-005 | 2026-08-09 | Residual-market rate manual: confirm the current published Ontario manual version and effective date to compile against (§10.1). Post-1 Jul 2026 AB changes may have moved it. | Milestone 5 | OPEN | |
| OQ-006 | 2026-08-09 | §9.1 lists thirteen rules, all of which produce `DENY`, then states that `ESCALATE` routes to the human checkpoint queue — without naming a rule that produces it. Some rule must, or `ESCALATE` is unreachable. | Milestone 2 | RESOLVED 2026-08-09 | Added **`P-HUMAN-01`** as a documented extension, in the same spirit as the `COMPUTED` status extension in §8.1. It is the only rule returning `ESCALATE`, and it fires on the three triggers §9.1 names: identity lookup, consent attestation, coverage advice (plus declarations and third-party record authorisations, per §2.2). The thirteen specified rules are unchanged and all still return `DENY`. |

---

## Authoritative clarifications

### AC-001 — Organizer Q&A, 2026-08-09

**Source: MyChoice judges, via organizer email. Recorded verbatim. Authoritative — this overrides
the operator's and the specification's prior reading of the participant profile rules.**

> 1. A participant without a car may use any vehicle or driver profile, including a hypothetical
>    one. A clean-record driver profile is recommended to maximize returned rates.
> 2. Manual form filling is not acceptable. An agentic element is required. The expectation is a
>    full driver profile completing as many quote forms as possible.
> 3. Licence plate is not usually mandatory. Skip it where optional; document it if it becomes a
>    blocker.
> 4. Automation is the ask, not a bonus.

**Consequences adopted the same day** — see amendments D-002 through D-007 below, and the
corresponding edits to `fathom.md` §2.1, §2.3, §3, §4, §5, §9.1 and §14.

**What the Q&A did *not* change.** It addresses which *profile* may be used and requires
automation. It says nothing about driver's licence numbers, about representing a hypothetical
person to a real human, or about identity, consent, declaration or purchase steps. The written
brief's prohibitions on those stand, and the amendments below tighten rather than relax them.

---

## Resolved decisions

Amendments to the specification, recorded with their rationale so the reasoning survives the
milestone that produced it.

### D-001 — Amendment to §14: Milestone 2 unblocked before the Day 0 probe completes

**Decided 2026-08-09 by the operator. Status: ADOPTED.**

§14 states that nothing starts until the Day 0 Viability Probe is recorded. That hold exists to
prevent **plan-dependent** work being built before the plan is known.

**The Policy Engine is not plan-dependent.** Every rule in §9.1 is identical under Plan A and Plan
B. `P-SANDBOX-01` matters *more* under Plan B, not less, because Plan B is precisely the branch
where the Benefit Price Probe, measured parity, vehicle inversion and channel arbitrage run against
`sim_g2_no_car` in the sandbox — so the rule preventing a simulated profile from reaching a real
destination carries more load, not less.

**Plan dependency begins at Milestone 5, not Milestone 2.** Milestone 5 is where the Day 0 outcome
selects whether those four modules run live for the `operator` profile or sandboxed under
`sim_g2_no_car`.

**Scope of the amendment.** Milestone 2 (the gate) is unblocked and proceeds. **Milestone 3 remains
blocked** pending the probe — the profile registry, vault, fact-lock, intake and evidence chain are
not touched. Milestones 4 onward remain blocked as written.

This is an amendment to the build order only. No Prime Directive is affected, and §14's ordering
principle — the spine before the signature features — is preserved.

### D-002 — §2.1 and §9.1: P-SANDBOX-01 decoupled, four rules added

**Decided 2026-08-09 by the operator, following AC-001. Status: ADOPTED.**

`sandbox_only` and `hypothetical` were one concept and are now two. Real-destination access and
hypothetical-profile conduct are separate concerns, and conflating them either blocks the primary
profile or lets a simulated one reach a real site.

| Rule | Denies | Terminal status emitted |
| --- | --- | --- |
| `P-HYPO-LICENCE-01` | Any driver's licence number submitted under a hypothetical profile | — |
| `P-HYPO-HUMAN-01` | Any voice, callback or human-contact action carrying a hypothetical profile | — |
| `P-HYPO-STEP-01` | Identity verification, consent attestation, declaration, callback enrolment and purchase steps under a hypothetical profile | `manual_handoff` |
| `P-REAL-FACT-01` | A fabricated material fact submitted under a non-hypothetical profile | — |
| `P-PLATE-01` | Submission of a licence plate value (§2.1 addition, item F) | `blocked` if the field is mandatory |

The brief bans a fabricated licence number under "Participant profile and eligibility" and §8, and
AC-001 did not address it. `P-HYPO-LICENCE-01` is therefore non-negotiable regardless of profile.

**Interpretation 1 — `P-SANDBOX-01` is retained, not deleted. CONFIRMED by the operator
2026-08-09.** Amendment A says "replace"; item B retains `sandbox_only` as the field governing
real-destination access and keeps `profile_sim_g2` sandbox-only and unchanged. With no rule reading
that field, nothing would enforce it. The rule is kept with narrowed semantics: it now keys off
`sandbox_only` alone and says nothing about hypothetical profiles.

> Operator's rationale: *"Redundancy in a safety layer costs nothing. Do not delete gate rules this
> close to the deadline."*

**Interpretation 2 — `P-FACT-01` and `P-REAL-FACT-01` are a mirrored pair, not a duplicate.
CONFIRMED by the operator 2026-08-09.**

> Operator's rationale: *"Fact-lock applies to `profile_hypo_clean` exactly as it does to
> `profile_operator`. If the hypothetical profile's facts drift between insurers, every parity and
> channel-arbitrage claim is invalid and the comparison is worthless. This is not optional."*

Consequence to carry forward: **`profile_hypo_clean` is fact-locked at session start like any other
profile.** Its facts are invented once, sealed, and never varied across routes. §10.6 channel
arbitrage depends on this directly — comparing two channels at "identical fact-lock" is meaningless
if the facts were not identical.

- `P-FACT-01` applies to **every** profile, hypothetical included. Fact-lock is what makes results
  comparable across insurers; if the clean hypothetical's facts drifted between routes, the whole
  comparison would be invalid and every parity claim with it. §10.2's boundary is unchanged —
  coverage elections vary freely, facts never do.
- `P-REAL-FACT-01` applies **only** to non-hypothetical profiles and denies a *fabricated* material
  fact, mirroring `P-HYPO-LICENCE-01`. Together the two prevent the profiles bleeding into each
  other: a hypothetical may never carry a real licence, and the operator's profile may never carry
  an invented fact.

**Both interpretations RESOLVED 2026-08-09. No code change required — the shipped rule set already
implements both, and `tests/test_policy_rules.py` covers each with a denial and an over-block case.**

**Interpretation 3 — contact capture that produces real human follow-up is callback enrolment.**
`P-HYPO-STEP-01` therefore denies submitting contact details under a hypothetical profile where the
journey's purpose is to trigger a call-back or an agent contact. Quote-form contact fields that do
not initiate human follow-up are unaffected. Rationale: AC-001 sanctions completing quote forms,
not causing a real representative to contact a person who does not exist.

### D-003 — §4: profile model, three profiles, two independent flags

**Decided 2026-08-09 by the operator, following AC-001. Status: ADOPTED.**

`sandbox_only: bool` is replaced by two independent fields:

- `hypothetical` — governs licence-number submission, human contact, and step gating.
- `sandbox_only` — governs real-destination access.

| Profile | `hypothetical` | `sandbox_only` | Role |
| --- | --- | --- | --- |
| `profile_hypo_clean` | true | false | **PRIMARY.** Clean-record hypothetical. Maximises returned rates, unlocks every priced-state module. No licence number, ever. |
| `profile_operator` | false | false | Real G1, no car, real information. Powers the Eligibility Frontier. Full voice and human-contact permissions. |
| `profile_sim_g2` | true | true | Sandbox only, unchanged. |

### D-004 — §3: thesis reframed

**Decided 2026-08-09 by the operator, following AC-001. Status: ADOPTED.**

Primary output is broad, evidenced retrieval across as many rate sources as the agent can reach,
using the clean hypothetical profile. The G1 study becomes a second lens layered on top, not the
premise. **Every evidence, dedup and parity requirement is unchanged.**

### D-005 — §5: Day 0 probe purpose changed

**Decided 2026-08-09 by the operator, following AC-001. Status: ADOPTED.**

The probe no longer selects Plan A versus Plan B. **Plan A applies.** It now answers: which of the
four routes returns a rate under `profile_hypo_clean`, which expose the post-1-July-2026
accident-benefit toggles, and what the quote reference ID grammar is. Operator-profile outcomes are
still recorded, because they feed the Eligibility Frontier.

### D-006 — §14: web executor, route recipes and field ontology raised in priority

**Decided 2026-08-09 by the operator, following AC-001. Status: ADOPTED.**

AC-001 items 2 and 4 make automation the ask and form coverage a graded outcome. The web executor,
route recipes and the field ontology mapper move up.

**Constraint, explicit:** evidence discipline is not traded for form count. The written brief's
judging criteria are unchanged and still reward trustworthy over numerous.

### D-007 — §2.1: licence plate

**Decided 2026-08-09 by the operator, following AC-001 item 3. Status: ADOPTED.**

Skip optional licence plate fields. If a plate is mandatory, record `blocked` with the exact field
and stop. Enforced by `P-PLATE-01`.
