# FATHOM run report

Generated 2026-08-13T03:41:36+00:00.

## Run parameters

- **Profile:** `profile_hypo_clean` (hypothetical)
- **Vehicle:** 2019 Honda Civic LX
- **Requested effective date:** 2026-09-01
- **Benchmark coverage package (§8.5):** $2,000,000 third-party liability, $1000 collision deductible, $1000 comprehensive deductible, DCPD included, OPCF 44R included, 12-month term

All results below were retrieved under `profile_hypo_clean`, a **hypothetical** clean-record driver permitted by the organizer Q&A (AC-001), unless otherwise noted. They are not quotes for the operator, and they are labelled as hypothetical everywhere they appear. Rows tagged `[SANDBOX]` are from the local synthetic test sites (§11.5), never a real destination, and are excluded from every market metric.

## Named findings

**No real insurer route returned a price under the hypothetical profile.** Every priced, benchmark-comparable outcome below is tagged `[SANDBOX]`. Real routes returned either a terminal blocker or an unresolved capability limit; the itemized reason per route is in the coverage ledger below and in `docs/LIMITATIONS.md`.

**Aggregator routes are Cloudflare-fronted (D-AGG).** Rates.ca and LowestRates.ca both returned a managed challenge at the entry page. Detected and respected, never bypassed (§2.1). The two broadest Ontario comparison routes are closed to an agent that acts honestly — a real, evidenced property of this market. Accepted; not retried.

**The Aviva amalgamation, evidenced.** Aviva Insurance, Pilot Insurance, Elite Insurance and Traders General Insurance collapse to one legal entity, Aviva Insurance Company of Canada, effective 2026-01-01, on two agreeing signals (`underwriter_disclosed` + `regulatory_amalgamation`, source: https://www.avivacanada.com/). See § Rate-source collapse below.

**A fabricated premium was caught before it reached this report.** A live run against MyChoice.ca returned `$177.83` from landing-page marketing copy with zero fields filled. Fixed and locked down as a regression test. Full account in `docs/SAFETY.md` § "Worked example: the fabricated premium"; reproduce with `make demo-fabrication`.

**Residual-market rating data, extracted and never computed.** `out/residual_manual_extract.json` parses the real, public Facility Association Ontario Manual of Rules and Rates (effective 2025-11-01) into 6,440 provenanced territory-definition rows (pages 1398-1605 and two earlier per-section repeats), each carrying its source page and table name. No premium or estimate was computed from it — every figure not cleanly parseable (e.g. rate-group tables whose cells stack multiple values with no unambiguous mapping) was left out rather than guessed. Labelled `UNVERIFIED EXTRACTION` everywhere it appears; see `docs/RESIDUAL_MARKET.md`.

## Coverage ledger

Every route ever attempted, hand-probed or automated. `unresolved` stays `unresolved` — never silently reclassified. Rows never attempted (reconnaissance-pending routes and unvalidated Appendix A rows) are not listed here — see § Metrics for their counts.

| Registry ID | Brand | Legal underwriter | Rate source | Channel | Status | Reason | Timestamp | Evidence CID |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `reg_0001` | Sonnet | Sonnet Insurance Company | `rs_0001` | web_manual_probe | `blocked` | licence_number_required_hypothetical_profile | 2026-08-09T00:00:00+00:00 | `cid:sha256-14216cc8eb1d6e18d…` |
| `reg_0002` | belairdirect | Belair Insurance Company Inc. | `rs_0002` | web | `unresolved` | — | 2026-08-12T00:00:00+00:00 | `—` |
| `reg_0003` | RBC Insurance | RBC Insurance Company of Canada | `rs_0003` | web | `unresolved` | — | 2026-08-12T00:00:00+00:00 | `—` |
| `reg_0004` | Desjardins Insurance | Certas Home and Auto Insurance Company | `rs_0004` | web | `unresolved` | — | 2026-08-12T00:00:00+00:00 | `—` |
| `reg_9001` **[SANDBOX]** | Sandbox Alpha | Sandbox Alpha Insurance Company | `rs_0068` | web | `blocked` | RC_HYPO_LICENCE_REQUIRED | 2026-08-13T03:41:27+00:00 | `cid:sha256-a7a0bcfbdd712ecb1…` |
| `reg_9002` **[SANDBOX]** | Sandbox Bravo | Sandbox Bravo Insurance Company | `rs_0069` | web | `blocked` | RC_ACCESS_CONTROL | 2026-08-13T03:41:28+00:00 | `cid:sha256-c17e5c48427cbc52d…` |
| `reg_9003` **[SANDBOX]** | Sandbox Charlie | Sandbox Charlie Insurance Company | `rs_0070` | web | `callback_required` | RC_HUMAN_REQUIRED | 2026-08-13T03:41:30+00:00 | `cid:sha256-0c449d4e3ea0dd442…` |
| `reg_9004` **[SANDBOX]** | Sandbox Delta | Sandbox Delta Insurance Company | `rs_0071` | web | `unresolved` | — | 2026-08-13T03:41:31+00:00 | `cid:sha256-8a9a8549a747a778e…` |
| `reg_9005` **[SANDBOX]** | Sandbox Echo | Sandbox Echo Insurance Company | `rs_0072` | web | `unresolved` | — | 2026-08-13T03:41:33+00:00 | `cid:sha256-b8de02fe43b1ef003…` |
| `reg_9006` **[SANDBOX]** | Sandbox Foxtrot | Sandbox Foxtrot Insurance Company | `rs_0073` | web | `quoted_comparable` | — | 2026-08-13T03:41:34+00:00 | `cid:sha256-07279c0c1f0cae656…` |
| `reg_9007` **[SANDBOX]** | Sandbox Golf | Sandbox Golf Insurance Company | `rs_0074` | web | `quoted_comparable` | — | 2026-08-13T03:41:36+00:00 | `cid:sha256-6024bbf0a44906b6b…` |

## Outcomes

| Route | Profile | Status | Reason | Annual | Assessment | Parity | Evidence |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `rt_reg_9007` `[SANDBOX]` | `profile_hypo_clean` | `quoted_comparable` | — | $1,634.00 | CAUTION | not_possible | 2 artifacts |
| `rt_reg_9006` `[SANDBOX]` | `profile_hypo_clean` | `quoted_comparable` | — | $1,712.00 | PASS | measured | 2 artifacts |
| `rt_reg_9001` `[SANDBOX]` | `profile_hypo_clean` | `blocked` | RC_HYPO_LICENCE_REQUIRED | — | FAIL | not_possible | 4 artifacts |
| `rt_reg_9002` `[SANDBOX]` | `profile_hypo_clean` | `blocked` | RC_ACCESS_CONTROL | — | FAIL | not_possible | 2 artifacts |
| `rt_reg_9003` `[SANDBOX]` | `profile_hypo_clean` | `callback_required` | RC_HUMAN_REQUIRED | — | FAIL | not_possible | 2 artifacts |
| `rt_reg_9004` `[SANDBOX]` | `profile_hypo_clean` | `unresolved` | — | — | FAIL | not_possible | 2 artifacts |
| `rt_reg_9005` `[SANDBOX]` | `profile_hypo_clean` | `unresolved` | — | — | FAIL | not_possible | 1 artifacts |

## Comparability

The lowest price (rt_reg_9007) does not match the benchmark package — it differs in 5 respect(s). It is a different product, not a cheaper one, and the difference has not been priced.

## Coverage variance

**`rt_reg_9007` `[SANDBOX]`** differs from the §8.5 benchmark in 5 respect(s):
- third-party liability limit: 1,000,000 vs benchmark 2,000,000 (lower)
- collision deductible: 500 vs benchmark 1,000 (lower)
- comprehensive deductible: 500 vs benchmark 1,000 (lower)
- OPCF 44R family protection: excluded vs benchmark included
- income replacement benefit: included — an optional benefit since 1 July 2026, included here and not in the benchmark

## Terminal blockers

**`rt_reg_9001` `[SANDBOX]`** — `blocked` / `RC_HYPO_LICENCE_REQUIRED`  
Stopping step: step 4: Driver's licence number (mandatory — journey cannot advance)  
Policy rules fired: P-HYPO-ATTEST-01, P-HYPO-LICENCE-01  
Stated reason: Field 'licence_number' submits a driver's licence number under hypothetical profile 'profile_hypo_clean'. Any value would be fabricated. §2.1: never fabricate, borrow or alter a licence number — this holds regardless of 

**`rt_reg_9002` `[SANDBOX]`** — `blocked` / `RC_ACCESS_CONTROL`  
Stopping step: step 2: bot check  
Policy rules fired: —  
Stated reason: A CAPTCHA or bot control was presented.

**`rt_reg_9003` `[SANDBOX]`** — `callback_required` / `RC_HUMAN_REQUIRED`  
Stopping step: step 2: callback only  
Policy rules fired: —  
Stated reason: The journey offers a callback instead of a price.

**`rt_reg_9004` `[SANDBOX]`** — `unresolved` / `None`  
Stopping step: step 2: no actionable control  
Policy rules fired: —  
Stated reason: 

**`rt_reg_9005` `[SANDBOX]`** — `unresolved` / `None`  
Stopping step: step 1: could not advance  
Policy rules fired: —  
Stated reason: 

## Rate-source collapse

**70 market brands and legal entities resolve to 67 distinct rate sources.**

FATHOM counts distinct rate sources, not brands. `same_rate_source_as` is asserted only where at least two independent signals agree (§9.3); a single-signal match is recorded as a hypothesis and never merged.

### `rs_0010` — 4 brands, 2 agreeing signals

**Legal underwriter: Aviva Insurance Company of Canada**

- Aviva Insurance
- Pilot Insurance
- Elite Insurance
- Traders General Insurance

Evidence: Pilot, Elite and Traders General amalgamated into Aviva Insurance Company of Canada, effective 2026-01-01. Source: https://www.avivacanada.com/ | UNVERIFIED GUIDANCE from the Appendix A discovery seed (2026-08-06): Direct, RBC, broker and program routes; deduplicate and validate legacy entities

Single-signal hypotheses recorded but **not** merged: 0.

The true number of distinct rate sources is very likely lower than 67 — several entities within the same group probably share filed rates and FATHOM has not evidenced it. An unevidenced merge would inflate the dedup metric, which §18 names directly as an anti-goal.

## Metrics

| Metric | Value |
| --- | --- |
| verified applicable rate sources | 4 |
| distinct rate sources total | 67 |
| records total | 70 |
| records attempted | 4 |
| records never attempted | 66 |
| records never attempted reconnaissance pending | 21 |
| records never attempted appendix unvalidated | 45 |
| market completion | 1/4 (25%) |
| comparable quote yield | 0/4 (0%) |
| evidence rate | 1/4 (25%) |
| duplicate suppression | 4/70 (6%) |
| freshness | 4/4 (100%) |
| synthetic records excluded | 7 |

Market completion and comparable quote yield are computed over distinct rate sources that have been attempted ('verified applicable rate sources'), per §11.9. Evidence rate, duplicate suppression and freshness are computed over records. Records never attempted — either FATHOM's own reconnaissance_pending routes, or Appendix A discovery-seed rows carrying requires_current_validation=true (whose exported status field reads 'unresolved' by explicit instruction, not because an attempt was made) — are excluded from these denominators and reported separately, rather than counted as failed attempts. A route FATHOM did attempt and could not resolve keeps status 'unresolved' and stays in every denominator; that is a different thing from a row nobody has touched yet.

## Chain verification

- Evidence chain: chain intact — 164 artifacts
- Policy audit chain: chain intact — 545 entries verified

