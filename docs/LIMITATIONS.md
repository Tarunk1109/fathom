# Known limitations

Deliverable per FATHOM §15. §15.2 says to write these honestly, and §18 lists "opening the
walkthrough with what could not be done" as an anti-goal — so this document is thorough and the
walkthrough is not.

Last updated 2026-08-12, final pass per `finish.md`.

---

## 1. No real insurer route returned a price under the hypothetical profile

**This is the headline finding of the retrieval phase.** Every priced, benchmark-comparable outcome
in this build is from the local synthetic sandbox, clearly labelled `[SANDBOX]` in `run_report.md`,
`results.json` (an explicit `sandbox: true` field, not a naming convention) and the UI. Per route:

| Route | Status | Why |
| --- | --- | --- |
| Sonnet | `blocked` / `RC_HYPO_LICENCE_REQUIRED` | Mandatory, case-sensitive driver's licence number at `Driver details → Your Information`. A hypothetical profile cannot supply one — `P-HYPO-LICENCE-01` denies it, no value is invented. |
| Rates.ca | `blocked` / `RC_ACCESS_CONTROL` | Cloudflare managed challenge at the entry page. Detected, never bypassed (§2.1; D-AGG). |
| LowestRates.ca | `blocked` / `RC_ACCESS_CONTROL` | Same — Cloudflare managed challenge, detected not bypassed. |
| MyChoice | `unresolved` | Reached step 4–7 of the flow (runs varied), 11–20 fields filled depending on attempt, then no actionable control found within the route's time budget. A capability limit of this build's link/button matching on that page's layout, not a market signal. |
| belairdirect | `unresolved` | Retried at the correct quote-entry URL (`car-insurance.html`) per D-URLS. 3 steps, 0 fields filled, no actionable control found. |
| RBC Insurance | `unresolved` | Retried at `/auto-insurance/` per D-URLS. A "Privacy & Security" modal was encountered and logged (not dismissed — no matching dismiss-text control), then no actionable control found. |
| Desjardins | `unresolved` | Retried at `/ca/personal/insurance/car/` per D-URLS. **The deepest real-route run in this build**: 12 steps, 7 fields filled, did not reach a terminal state within the step budget. |

**One bounded attempt each on the D-URLS retry, per instruction.** No rejection was retried;
`unresolved` outcomes were not retried further because they were not rejections — they were the
executor's own capability limit, and repeating the same attempt would not change that limit.

## 2. Aggregators are Cloudflare-fronted (D-AGG)

Rates.ca and LowestRates.ca — the two broadest Ontario comparison routes, and the ones most likely
to price a hypothetical profile without a licence-number wall — both sit behind a Cloudflare
managed challenge. §2.1 forbids bypassing a bot control; the detector recognises the challenge page
and the route is recorded `blocked` with the evidence artifact kept. **This was detected and
respected, not searched around.** No unprotected aggregator substitute was sought, per the standing
decision. It is a real, evidenced property of the Ontario comparison-platform market for an honest
agent, not a defect in this build.

## 3. Licence walls on direct writers for hypothetical profiles

Confirmed on Sonnet (Day 0 hand probe and the automated sandbox reproduction of the same journey
shape both produced the identical wall). Not independently confirmed on belairdirect, RBC or
Desjardins — those three did not reach a licence-number field before running out of actionable
controls or step budget, so whether they would wall the same way is unknown, not evidenced.

**`RC_HYPO_LICENCE_REQUIRED` is deliberately distinct from `RC_LICENCE_CLASS`.** The latter means
the market assessed the applicant's licence class and declined it. The former means the market
never reached an assessment at all — it demanded a credential a hypothetical profile is structurally
prohibited from holding. Its unlock is `run_under_operator_profile`, not `obtain_g2`. Collapsing the
two into one code would put a false rung on the Eligibility Frontier, which this build does not
build but whose input data this distinction protects.

## 4. `profile_operator` was not run against any real destination (D-OPER, final)

> The operator holds a G1 licence and owns no vehicle. The expected outcome of a live retail run is
> a decline, which the project already holds evidenced from the Sonnet reconnaissance. The cost of
> obtaining a second instance of that same evidence is entering a real driver's licence number, date
> of birth and home address into multiple insurer databases hours before a deadline. The evidence
> gain does not justify that. This is a stated limitation, not a gap the submission conceals.

No workaround was sought. This is the operator's own explicit, final decision, not a default.

## 5. The two normalized outcomes with visible coverage differences are sandbox routes

`rt_reg_9006` ($1,712.00, PASS, matches the §8.5 benchmark exactly) and `rt_reg_9007` ($1,634.00,
CAUTION, five coverage variances) satisfy the "two outcomes in the common schema showing coverage
differences" acceptance check — but both are `[SANDBOX]`, labelled as such everywhere they appear
in `run_report.md`, `results.json` and the UI. No real insurer produced a comparable pair.

## 6. Appendix A: 45 of 70 market rows are unvalidated by design

The registry merges FATHOM's own 25 evidenced rows (each carrying a real `source_url` and
`last_verified_at`) with 45 rows from the Ontario regulator's public rate-approval dataset display
of 2026-08-06, supplied directly by the operator. Every appendix-only row loads with
`status: "unresolved"`, `last_verified_at: null`, `requires_current_validation: true`, and its
starting-route text stored as *unverified guidance* in `automation_notes` — never presented as
verified fact, per the appendix's own header note. See `data/seed/appendix_a_source.json` for the
verbatim text and `docs/DECISIONS.md` DL-16/17 for the merge rule.

**One discrepancy is recorded, not resolved:** the appendix's 2026-08-06 display still lists Traders
General Insurance Company as a separate legal entity, while the Aviva amalgamation folding it (with
Pilot and Elite) into Aviva Insurance Company of Canada was effective 2026-01-01. Both readings are
recorded; neither is asserted as correct. This is exactly the class of gap the appendix's own
trailing note warns about.

**Dedup is correspondingly thin.** Only one merge is evidenced (the Aviva amalgamation, on two
agreeing signals). Zero single-signal matches were merged — §9.3's two-signal rule was not relaxed
under deadline pressure. The true number of distinct rate sources is very likely lower than the 67
reported: several appendix entities within the same group almost certainly share filed rates, and
FATHOM has not evidenced it. An unevidenced merge would inflate the dedup metric, which §18 names
directly as an anti-goal — so the metric is reported low rather than guessed high.

## 7. The fabricated-price incident

On 2026-08-11, a live run against MyChoice.ca returned `$177.83` as a quoted premium with zero form
fields filled — a number scraped from the page's own "recent quotes" marketing ticker, not a
response to any submission FATHOM made. It was one run away from reaching `out/results.json` as a
retrieved rate.

**Fixed, three parts:** a price is now believed only if the run actually filled at least one field;
an explicit price container is preferred over free page text; and any figure adjacent to
advertising language ("as low as", "starting at", "from $", "average", ...) is refused even after a
real fill. Locked down as a regression test (`tests/test_price_reader.py`) and demonstrated live
against real captured content (`make demo-fabrication`). Full account: `docs/SAFETY.md` §
"Worked example: the fabricated premium".

## 8. Structural limitations, known from the outset

- **Results retrieved under `profile_hypo_clean` are not quotes for the operator**, and are
  labelled hypothetical everywhere they appear. Neither profile's results are presented as the
  other's.
- **Panel membership changes constantly.** Any aggregator result is bounded by its live panel on
  the day, which is why every registry row carries `last_verified_at` (or `null` where genuinely
  unverified).
- **`unresolved` rate sources stay in every metric denominator** (§11.9). They are never silently
  reclassified toward a better-looking status.

## 9. Method and scope limitations

- **The PII sweep is a regex floor, not a ceiling.** Three live false-positive classes were found
  and fixed during this build: a header-scoped pragma leaking from a test fixture, and
  `PHONE_NANP`/`PAYMENT_CARD` matching digit runs inside sha256 hex digests. See
  `docs/SAFETY.md` § "Controls that failed open, and were caught".
- **Vision redaction was not built (DL-04).** Screenshots are excluded from the submission per
  OQ-004, so it has no consumer — a scope decision, not an oversight.
- **Day 0 evidence is verbatim quotes only** — no screenshots, for the same reason.
- **Parity is `not_possible` on every route with coverage variance.** The Benefit Price Probe that
  would measure per-item deltas was not built, so no benchmark-equivalent price is stated where
  coverage differs. §18 forbids filling a parity gap with an invented number.
- **Field mapping is heuristic.** The ontology scores label/name/id/placeholder signals; a
  mis-mapped field is possible and would show up as a filled field the journey rejected.
- **The executor's link/button detection is a real capability limit**, evidenced directly by
  belairdirect and MyChoice both stopping at "no actionable control" on pages that plausibly had
  one. This is not a market signal — it is a gap in this build's page-reading heuristics, stated
  plainly rather than disguised as a market finding.
- **"Appendix B" (the hackathon brief's registry field template) was never supplied in this
  session**, the same gap Appendix A originally had before the operator provided it. FATHOM's own
  §8.3 registry schema was used as the operative field set instead — every field present on every
  row, `null` or empty where genuinely unknown. See `docs/DECISIONS.md` DL-21.

## 10. Deferred entirely

Present in `fathom.md`, not built, and not claimed:

- Voice executor (disclosure prelude, consent state machine, live escalation)
- Inbound callback catcher
- Rulebook Compiler and the `COMPUTED` residual-market premium — §3 lists this as one of four
  headline outputs and it is the most significant absence in this build
- Benefit Price Probe and measured parity
- Vehicle Inversion Engine
- Channel Arbitrage Detector
- Dark Pattern Detector
- Eligibility Frontier solver
- Twin Readers (dual extraction with agreement checking)
- Self-healing route recipes
- The injection-resistance demo
- Ask-Your-Own-Findings

These were deferred deliberately under the operator's priority order: a working executor beats
every one of them, and the organizers stated that automation is the ask, not a bonus.

## 11. Cross-channel handoff

**Not built.** The brief's minimum acceptance list includes a cross-channel handoff where the
journey requires it (e.g., web route escalating to a voice or broker channel with context
preserved). No voice or broker executor exists in this build, so no handoff was possible to
demonstrate. Marked FAIL in the acceptance checklist rather than claimed.

---

## Open questions and decisions

Deferred decisions live in [`OPEN_QUESTIONS.md`](OPEN_QUESTIONS.md) with what blocks each one, and
build-time calls in [`DECISIONS.md`](DECISIONS.md).
