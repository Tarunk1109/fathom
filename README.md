# FATHOM

**An evidence-grade instrument for the Ontario private-passenger auto insurance market.**

> Sound the market. Prove the bottom.

One intake. Every reachable Ontario rate source. Proof for every result, including every refusal.

Built for the Ontario All-Quote Agent Challenge, August 2026.
Operator: Tarun Karnati, Toronto, Ontario.

---

## Scope, stated plainly

FATHOM is a **personal-use agentic market instrument**. It is not a product, not a service, and not
for anyone but the operator. See [`LICENSE`](LICENSE) — it is not an open source licence and grants
no right of use to anyone else. Judges and challenge organisers have read access for evaluation
only.

**What it does.** It measures the Ontario private-passenger auto market from the position of a
single real applicant: a G1 licence holder who owns no vehicle and has no Canadian driving history.
Every rate source attempted ends in an evidenced terminal status. Refusals are first-class results,
not errors.

**What it does not do.** It does not bind, purchase, renew, cancel or modify a policy. It does not
submit payment information, an e-signature, or an application declaration. It does not bypass a
CAPTCHA, bot control, authentication or rate limit. It does not act for anyone but the operator, and
it does not use anyone else's data. These are enforced in code by the Policy Engine, not by
convention — see [`docs/PRIME_DIRECTIVES.md`](docs/PRIME_DIRECTIVES.md).

**What its outputs are.** Records of observations with timestamps and redacted evidence. Not
insurance advice, not offers, not quotes. A premium labelled `computed` is a calculation from a
publicly published rate manual — it is not a quote from an insurer, and real placement requires a
licensed intermediary. Friction is recorded as observation only; FATHOM alleges no breach of any
law, regulation or rule by any party.

---

## Status

Built in the order given in `fathom.md` §14. The spine before the signature features.

| Milestone | Scope | Status |
| --- | --- | --- |
| 0 | Day 0 reconnaissance probe → maps the four routes (Plan A applies) | **in progress** — probe running by hand, see [`docs/DAY0_PROBE.md`](docs/DAY0_PROBE.md) |
| 1 | The contract: scaffold, licence, directives, PII-sweep CI | **done** |
| 2 | The gate: Policy Engine + hash-chained audit log | **done** — `make demo`, `make verify` |
| 3 | The spine: profiles, vault, fact-lock, intake, evidence, redactor, registry | blocked on Milestone 0 |
| 4 | First blood: web executor, first real terminal status, normalizer | blocked |
| 5 | The signature: Rulebook Compiler, Benefit Price Probe, Parity Solver | blocked |
| 6 | The market: fingerprinting, Rate Filing Radar, Broker Harvester, Frontier | blocked |
| 7 | The engineering: recipes, twin readers, sandbox, injection defence | blocked |
| 8 | The voice: disclosure, consent state machine, escalation, callbacks | blocked |
| 9 | The submission: vehicle inversion, arbitrage, scorecard, narration | blocked |

Milestones 1 and 2 are plan-independent, so they ran in parallel with the probe (amendment D-001).
Nothing past Milestone 2 begins until the probe is recorded.

The specification was amended on 2026-08-09 following an organizer Q&A: a hypothetical clean-record
driver profile is permitted and automation is required. See `docs/OPEN_QUESTIONS.md` — AC-001 and
amendments D-002 through D-007.

---

## The gate

```bash
make demo      # a bind attempt denied, with rule ID and audit chain index, then chain verification
make verify    # verify the audit chain — judge-facing, no code reading required
make rules     # list every registered rule and what it denies
```

Everything routes through the Policy Engine (§7.1). No executor calls a browser, phone or API
directly. 18 deny rules plus one escalate rule, deterministic, no LLM in the decision path, every
decision appended to a hash-chained log.

Three verdicts with different downstream behaviour: `ALLOW` proceeds, `DENY` refuses and the route
ends, `ESCALATE` sends the request to the operator and leaves the route open.

---

## Requirements

Python 3.12+. Nothing else, yet.

Dependencies are added at the milestone that uses them, not up front — the stack in `fathom.md` §13
is a set of decisions to be made on arrival, not a manifest to install now. The PII sweep and its
tests are stdlib-only by design, so the safety check runs before any dependency exists.

```
python3 --version    # 3.12 or newer
```

---

## Setup

```bash
git clone <repo> fathom && cd fathom
make hooks     # optional: run the PII sweep automatically before every commit
make check     # sweep + tests
```

---

## The PII sweep

The hard constraint in §2.1 — no real licence number, full address, payment data or raw call audio
anywhere in the repo, logs, prompts, traces, screenshots or the submission — is enforced by a check
that runs identically in CI and locally.

```bash
make sweep                       # scan the whole repo, including out/ and docs/
python3 tools/pii_sweep.py       # identical, no make required
python3 tools/pii_sweep.py --list-rules
python3 tools/pii_sweep.py --json
```

Exit code 0 clean, 1 on findings. CI fails the build on a hit.

Two properties are deliberate:

- **The sweep never prints what it found.** Findings are reported as file, line, rule and a masked
  excerpt. Printing the match would put PII into CI logs — the exact failure the sweep prevents.
- **Binary files are listed for manual review, not silently skipped.** A screenshot cannot be
  grepped. §15.1 requires the final sweep to cover screenshots and recordings too, and the tool must
  not imply coverage it does not have.

False positives are handled with an inline pragma, never by weakening a rule:

```python
value = "K1A 0B1"   # pii-sweep: allow PC_FULL_POSTAL  synthetic fixture
value = "..."       # pii-sweep: allow PC_FULL_POSTAL,EMAIL  two rules on one line
value = "..."       # pii-sweep: allow  everything on this line
```

Rules: `DL_ONTARIO`, `PC_FULL_POSTAL` (FSA-only such as `M5V` is permitted), `VIN`, `PHONE_NANP`,
`EMAIL`, `PAYMENT_CARD` (Luhn-checked), `STREET_ADDRESS`, `DOB_LABELLED` (birth year alone is
permitted).

---

## Tests

```bash
make test                                  # python3 -m unittest discover -s tests
```

Stdlib `unittest` for now; pytest arrives with Milestone 2 per §13. The suite includes a test that
sweeps the live repository, so a leak fails the tests as well as CI.

---

## Layout

```
fathom/
├── docs/            PRIME_DIRECTIVES, DAY0_PROBE, ARCHITECTURE, SAFETY, LIMITATIONS, OPEN_QUESTIONS
├── packages/        policy, profiles, vault, intake, registry, planner, executors,
│                    rater, evidence, redactor, normalizer, analysis, mcp
├── sandbox/         five synthetic insurer sites (Milestone 7)
├── ui/              seven views (Milestone 9)
├── tools/           pii_sweep.py
├── tests/
├── out/             registry.json/csv, run_report.md, benefit_price_curves.json
└── data/            profiles, regulatory seed, public rate/vehicle data
```

`fathom.md` is the specification and governs. `docs/PRIME_DIRECTIVES.md` is a verbatim copy of §2
carried in-repo; if the two diverge, §2 governs.

---

## Reading order

1. [`docs/PRIME_DIRECTIVES.md`](docs/PRIME_DIRECTIVES.md) — the hard constraints, and which are
   enforced in code today
2. [`docs/DAY0_PROBE.md`](docs/DAY0_PROBE.md) — the probe that selects the build plan
3. [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — one entry per module
4. [`docs/OPEN_QUESTIONS.md`](docs/OPEN_QUESTIONS.md) — deferred decisions, with what blocks them
