# Known limitations

Deliverable per FATHOM §15. §15.2 says to write these honestly, and §18 lists "opening the
walkthrough with what could not be done" as an anti-goal — so this document is thorough and the
walkthrough is not.

Last updated 2026-08-12.

---

## 1. What the market map actually contains

**70 market records, 67 distinct rate sources. Of those 70, only 25 are evidenced by FATHOM.**

| Category | Count | Meaning |
| --- | --- | --- |
| Evidenced rows | 25 | Carry a `source_url` FATHOM retrieved and a `last_verified_at` |
| Appendix A discovery-seed rows | 45 | `requires_current_validation: true`, `last_verified_at: null`, `status: unresolved` |

The Appendix A rows come from the Ontario regulator's public rate-approval dataset display of
2026-08-06. **The appendix's own header states it proves nothing on its own** — not current
new-business availability, not standard personal-auto scope, not a consumer-accessible quote path.
FATHOM stores its starting-route text as *unverified guidance* in `automation_notes`, never as
fact, and those rows are excluded from any claim of verification.

Reported as 67 rate sources rather than 60 entities because the appendix lists legal entities while
FATHOM additionally tracks consumer brands and comparison platforms as separate records.

## 2. Dedup is thin, and honestly so

One merge was made: **Aviva Insurance, Pilot Insurance, Elite Insurance and Traders General
Insurance collapse into Aviva Insurance Company of Canada**, on two agreeing signals
(`underwriter_disclosed` + `regulatory_amalgamation`, the latter carrying its source URL).

Everything else stands as a distinct rate source, and **zero single-signal merges were made** —
§9.3 requires two agreeing signals and that rule was not relaxed. The consequence is that the true
number of distinct rate sources is almost certainly **lower than 67**: several appendix entities
within the same group very likely share filed rates, and FATHOM has not evidenced it. An
unevidenced merge would inflate the dedup metric, which is the failure §18 names directly.

**Notable discrepancy, unresolved.** The appendix dataset of 2026-08-06 still lists Traders General
Insurance Company as a separate legal entity, while the amalgamation into Aviva Insurance Company
of Canada was effective 2026-01-01. Either the amalgamation is narrower than the public source
describes, or the regulator's display carries legacy names. FATHOM records both readings and
asserts neither. This is exactly the class of thing the appendix's trailing note warns about.

## 3. Retrieval: what walled, and where

Under `profile_hypo_clean` (a hypothetical clean-record driver, permitted by AC-001):

| Route | Outcome | Where it stopped |
| --- | --- | --- |
| Sonnet | `blocked` / `RC_HYPO_LICENCE_REQUIRED` | `Driver details → Your Information → Driver's licence number`, mandatory and case sensitive |
| Rates.ca | `blocked` / `RC_ACCESS_CONTROL` | Cloudflare managed challenge at the entry page |
| LowestRates.ca | `blocked` / `RC_ACCESS_CONTROL` | Cloudflare managed challenge at the entry page |
| MyChoice, belairdirect, RBC, Desjardins | see `out/run_report.md` | recorded per run |

**Bot controls were detected, never bypassed.** §2.1 prohibits it, so detection *is* the response:
record `blocked`, keep the evidence artifact, end the route. Two of the three aggregator routes —
the ones most likely to price a hypothetical profile — are therefore closed to any automated
agent that respects the rule. That is a real property of this market, not a defect in the agent,
but it substantially caps the number of retrieved prices this build can honestly report.

**The licence-number wall is the dominant finding.** Where a journey demands a driver's licence
number before pricing, a hypothetical profile cannot proceed: `P-HYPO-LICENCE-01` denies it and no
value is invented. Its unlock is `run_under_operator_profile`, not `obtain_g2` — a distinction the
Eligibility Frontier depends on, and one that would produce a false rung if collapsed into
`RC_LICENCE_CLASS`.

## 4. Structural limitations, known from the outset

- **The operator holds a G1 and owns no vehicle.** Most standard retail routes correctly return
  ineligible for `profile_operator`. That is the measurement, not a defect — but it means the
  operator-profile quote count is small by construction.
- **Results retrieved under `profile_hypo_clean` are not quotes for the operator**, and are
  labelled hypothetical everywhere they appear. Neither profile's results are presented as the
  other's.
- **Panel membership changes constantly.** Any aggregator result is bounded by its live panel on
  the day, which is why every registry row carries `last_verified_at`.
- **Unresolved rate sources stay in every metric denominator** (§11.9). `reconnaissance_pending`
  rows — never attempted — are reported separately rather than counted as failures.

## 5. Method and scope limitations

- **The PII sweep is a regex floor, not a ceiling.** It cannot see inside an image, detect an
  address written in prose, or catch a value split across lines. Three live false-positive classes
  were found and fixed (hex digests matching phone and card patterns; a file-scoped pragma leaking
  from a test fixture), which is itself evidence that regex matching is approximate.
- **Vision redaction was not built** (DL-04). Screenshots are excluded from the submission per
  OQ-004, so it has no consumer. The consequence is that FATHOM's evidence is page *text*, not
  page images.
- **Day 0 evidence is verbatim quotes only** — no screenshots (OQ-004), because the vision
  redactor did not exist and hand-redaction was judged the worse risk.
- **Parity is `not_possible` on every route with coverage variance.** The Benefit Price Probe that
  would measure per-item deltas is deferred, so no benchmark-equivalent price is stated where
  coverage differs. §18 forbids filling a parity gap with an invented number, so the gap is
  reported as a gap.
- **Field mapping is heuristic.** The ontology scores label/name/id/placeholder signals; matches
  below 0.6 confidence are recorded as hypotheses. A mis-mapped field is possible and would show
  up as a filled field that the journey rejected.

## 6. Deferred entirely

Present in `fathom.md`, not built, and not claimed: voice executor, inbound callback catcher,
Rulebook Compiler and the `COMPUTED` residual-market premium, Benefit Price Probe, vehicle
inversion, channel arbitrage, dark-pattern detector, Eligibility Frontier solver, twin readers,
self-healing route recipes, the injection-resistance demo, and Ask-Your-Own-Findings.

These were deferred deliberately under the operator's priority order: a working executor beats
every one of them, and the organizers stated that automation is the ask.

**The most significant absence is the `COMPUTED` residual-market premium.** §3 lists it as one of
four headline outputs — the one price guaranteed to be available — and it is not in this build.

## 7. A real error caught in flight

The executor returned `$177.83` as a quoted premium from a comparison platform's landing page. It
was advertising copy, not a quote: zero fields had been filled. The price reader now refuses any
number unless the run actually submitted data, prefers an explicit price container over free page
text, and rejects figures adjacent to advertising language.

Recorded here because §6.1 is explicit that a single invented number ends the submission, and this
one came within a run of being reported as a retrieved rate. Any premium in this build's outputs
was returned in response to data FATHOM submitted.

---

## Open questions

Deferred decisions live in [`OPEN_QUESTIONS.md`](OPEN_QUESTIONS.md) with what blocks each one, and
build-time calls in [`DECISIONS.md`](DECISIONS.md).
