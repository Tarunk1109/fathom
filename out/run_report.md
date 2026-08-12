# FATHOM run report

Generated 2026-08-12T03:11:30+00:00.

All results below were retrieved under `profile_hypo_clean`, a **hypothetical** clean-record driver permitted by the organizer Q&A (AC-001). They are not quotes for the operator, and they are labelled as hypothetical everywhere they appear.

## Outcomes

| Route | Profile | Status | Reason | Annual | Assessment | Parity | Evidence |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `rt_reg_9007` | `profile_hypo_clean` | `quoted_comparable` | — | $1,634.00 | CAUTION | not_possible | 2 artifacts |
| `rt_reg_9006` | `profile_hypo_clean` | `quoted_comparable` | — | $1,712.00 | PASS | measured | 2 artifacts |
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

## Metrics

| Metric | Value |
| --- | --- |
| verified applicable rate sources | 22 |
| records total | 25 |
| records attempted | 1 |
| records reconnaissance pending | 24 |
| market completion | 1/1 (100%) |
| comparable quote yield | 0/1 (0%) |
| evidence rate | 0/1 (0%) |
| duplicate suppression | 4/25 (16%) |
| freshness | 1/1 (100%) |
| synthetic records excluded | 7 |

reconnaissance_pending routes were never attempted and are reported separately rather than counted as failures. Unresolved routes stay in every denominator.

## Chain verification

- Evidence chain: chain intact — 15 artifacts
- Policy audit chain: chain intact — 53 entries verified

