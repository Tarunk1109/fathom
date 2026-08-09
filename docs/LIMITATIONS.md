# Known limitations

Deliverable per FATHOM §15. §15.2 says to write these honestly, and §18 lists "opening the
walkthrough with what could not be done" as an anti-goal — so this document is thorough and the
walkthrough is not.

**Populated as the build proceeds.** Limitations are recorded when they are discovered, not
assembled at the end, because the ones assembled at the end are the ones that get softened.

---

## Structural, known from the outset

These follow from the premise (§3) rather than from any defect.

- **The operator holds a G1 and owns no vehicle.** Most standard retail routes correctly return
  ineligible. That is the measurement, not a failure of the system — but it means the retrieved
  quote count is small by construction.
- **The `computed` residual-market premium is a calculation, not a quote.** It is produced from a
  publicly published rate manual and does not bind any insurer. Real placement requires a licensed
  intermediary. It is rendered in its own band and never mixed with retrieved quotes.
- **Panel membership changes constantly.** Any aggregator or brokerage result is bounded by its
  live panel on the day it was run, which is why every registry row carries a `last_verified_at`.
- **Some rate sources will remain `unresolved`.** They stay in every metric denominator (§11.9)
  rather than being dropped.
- **Simulated profiles never touch a real destination.** Anything demonstrated under
  `sim_g2_no_car` or `sim_g_owner` is a sandbox result, visibly labelled, and is not evidence about
  the real market.
- **Industry vehicle rating group tables are not public.** Vehicle work uses published rankings
  only, and inferred rows are labelled inferred (§10.4). A ranking is never presented as a premium.

---

## Method limitations

- **The PII sweep is a regex floor, not a ceiling.** It cannot see inside an image, cannot detect an
  address written in prose, and cannot catch a value split across lines. The local redactor
  (Milestone 3) is the real defence, and §15.1 still requires a manual sweep of screenshots and the
  recorded walkthrough.
- **Day 0 evidence is verbatim quotes only.** No screenshots were captured during the probe
  (OQ-004), because the vision redactor did not exist yet and hand-redaction was judged a worse
  risk than a narrower evidence form.

---

## Discovered during the build

Recorded with the milestone that surfaced them. Empty until Milestone 2.

| # | Limitation | Surfaced at | Consequence |
| --- | --- | --- | --- |

---

## Open questions

Deferred decisions live in [`OPEN_QUESTIONS.md`](OPEN_QUESTIONS.md) with what blocks each one. An
open question is not a limitation until it is answered badly.
