# FATHOM

**An evidence-grade instrument for the Ontario private-passenger auto insurance market.**

FATHOM runs an agentic web executor against Ontario auto insurers under a hypothetical clean-record
driver profile, gates every action through a deterministic policy engine before it touches a real
page, and turns every outcome — a price or a refusal — into evidenced, comparable, common-schema
records. It measures the market rather than shopping it: a refusal with its exact reason is as
valuable an output as a price.

Built for the Ontario All-Quote Agent Challenge, August 2026.
Operator: Tarun Karnati, Toronto, Ontario.

---

## Scope, stated plainly

FATHOM is a **personal-use agentic market instrument**. It is not a product, not a service, and not
for anyone but the operator. See [`LICENSE`](LICENSE) — it is not an open source licence and grants
no right of use to anyone else. Judges and challenge organisers have read access for evaluation
only.

**What it does not do.** It does not bind, purchase, renew, cancel or modify a policy. It does not
submit payment information, an e-signature, or an application declaration. It does not bypass a
CAPTCHA, bot control, authentication or rate limit — when the executor met one (Rates.ca,
LowestRates.ca), it recorded the block and stopped. These are enforced in code by the Policy
Engine on every proposed action, not by convention. See
[`docs/PRIME_DIRECTIVES.md`](docs/PRIME_DIRECTIVES.md) for the full rule list and which parts are
genuinely exercised by this build versus merely tested.

**What its outputs are.** Records of observations with timestamps and content-addressed, redacted
evidence. Not insurance advice, not offers, not quotes. Results retrieved under the hypothetical
profile are not quotes for the operator and are labelled as hypothetical everywhere they appear.
Friction is recorded as observation only; FATHOM alleges no breach of any law or rule by any party.

---

## The honest summary

No real insurer priced the hypothetical profile in this build. Sonnet, reconnoitred by hand on Day
0, walled at a mandatory driver's licence number field — a hypothetical profile cannot supply one,
by design (`P-HYPO-LICENCE-01`). Rates.ca and LowestRates.ca sit behind a Cloudflare managed
challenge, detected and respected, never bypassed. belairdirect, RBC and Desjardins were retried at
their actual quote-entry URLs and each returned `unresolved` — a real capability limit in this
build's page-reading heuristics, not a market signal, stated as such. The two normalized outcomes
that show visible coverage differences at a common price point are both from the local synthetic
sandbox, clearly labelled `SANDBOX` everywhere they appear.

What did ship: a policy gate that every proposed action passes through and that genuinely denied
real things during real runs (a licence-number field, an accuracy-attestation checkbox, a time
budget); an executor that fills real multi-step insurer forms, handles a real mid-journey modal, and
recaptures evidence live; a 70-brand registry collapsing to 67 distinct rate sources with one
evidenced merger (the Aviva amalgamation); and a fabricated-premium bug that was caught, fixed, and
turned into a demonstrable regression test rather than quietly patched away. `docs/LIMITATIONS.md`
states all of this in full, itemized detail — this paragraph is the summary, not the substitute.

---

## Setup

```bash
git clone <repo> fathom && cd fathom
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m playwright install chromium
make hooks     # optional: run the PII sweep automatically before every commit
```

Requires Python 3.12+. Two dependencies, each added at the milestone that introduced it
(`cryptography` for the vault, `playwright` for the web executor) — see `requirements.txt` and
`docs/DECISIONS.md`. Everything before the executor (the policy gate, the PII sweep) is stdlib
only, so the safety check runs before any dependency exists.

`make` targets below assume the venv is active, or call `.venv/bin/python` directly as shown.

---

## Judge-facing commands

```bash
make check              # tests + PII sweep — sweep + test  →  152+ tests, zero PII findings
make sandbox             # start the 7 synthetic insurer sites on :8801 (needed by `make run`)
make run                 # the full pipeline: execute → normalize → dedup → export → build UI
make demo                # the gate: a bind attempt denied, rule ID + chain index, then chain
                          #   verification, then a deliberate tamper to show the check can fail
make demo-fabrication    # the fabricated-$177.83-premium incident, reproduced against real
                          #   captured content, old buggy reader vs. the fix, side by side
make verify              # judge-facing chain verification, no code reading required
make rules                # list every registered policy rule and what it denies
```

Run `make sandbox` in one terminal, then `make run` in another to regenerate every deliverable
from a live pipeline run. `make demo` and `make demo-fabrication` need nothing else running.

---

## Where to find each deliverable

| Deliverable | Path |
| --- | --- |
| Machine-readable market registry | `out/registry.json`, `out/registry.csv` |
| Normalized outcomes, common schema | `out/results.json` |
| Redacted run report (metrics, findings, coverage ledger) | `out/run_report.md` |
| Three-view UI (results / market graph / policy gate) | `ui/index.html` |
| Architecture and safety note | `docs/ARCHITECTURE.md`, `docs/SAFETY.md` |
| Known limitations | `docs/LIMITATIONS.md` |
| Day 0 probe record | `docs/DAY0_PROBE.md` |
| Demo walkthrough script | `docs/DEMO_SCRIPT.md` |
| Build-time decisions log | `docs/DECISIONS.md` |
| Open questions, incidents, spec amendments | `docs/OPEN_QUESTIONS.md` |

---

## The gate

Everything routes through the Policy Engine (§7.1 of `fathom.md`). No executor calls a browser,
phone or API directly — every proposed action is a structured object submitted to
`PolicyEngine.evaluate()`, which returns `ALLOW`, `DENY` or `ESCALATE` plus the rule that fired, and
appends the decision to a hash-chained, concurrency-safe audit log.

19 deny rules, 1 escalate rule. Deterministic — no LLM in the decision path. Full list and current
enforcement status (which rules are exercised by this build's real operation, not only unit-tested)
in [`docs/PRIME_DIRECTIVES.md`](docs/PRIME_DIRECTIVES.md).

Three verdicts, different downstream behaviour: `ALLOW` proceeds. `DENY` refuses and the route
ends. `ESCALATE` sends the request to a checkpoint queue and **leaves the route open** — a
representative requiring identity verification or coverage advice is not the same as a rejection.

**No real destination is touched without a recorded, digest-bound payload approval**
(`P-APPROVAL-01`, default deny — see `scripts/approve_payload.py`). Six real routes were approved
this way: belairdirect, RBC Insurance, Desjardins, Rates.ca, LowestRates.ca, MyChoice.

---

## The PII sweep

The hard constraint — no real licence number, full address, payment data or raw call audio
anywhere in the repo, logs, prompts, traces, screenshots or exports — is enforced by a check that
runs identically in CI and locally.

```bash
make sweep                       # scan the whole repo, including out/ and docs/
python3 tools/pii_sweep.py       # identical, no make required
python3 tools/pii_sweep.py --list-rules
python3 tools/pii_sweep.py --json
```

Exit code 0 clean, 1 on findings. Eight rule classes (`DL_ONTARIO`, `PC_FULL_POSTAL`, `VIN`,
`PHONE_NANP`, `EMAIL`, `PAYMENT_CARD`, `STREET_ADDRESS`, `DOB_LABELLED`), each permitting the
specific redacted forms this project actually records (an FSA like `M5V`, a bare birth year, a
licence class like `G1`). Findings are reported as file/line/rule and a masked excerpt, never the
matched value. Three real false-positive classes were found and fixed against real content during
this build (a header-scoped pragma leak, and two hex-digest collisions) — see `docs/SAFETY.md`.

---

## Tests

```bash
make test          # python3 -m unittest discover -s tests
```

Stdlib `unittest`, no test framework dependency. 150+ cases, including a real 6-process concurrency
stress test for the audit and evidence chains (`tests/test_audit_concurrency.py`), a regression
test for the fabricated-premium fix (`tests/test_price_reader.py`), and a test that sweeps the live
repository for PII on every run.

---

## Layout

```
fathom/
├── fathom.md          the specification — governs
├── finish.md           the final-completion instruction this pass executed
├── docs/               PRIME_DIRECTIVES, ARCHITECTURE, SAFETY, LIMITATIONS, DAY0_PROBE,
│                        DEMO_SCRIPT, DECISIONS, OPEN_QUESTIONS
├── packages/
│   ├── policy/          the gate — actions, rules, audit chain, engine
│   ├── profiles/        profile registry — records, not code paths
│   ├── vault/            encrypted operator store (Fernet)
│   ├── evidence/         content-addressed, hash-chained evidence chain
│   ├── redactor/          regex redaction, shares rules with the PII sweep
│   ├── registry/          market registry, §9.3 fingerprinting/dedup
│   ├── executors/web/     the web executor — every action gate-mediated
│   └── normalizer/        common schema, PASS/CAUTION/FAIL, parity
├── sandbox/              7 synthetic insurer sites
├── scripts/              run_all, demo_gate, demo_fabrication, verify_chain,
│                          approve_payload, prepare_payload, build_seed
├── ui/                   the three-view static UI
├── tools/pii_sweep.py
├── tests/
├── out/                  every deliverable this pipeline produces
└── data/                 profiles, registry seed (Appendix A + evidenced rows)
```

`fathom.md` is the specification and governs. `finish.md` is the completion instruction this final
pass executed top to bottom. `docs/PRIME_DIRECTIVES.md` is a verbatim copy of `fathom.md` §2 carried
in-repo; if the two diverge, `fathom.md` §2 governs.

---

## Reading order

1. [`docs/DEMO_SCRIPT.md`](docs/DEMO_SCRIPT.md) — the fastest way to see everything that matters
2. [`docs/PRIME_DIRECTIVES.md`](docs/PRIME_DIRECTIVES.md) — the hard constraints and what actually
   enforces them today
3. [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — the pipeline as it actually runs, one section
   per module, and an explicit "not built" list
4. [`docs/SAFETY.md`](docs/SAFETY.md) — including the fabricated-premium incident and every other
   control that failed open and was caught
5. [`docs/LIMITATIONS.md`](docs/LIMITATIONS.md) — written honestly, itemized, no hedging
6. [`docs/DAY0_PROBE.md`](docs/DAY0_PROBE.md) — the hand-run reconnaissance that mapped Sonnet's
   licence wall before any executor existed
7. [`docs/DECISIONS.md`](docs/DECISIONS.md) and [`docs/OPEN_QUESTIONS.md`](docs/OPEN_QUESTIONS.md)
   — every build-time judgment call, amendment and incident, with rationale
