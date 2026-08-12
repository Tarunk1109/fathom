# FATHOM run report

Generated 2026-08-12T05:58:59+00:00.

All results below were retrieved under `profile_hypo_clean`, a **hypothetical** clean-record driver permitted by the organizer Q&A (AC-001). They are not quotes for the operator, and they are labelled as hypothetical everywhere they appear.

## Outcomes

| Route | Profile | Status | Reason | Annual | Assessment | Parity | Evidence |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `rt_reg_9007` | `profile_hypo_clean` | `quoted_comparable` | — | $1,634.00 | CAUTION | not_possible | 2 artifacts |
| `rt_reg_9006` | `profile_hypo_clean` | `quoted_comparable` | — | $1,712.00 | PASS | measured | 2 artifacts |
| `rt_reg_0002` | `profile_hypo_clean` | `unresolved` | — | — | FAIL | not_possible | 3 artifacts |
| `rt_reg_0003` | `profile_hypo_clean` | `unresolved` | — | — | FAIL | not_possible | 1 artifacts |
| `rt_reg_0004` | `profile_hypo_clean` | `unresolved` | — | — | FAIL | not_possible | 12 artifacts |
| `rt_reg_0100` | `profile_hypo_clean` | `blocked` | RC_ACCESS_CONTROL | — | FAIL | not_possible | 1 artifacts |
| `rt_reg_0101` | `profile_hypo_clean` | `blocked` | RC_ACCESS_CONTROL | — | FAIL | not_possible | 1 artifacts |
| `rt_reg_0102` | `profile_hypo_clean` | `unresolved` | — | — | FAIL | not_possible | 7 artifacts |
| `rt_reg_9001` | `profile_hypo_clean` | `blocked` | RC_HYPO_LICENCE_REQUIRED | — | FAIL | not_possible | 4 artifacts |
| `rt_reg_9002` | `profile_hypo_clean` | `blocked` | RC_ACCESS_CONTROL | — | FAIL | not_possible | 2 artifacts |
| `rt_reg_9003` | `profile_hypo_clean` | `callback_required` | RC_HUMAN_REQUIRED | — | FAIL | not_possible | 2 artifacts |
| `rt_reg_9004` | `profile_hypo_clean` | `unresolved` | — | — | FAIL | not_possible | 1 artifacts |
| `rt_reg_9005` | `profile_hypo_clean` | `unresolved` | — | — | FAIL | not_possible | 1 artifacts |

## Comparability

The lowest price (rt_reg_9007) does not match the benchmark package — it differs in 5 respect(s). It is a different product, not a cheaper one, and the difference has not been priced.

## Coverage variance

**`rt_reg_9007`** differs from the §8.5 benchmark in 5 respect(s):
- third-party liability limit: 1,000,000 vs benchmark 2,000,000 (lower)
- collision deductible: 500 vs benchmark 1,000 (lower)
- comprehensive deductible: 500 vs benchmark 1,000 (lower)
- OPCF 44R family protection: excluded vs benchmark included
- income replacement benefit: included — an optional benefit since 1 July 2026, included here and not in the benchmark

## Terminal blockers

**`rt_reg_0002`** — `unresolved` / `None`  
Stopping step: step 3: no actionable control  
Policy rules fired: —  
Stated reason: 

**`rt_reg_0003`** — `unresolved` / `None`  
Stopping step: step 1: no actionable control  
Policy rules fired: P-BUDGET-01  
Stated reason: 

**`rt_reg_0004`** — `unresolved` / `None`  
Stopping step: exhausted 12 steps  
Policy rules fired: —  
Stated reason: 

**`rt_reg_0100`** — `blocked` / `RC_ACCESS_CONTROL`  
Stopping step: step 1: bot check  
Policy rules fired: —  
Stated reason: A CAPTCHA or bot control was presented.

**`rt_reg_0101`** — `blocked` / `RC_ACCESS_CONTROL`  
Stopping step: step 1: bot check  
Policy rules fired: —  
Stated reason: A CAPTCHA or bot control was presented.

**`rt_reg_0102`** — `unresolved` / `None`  
Stopping step: step 7: could not advance  
Policy rules fired: P-BUDGET-01  
Stated reason: 

**`rt_reg_9001`** — `blocked` / `RC_HYPO_LICENCE_REQUIRED`  
Stopping step: step 4: Driver's licence number (mandatory — journey cannot advance)  
Policy rules fired: P-HYPO-ATTEST-01, P-HYPO-LICENCE-01  
Stated reason: Field 'licence_number' submits a driver's licence number under hypothetical profile 'profile_hypo_clean'. Any value would be fabricated. §2.1: never fabricate, borrow or alter a licence number — this holds regardless of 

**`rt_reg_9002`** — `blocked` / `RC_ACCESS_CONTROL`  
Stopping step: step 2: bot check  
Policy rules fired: —  
Stated reason: A CAPTCHA or bot control was presented.

**`rt_reg_9003`** — `callback_required` / `RC_HUMAN_REQUIRED`  
Stopping step: step 2: callback only  
Policy rules fired: —  
Stated reason: The journey offers a callback instead of a price.

**`rt_reg_9004`** — `unresolved` / `None`  
Stopping step: step 1: could not advance  
Policy rules fired: —  
Stated reason: 

**`rt_reg_9005`** — `unresolved` / `None`  
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
| verified applicable rate sources | 67 |
| records total | 70 |
| records attempted | 52 |
| records reconnaissance pending | 18 |
| market completion | 3/52 (6%) |
| comparable quote yield | 0/52 (0%) |
| evidence rate | 6/52 (12%) |
| duplicate suppression | 4/70 (6%) |
| freshness | 7/52 (13%) |
| synthetic records excluded | 7 |

reconnaissance_pending routes were never attempted and are reported separately rather than counted as failures. Unresolved routes stay in every denominator.

## Chain verification

- Evidence chain: chain intact — 30 artifacts
- Policy audit chain: chain intact — 103 entries verified

