# Known limitations

Deliverable per FATHOM §15. §15.2 says to write these honestly, and §18 lists "opening the
walkthrough with what could not be done" as an anti-goal — so this document is thorough and the
walkthrough is not.

Last updated 2026-08-13, final pass per `final.md` (Part A UI overhaul + Part B features, on top
of the earlier `finish.md` pass).

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

## 10. Built in the `final.md` pass — Part B

Four of six Part B items shipped, in priority order, on top of the UI overhaul (Part A):

- **B1, Eligibility Frontier** — a full sixth view (`ui/index.html` → **Frontier**), pure inversion
  of reason codes already collected. Honestly thin under this build's actual data: one unlockable
  rung (`run_under_operator_profile`, opening 1 distinct rate source — Sonnet's licence wall), and
  a "closed regardless" list of six routes whose `unresolved`/`RC_ACCESS_CONTROL` outcomes have no
  operator-side unlock. Most attempted routes stopped at this build's own capability limit rather
  than a market-eligibility refusal, so there is little for the ladder to invert yet — stated
  explicitly in the view itself, not left implicit.
- **B3, Injection defense demo** (`make demo-injection`) — runs the real executor against the
  sandbox `echo` site's hidden payload, captures it verbatim in a real evidence artifact, and
  confirms zero bind/payment-shaped actions were proposed in response. See `docs/DECISIONS.md`
  DL-24 for the honest architecture note: this codebase has no module literally named "Reader" or
  "Planner" as §11.3 describes — the defense demonstrated is that the field-filler's behaviour is
  determined by page structure matched against a fixed ontology, never by page content, so the
  payload was never in a position to be read as a command.
- **B4, Ask Your Findings** (`make ask Q="..."`) — a CLI, not a live browser text box. Retrieval
  runs first over `ui/data.json`; the model is only ever called with the retrieved rows, and never
  called at all if nothing retrieves — a structural enforcement of "never answer from general
  knowledge," not a prompt-only promise. See §12 below for why this is a CLI.
- **B5, Honest Scorecard** — rendered on the Sounding view: fabrications caught/shipped, policy
  rules LIVE/PARTIAL, the concurrency bug found-and-fixed flag, sandbox routes run and priced.
  **One figure is deliberately reported as unmeasured rather than invented:** extraction accuracy
  against a manually verified sample. No such sample was built this session; the scorecard says
  "not measured this session" instead of a number, per the same discipline as everything else here.

## 11. Deferred entirely — Part B items not attempted

- **B2, Rulebook Compiler and the `COMPUTED` residual-market premium** — §3 lists this as one of
  four headline outputs and it remains **the single most significant absence in this build.**
  Deliberately not attempted: it requires sourcing a real public rate manual, extracting real
  rating tables reliably, having an LLM write a deterministic rater, and self-verifying against the
  manual's own worked examples — a multi-hour undertaking with a hard honesty bar (a wrong computed
  price is fatal; a missing one is fine). final.md itself sanctions stopping cleanly rather than
  approximating, which is what this is.
- **B6, Live Narration Mode** — explicitly gated by final.md on "only if everything above is done."
  B2 is not done, so this was never in scope for this pass.

Also still not built, from `fathom.md` directly, deferred under the same priority reasoning as the
`finish.md` pass (a working executor and an honest UI beat every one of these):

- Voice executor (disclosure prelude, consent state machine, live escalation)
- Inbound callback catcher
- Benefit Price Probe and measured parity
- Vehicle Inversion Engine
- Channel Arbitrage Detector
- Dark Pattern Detector
- Twin Readers (dual extraction with agreement checking)
- Self-healing route recipes
- Rate Filing Radar
- Broker Disclosure Harvester

## 12. Ask Your Findings is a CLI, not a live UI text box

The Evidence view's "Ask your findings" panel explains this in place, but the reasoning belongs
here too: embedding a live Anthropic API key in `ui/index.html`'s JavaScript would put that key in
the page source of every copy of the file — a static HTML page has no server side to hide it behind.
That is exactly the class of leak this project's own PII/secret discipline exists to prevent (the
operator supplied a real API key mid-session; it was stored in a local, gitignored `.env`, never
committed, never printed after receipt, never embedded in any UI code — see `docs/DECISIONS.md`
DL-26). `make ask Q="..."` runs the same retrieval-and-answer logic server-side instead.

## 13. Cross-channel handoff

**Not built.** The brief's minimum acceptance list includes a cross-channel handoff where the
journey requires it (e.g., web route escalating to a voice or broker channel with context
preserved). No voice or broker executor exists in this build, so no handoff was possible to
demonstrate. Marked FAIL in the acceptance checklist rather than claimed.

## 14. UI-specific limitations

- **Responsive behaviour below ~860px width was written but not visually confirmed.** The browser
  automation tool used to test this UI resized the OS window but the captured screenshot did not
  reflect the narrower viewport, so the `@media (max-width: 860px)` rail-collapse rule in
  `ui/styles.css` is implemented per final.md §A3 but not screenshot-verified at that width.
- **The market graph's layout is a hand-rolled two-column node-link diagram, not a force-directed
  or otherwise auto-laid-out graph.** It is legible and correctly wired (verified live, including
  fixing a real row-collapse bug — see `docs/DECISIONS.md` DL-28), but it does not reflow to avoid
  edge crossings at arbitrary data sizes the way a proper graph layout algorithm would.
- **Extraction accuracy has no verified-sample figure** — see §10 above.

---

## Open questions and decisions

Deferred decisions live in [`OPEN_QUESTIONS.md`](OPEN_QUESTIONS.md) with what blocks each one, and
build-time calls in [`DECISIONS.md`](DECISIONS.md).
