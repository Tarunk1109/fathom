# FATHOM — FINISH

**Single-shot completion plan. Execute top to bottom. Do not stop for approval.**

Read this whole file before starting. Everything here is decided. Nothing in it needs my confirmation.

Deadline: Wednesday 12 August 2026, 11:59 PM ET.

---

## 0. Working mode for this session

- **Feature freeze is in effect.** No new modules, no new subsystems, no refactors. If something in `fathom.md` is not built by now, it is deferred and goes in LIMITATIONS.md.
- Run every section below without stopping. Make judgment calls yourself and record them in `docs/DECISIONS.md`.
- Only stop if you hit something genuinely undecidable. Everything in this file is already decided.
- Status updates: two or three lines per section. No long reports.
- No new dependencies.
- Commit after each numbered section.

---

## 1. Three standing decisions — record these, then act on them

Write all three into `docs/DECISIONS.md` with rationale, and into `docs/LIMITATIONS.md` where noted.

### D-AGG: Aggregator routes are closed. Accepted.

Rates.ca and LowestRates.ca are behind Cloudflare managed challenge. Detected, not bypassed. §2.1 forbids working around access controls and the brief lists `blocked` as a valid terminal status.

Do not search for an unprotected aggregator. Do not retry.

**Record this as a finding, not a failure:** the two broadest Ontario comparison routes are bot-fronted, so an agentic shopper acting honestly cannot reach them. That is a real, evidenced property of the market and it belongs in run_report.md as a result.

### D-OPER: profile_operator will NOT be run against any real destination. Final.

Rationale for LIMITATIONS.md, verbatim:

> The operator holds a G1 licence and owns no vehicle. The expected outcome of a live retail run is a decline, which the project already holds evidenced from the Sonnet reconnaissance. The cost of obtaining a second instance of that same evidence is entering a real driver's licence number, date of birth and home address into multiple insurer databases hours before a deadline. The evidence gain does not justify that. This is a stated limitation, not a gap the submission conceals.

Do not run it. Do not ask again.

### D-URLS: Retry the three direct writers at their actual quote entry points.

The previous run hit marketing homepages, not quote flows. Use these:

- belairdirect: `https://www.belairdirect.com/en/car-insurance.html`, then the "Get a quote" control
- RBC Insurance: `https://www.rbcinsurance.com/auto-insurance/`, then "Get a quote"
- Desjardins: `https://www.desjardins.com/ca/personal/insurance/car/`, then "Get a quote"

One bounded attempt each with a generous time budget. Existing approvals cover these routes. If a payload change invalidates an approval, record `manual_handoff` and move on — do not block the run waiting for me.

Whatever comes back, record it with a terminal status and reason code. A deep run that ends at a licence wall is a good result. Do not retry a rejection.

---

## 2. The fabricated-price incident becomes a headline

This is the most important artifact in the submission. Treat it accordingly.

**What happened:** the executor reported `$177.83` as a MyChoice quote. It was advertising copy on a landing page. Zero fields had been submitted. One run away from being reported as a retrieved rate.

**What was fixed:** the price reader now refuses any figure unless the run actually submitted data, prefers an explicit price container, and rejects figures adjacent to advertising language.

### 2.1 Write it up in `docs/SAFETY.md`

A dedicated section, `Worked example: the fabricated premium`. Cover:

- The exact bad reading and where it came from
- Why it was wrong: landing-page marketing copy, no submission had occurred
- The three-part fix
- What it demonstrates: the difference between a system that returns numbers and one that returns evidence. A number with no submission behind it is not a quote, and the system now knows that structurally rather than by convention.

Reference §6.1 — one invented number ends the submission — and state that this control exists because the failure actually occurred, not because it was anticipated.

### 2.2 Build `scripts/demo_fabrication.py`

Same shape as `demo_gate.py`. One command, no arguments needed.

It must:
1. Load the saved MyChoice artifact from the original run
2. Run the OLD reader logic against it and print the fabricated `$177.83`
3. Run the CURRENT reader against the same artifact and print the refusal, with the reason (no submission occurred / advertising-adjacent figure / no price container)
4. Exit 0

Add it to the Makefile as `make demo-fabrication`.

Keep the old reader logic as a small quarantined function inside this script only, clearly commented as retained for demonstration. It must not be importable from the executor package.

### 2.3 Add the pair to SAFETY.md's controls-that-failed-open list

Alongside the header-only pragma fix and the PII sweep boundary fixes. Three worked examples of controls that failed open and were caught. That list is a submission asset.

---

## 3. Deliverables — regenerate all of them, in this order

### 3.1 `out/run_report.md`

Required content:

- **Header:** run timestamp, profile used, benchmark coverage package, vehicle, requested effective date
- **Coverage ledger:** every route attempted, with registry_id, brand, legal underwriter, distinct_rate_source_id, channel, terminal status, reason code, timestamp, evidence CID
- **The five metrics with denominators visible:**
  - Market completion = evidenced terminal statuses ÷ verified applicable rate sources
  - Comparable quote yield = quoted_comparable ÷ verified applicable rate sources
  - Evidence rate = outcomes with valid source, timestamp and redacted artifact ÷ all outcomes
  - Duplicate suppression = brands mapped to an existing distinct_rate_source_id ÷ total brands
  - Freshness = registry records verified in the hackathon window ÷ total records
- **Unresolved records stay in every denominator.** Never silently reclassify.
- **A plain statement, prominently placed:** no real insurer route returned a price under the hypothetical profile, and the reasons why, itemized.
- **The Aviva collapse called out explicitly** as a named finding: Pilot, Elite and Traders General amalgamated into Aviva Insurance Company of Canada on 2026-01-01, merged on two evidenced signals, with the source URLs.
- **The aggregator finding** as a named finding per D-AGG.
- **The fabricated-price incident** as a named finding, with a pointer to SAFETY.md and `make demo-fabrication`.

Every sandbox-derived number is labelled `SANDBOX` inline, not only in a legend.

### 3.2 `docs/LIMITATIONS.md`

Honest, specific, no hedging. Cover:

- No real insurer priced the hypothetical profile. Why, per route.
- Cloudflare-fronted aggregators (D-AGG), and that this was detected and respected rather than bypassed
- Licence walls on direct writers for hypothetical profiles — Sonnet confirmed, others where observed. Include the `RC_HYPO_LICENCE_REQUIRED` distinction and why it is not `RC_LICENCE_CLASS`.
- profile_operator not run, with the D-OPER rationale verbatim
- The two normalized outcomes are sandbox routes, clearly labelled as such everywhere they appear
- 45 Appendix A rows loaded unvalidated, `requires_current_validation: true`, never presented as verified
- The fabricated-price incident, with the fix
- Deferred from fathom.md: voice executor, inbound callback catcher, rulebook compiler, benefit price probe, vehicle inversion, channel arbitrage, dark pattern detector, eligibility frontier solver, twin readers, self-healing recipes, injection demo, ask-your-findings. List them plainly as not built.

### 3.3 `out/registry.json` and `out/registry.csv`

- All 70 brands/entities, 67 distinct rate sources
- Every Appendix A row: `status: unresolved`, `last_verified_at: null`, `requires_current_validation: true`
- Evidenced rows carry `source_url`
- Aviva collapse visible in the data, not only in the UI
- Every required field from the brief's Appendix B template present, `null` where genuinely unknown

### 3.4 `out/results.json`

Every outcome in the common schema. Sandbox results carry an explicit `sandbox: true` field, not just a naming convention.

### 3.5 UI — verify and polish, do not rebuild

The thin UI (results table, market graph, policy gate log) was already built earlier. This step confirms it actually works and is presentable for the video. No new views, no redesign.

- Start it (`make ui` or whatever the existing command is) and load real data from the latest run, not stale fixture data
- Results view: every route's status, PASS/CAUTION/FAIL verdict, reason code, confidence, evidence link. Sandbox rows visibly marked `SANDBOX` — a badge or label, not just a tooltip.
- Market graph view: 70 brands collapsing to 67 rate sources renders without crashing at that size. The Aviva collapse is visually distinguishable (the green highlight already added) and clicking it shows the two-signal evidence.
- Policy gate log view: shows real entries from the actual run, not placeholder rows. A bind-attempt denial and its rule ID must be visible somewhere in this view.
- No console errors on load. Check the browser dev console once.
- No PII rendered anywhere on screen — run the PII sweep expectation against what's displayed, not just what's stored. Postal code, name, DOB must never appear unredacted in any view.
- If any view is broken or missing, fix it now — this section is still inside the deadline, not deferred. If something is too broken to fix in time, note it plainly in LIMITATIONS.md rather than leaving a view that errors on camera.

Report pass/fail per view.

### 3.6 `docs/ARCHITECTURE.md`

Final pass. Must accurately describe what was built, not what was specified. If a component in fathom.md was not built, it does not appear here as though it was. Include:

- The pipeline as it actually runs
- The policy gate as the load-bearing decision, with the rule list and the LIVE / PARTIAL / DOCUMENTED-ONLY enforcement table
- Human checkpoints and the approval flow
- Consent handling
- Data storage, redaction, deletion
- The MCP servers that exist

### 3.7 `docs/PRIME_DIRECTIVES.md`

Re-sync with `fathom.md` §2. Update the enforcement-status table one final time. Never mark a directive LIVE if the state it reads is not populated.

### 3.8 `README.md`

Written for a judge opening the repo cold, with no context.

- What FATHOM is, in three sentences
- The personal-use boundary
- Setup: exact commands, from clone to running
- `make check` — tests + PII sweep
- `make run` — the full pipeline
- `make demo` — the gate denying a bind attempt, then chain verification, then tamper detection
- `make demo-fabrication` — the fabricated-price catch
- `make verify` — judge-facing chain verification
- Where to find each deliverable
- A one-paragraph honest summary of what the system did and did not achieve

---

## 4. `docs/DEMO_SCRIPT.md`

One page. For each beat: the claim being made, the exact command or UI view that produces it, and what appears on screen.

Beats, in order:

| # | Beat | Command / view |
| --- | --- | --- |
| 1 | Premise and scope | README |
| 2 | Fact-lock: facts sealed at session start, cannot drift between insurers | show the seal + a denial |
| 3 | Market graph: 70 brands collapse to 67 rate sources; the Aviva amalgamation on two evidenced signals | UI graph view |
| 4 | Two normalized outcomes with coverage differences; cheaper one is a different product, labelled SANDBOX | UI results view |
| 5 | The gate: bind attempt denied, rule ID and chain index on screen | `make demo` |
| 6 | Tamper detection: edit an entry, verification fails | `make demo` (second half) |
| 7 | **The fabricated premium: caught, and the fix demonstrated** | `make demo-fabrication` |
| 8 | Real-route outcomes: Cloudflare blocks detected not bypassed, licence walls, every one evidenced | `out/run_report.md` |
| 9 | Metrics with denominators, unresolved kept in the denominator | `out/run_report.md` |
| 10 | Limitations, stated plainly | `docs/LIMITATIONS.md` |

For each beat, note the exact file path or command so nothing needs hunting during recording.

---

## 5. Final integrity sweep

Run and report results for each:

1. `make check` — all tests green, PII sweep clean
2. `python3 tools/pii_sweep.py` across the full repo including `out/` and `docs/` — zero hits
3. `make verify` — chain verifies
4. `make demo` — works
5. `make demo-fabrication` — works
6. `make run` — full pipeline completes
7. **Grep the entire repo for the operator's real values.** No real licence number, DOB, full postal code, street address, phone or email anywhere in code, docs, exports, evidence artifacts or commit history. Report explicitly that this check ran and what it found.
8. Confirm every sandbox-derived number is labelled `SANDBOX` in run_report.md, results.json and the UI
9. Confirm no fabricated value exists anywhere in any export — every number traces to an evidence artifact or is labelled computed/sandbox
10. Confirm `unresolved` counts appear in every metric denominator

---

## 6. Acceptance checklist — verify each, report pass/fail honestly

From the brief's minimum demo acceptance:

- [ ] At least one permitted route reaches a returned rate **or an exact terminal blocker** — blockers count, and you have several
- [ ] Cross-channel handoff where the journey required it — if not built, mark FAIL and note it in LIMITATIONS.md rather than claiming it
- [ ] At least two outcomes in the common schema showing coverage differences — present, sandbox-labelled
- [ ] Registry distinguishes legal underwriter, insurer group, brand, distributor and rate source
- [ ] Every demonstrated outcome has a timestamp and redacted evidence
- [ ] No real licence number, full address, payment data or unredacted recording anywhere in the submission
- [ ] No route used a fabricated licence number
- [ ] Every simulated or hypothetical profile visibly labelled, none sent anywhere prohibited
- [ ] All three UI views (results, graph, gate log) load real data and render without errors, ready to record

Do not mark anything pass that is not actually pass. A FAIL that is honestly reported is worth more than a claim that collapses in a live walkthrough.

---

## 7. Final commit

- Commit everything
- `git status` clean
- Print a final summary: what shipped, what did not, and the acceptance checklist result

Then stop.

---

## 8. Standing rules for this session

- No number appears in any export unless it traces to an evidence artifact, or is explicitly labelled computed or sandbox
- No route status is upgraded to look better than the evidence supports
- `unresolved` is never silently converted to anything else
- No insurer is characterized as violating any law or rule anywhere in any artifact — friction is reported with timestamps, never editorialized
- No real destination is touched beyond the three D-URLS retries
- If something cannot be finished, it goes in LIMITATIONS.md rather than being quietly dropped