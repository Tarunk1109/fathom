# FATHOM

**An evidence-grade instrument for the Ontario private-passenger auto insurance market.**

*Sound the market. Prove the bottom.*

FATHOM runs an agentic web executor against Ontario auto insurers under a hypothetical clean-record
driver profile, gates every proposed action through a deterministic policy engine before it ever
touches a real page, and turns every outcome — a price **or** a refusal — into an evidenced,
comparable, common-schema record. It measures the market rather than shopping it: a refusal with
its exact reason is as valuable an output as a price, and both are recorded with the same rigor.

Built for the **Ontario All-Quote Agent Challenge**, August 2026.
Operator: Tarun Karnati, Toronto, Ontario.

A twelve-slide presentation deck covering the same ground visually is at
[`out/FATHOM_deck.pptx`](out/FATHOM_deck.pptx).

---

## Table of contents

1. [Scope, stated plainly](#scope-stated-plainly)
2. [The honest summary](#the-honest-summary)
3. [How it works — the pipeline](#how-it-works--the-pipeline)
4. [The policy gate](#the-policy-gate)
5. [The UI — six views](#the-ui--six-views)
6. [The residual-market extraction](#the-residual-market-extraction)
7. [Setup](#setup)
8. [Judge-facing commands](#judge-facing-commands)
9. [Where to find each deliverable](#where-to-find-each-deliverable)
10. [The PII sweep](#the-pii-sweep)
11. [Tests](#tests)
12. [Repository layout](#repository-layout)
13. [Reading order](#reading-order)
14. [Known limitations](#known-limitations)

---

## Scope, stated plainly

FATHOM is a **personal-use agentic market instrument**. It is not a product, not a service, and not
for anyone but the operator. See [`LICENSE`](LICENSE) — it is **not** an open source licence and
grants no right of use, copy, modification, or redistribution to anyone else. It is published on
GitHub so that judges and challenge organizers can read and evaluate it; that visibility is not a
grant of use.

**What it does not do.** It does not bind, purchase, renew, cancel or modify a policy. It does not
submit payment information, an e-signature, or an application declaration. It does not bypass a
CAPTCHA, bot control, authentication, or rate limit — when the executor met one (Rates.ca,
LowestRates.ca), it recorded the block and stopped, it did not work around it. It does not compute,
estimate, or claim a premium anywhere in the codebase — not even in the residual-market extraction
feature, which surfaces real published rating **tables**, never a synthesized price. These are
enforced in code by the Policy Engine on every proposed action, not by convention or by a prompt
asking the model nicely. See [`docs/PRIME_DIRECTIVES.md`](docs/PRIME_DIRECTIVES.md) for the full
rule list and an honest, current statement of which rules are genuinely exercised by this build's
own operation versus tested-but-never-naturally-triggered.

**What its outputs are.** Records of observations — a price, a refusal, or an unresolved attempt —
each with a timestamp and content-addressed, redacted evidence pointing at exactly what produced
it. Not insurance advice, not offers, not quotes. Results retrieved under the hypothetical profile
are not quotes for the operator, and are labelled as hypothetical everywhere they appear, in the UI
and in every export. Friction (a refusal, a licence wall, a bot check) is recorded as an
observation only; FATHOM alleges no breach of any law or regulation by any party, anywhere.

---

## The honest summary

**No real insurer priced the hypothetical profile in this build.** Sonnet, reconnoitred by hand on
Day 0 and reproduced automatically in the sandbox, walled at a mandatory driver's-licence-number
field — a hypothetical profile cannot supply one, by design (`P-HYPO-LICENCE-01`, non-negotiable
per the brief). Rates.ca and LowestRates.ca sit behind a Cloudflare managed challenge, detected and
respected, never bypassed. belairdirect, RBC and Desjardins were retried at their actual
quote-entry URLs and each returned `unresolved` — a real capability limit in this build's
page-reading heuristics, stated plainly as such, not disguised as a market signal. The two
normalized outcomes that show visible coverage differences at a comparable price point are both
from the local synthetic sandbox, and are labelled `SANDBOX` everywhere they appear — in the UI, in
`results.json`, and in every export. No sandbox figure is ever presented as if it came from a real
insurer.

**What did ship:** a policy gate that every proposed action passes through, and that genuinely
denied real things during real runs (a licence-number field, an accuracy-attestation checkbox, a
time budget) — not just in a unit test; a web executor that fills real multi-step insurer forms,
handles a real mid-journey modal, and recaptures evidence live; a 70-brand market registry
collapsing to 67 distinct rate sources with one evidenced merger (the Aviva amalgamation, on two
independent signals); a fabricated-premium bug that was caught mid-build, fixed, and turned into a
reproducible regression demo rather than quietly patched away; a six-view UI built around one
honest visual metaphor (the Sounding Chart — see below); a prompt-injection resistance
demonstration; a retrieval-gated "ask your findings" question tool that refuses to call an LLM at
all when nothing relevant retrieves; and a scoped, provenance-first extraction of the real public
Facility Association residual-market rate manual that stops short of computing anything.
[`docs/LIMITATIONS.md`](docs/LIMITATIONS.md) states all of this in full, itemized detail — this
paragraph is the summary, not the substitute.

---

## How it works — the pipeline

```
intake → safety gate → route planner → executors → evidence chain → normalized results
```

Every proposed action — `navigate`, `fill`, `submit`, `dial` — is a structured object passed to
`PolicyEngine.evaluate()` before it is allowed anywhere near a real page, a real phone number, or a
real API. No executor code calls a browser directly; every call is gate-mediated. The gate returns
one of three verdicts and appends the decision to a hash-chained, concurrency-safe audit log:

| Verdict | Meaning | Downstream behaviour |
| --- | --- | --- |
| `ALLOW` | The action is permitted | Proceeds |
| `DENY` | The action is prohibited | The route ends there; recorded with the exact rule ID that fired |
| `ESCALATE` | A human checkpoint is required (identity verification, licensed advice, consent) | Route stays **open**, queued for the operator — not the same as a rejection |

From there: the route planner selects which registered rate source to attempt next within its
attempt/time budget; the web executor (Playwright-driven, structural page-reading rather than
brittle CSS selectors) fills the form and reads back the result; every fetched page and every
result is written to a content-addressed, sha256-chained evidence store *after* redaction, never
before; and the normalizer maps whatever came back onto one common schema — `blocked`,
`unresolved`, `callback_required`, or a priced outcome with coverage variance computed against a
fixed benchmark package — so two insurers' very different forms become one comparable record.

## The policy gate

The gate is code, not prompting. There is no LLM anywhere in the decision path — `PolicyEngine`
is deterministic Python, evaluated the same way every time against the same input, and every
decision is independently reproducible from the audit log alone.

**22 registered rules** — 21 `DENY`, 1 `ESCALATE` — covering the full Prime Directive list: no
bind/purchase/renew/cancel, no payment or signature submission, no CAPTCHA bypass, no licence
number under a hypothetical profile, no mixing of two profiles' fields in one submission, no real
destination touched without a recorded, payload-digest-bound operator approval, and more. Full list
and rationale: [`docs/PRIME_DIRECTIVES.md`](docs/PRIME_DIRECTIVES.md).

**Enforcement status is tracked honestly, not aspirationally.** Of the 22 rules, 19 are `LIVE` —
wired into this build's actual operation (`scripts/run_all.py`), not only exercised by a
constructed unit-test state. The remaining 3 are `PARTIAL`: fully implemented and tested, but their
one precondition (`profile_operator` — the operator's own vault-backed real identity — being run
against a destination) was deliberately never exercised, because the operator decided the marginal
evidence didn't justify entering real personal data into insurer systems hours before a deadline
(decision `D-OPER`, [`docs/DECISIONS.md`](docs/DECISIONS.md)). Nothing is marked `LIVE` before the
gate that enforces it demonstrably exists and fires. Run `make rules` to list every rule yourself,
`make demo` to watch one deny in real time, and `make verify` to re-check the audit chain's
integrity.

**No real destination is touched without a recorded, digest-bound payload approval**
(`P-APPROVAL-01`, default-deny). Every field of every payload sent to a real insurer was approved
in advance via `scripts/approve_payload.py`, which binds the approval to a sha256 digest of the
exact payload — an approval for one payload does not cover a different one. Six real routes were
approved and run this way: belairdirect, RBC Insurance, Desjardins, Rates.ca, LowestRates.ca, and
MyChoice.ca. Sonnet was reconnoitred by hand on Day 0, before this approval flow existed — its
licence-wall finding was reproduced automatically in the sandbox instead (see
[`docs/DAY0_PROBE.md`](docs/DAY0_PROBE.md)).

**The audit chain itself is hash-chained and independently re-verifiable.** Each entry carries the
previous entry's hash; `AuditLog.verify_chain()` (and the browser-side "Verify chain" button in the
UI's **Gate** view, which recomputes every entry's SHA-256 in-browser via the Web Crypto API — no
server round-trip) walk the whole chain and report the first broken link, if any. A real
concurrency bug in this exact mechanism (two processes computing the same next index under
concurrent writes) was found by testing during this build, fixed with file-locking and a
fresh-read-under-lock, and is covered by a dedicated 6-process stress test
(`tests/test_audit_concurrency.py`) — see [`docs/SAFETY.md`](docs/SAFETY.md).

---

## The UI — six views

`ui/index.html` is a single static file: data is embedded as JSON at build time
(`scripts/build_ui.py`), so it opens correctly from a plain double-click (`file://`) with no server
and no build step — vanilla JS throughout, no framework. Six views, one landing metaphor:

| View | What it shows |
| --- | --- |
| **Sounding** | The landing view and the instrument's whole thesis in one chart. Every rate source is drawn as a line dropping from a horizontal "surface," terminating at the deepest real pipeline stage it actually reached (`entry → intake → vehicle → driver → coverage → price`), colour-coded by why it stopped. Depth is derived from real field-stage data the executor actually filled — never an invented per-site label. A metric row and an honest scorecard sit below the chart. |
| **Outcomes** | Every retrieved result, sortable, with coverage variance rendered **above** the price line — a cheaper sandbox result is visibly a different insurance product, not a better deal, and that is never hidden below the fold. |
| **Market** | The brand-collapse graph: 70 market brands and legal entities resolve to 67 distinct rate sources. Click any node for the evidence behind a merge. A lens toggle switches between brand / distributor / legal-underwriter / insurer-group groupings. The residual-market extraction panel (see below) lives at the bottom of this view. |
| **Frontier** | The Eligibility Frontier: every refusal reason, inverted into "what would have to change to unlock this." Currently one real, evidenced rung — stated as honestly thin, not oversold. |
| **Gate** | The full policy-decision log in sequence, filterable by rule, plus the live enforcement-status table and the in-browser chain-verification control. |
| **Evidence** | Every content-addressed evidence artifact this build collected, with its redacted text excerpt and its own hash-chain verification. |

---

## The residual-market extraction

Ontario's Facility Association is the market's insurer of last resort — by regulation it must
accept any eligible applicant a voluntary-market insurer declines, which is exactly why its Manual
of Rules and Rates is a public document rather than proprietary underwriting criteria. FATHOM
parses the real, current, publicly published manual (`ON_Manual_Effective_November_1_2025.pdf`,
1,606 pages) — but **only extracts what parses cleanly and unambiguously, and only extracts
lookup tables, never a rate**.

The one table type that met that bar: the **territory-definitions lookup** (municipality → numeric
territory code and statistical code), yielding **6,440 rows**, each carrying its source page number
and table name — no row without provenance. Every other candidate section was tried and explicitly
rejected as too ambiguous to extract without guessing: vehicle rate-group tables spanning hundreds
of pages with no stable column structure across manufacturers; annual-premium tables whose cells
pack multiple stacked rate-group figures with no unambiguous delimiter; driver-class rules, which
are prose, not tabular data. Full account, including exactly what was tried and why it was left
out: [`docs/RESIDUAL_MARKET.md`](docs/RESIDUAL_MARKET.md).

**This is never a quote, an estimate, or a premium**, and the codebase computes no dollar figure
from it anywhere. `out/residual_manual_extract.json` and the UI panel that displays it are both
hard-labelled `UNVERIFIED EXTRACTION` — real placement in the residual market requires a licensed
insurance broker or intermediary, which FATHOM is not and does not simulate.

---

## Setup

```bash
git clone https://github.com/Tarunk1109/fathom.git
cd fathom

python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m playwright install chromium

make hooks     # optional: runs the PII sweep automatically before every commit
```

Requires **Python 3.12+**. Three dependencies, each added at the milestone that introduced it —
see [`requirements.txt`](requirements.txt) and [`docs/DECISIONS.md`](docs/DECISIONS.md) for the
rationale behind each:

| Dependency | Why |
| --- | --- |
| `cryptography` | Fernet encryption at rest for the operator vault |
| `playwright` | The web executor — real browser automation, structural page reading |
| `pdfplumber` | One-time, offline table extraction from the residual-market manual |

Everything upstream of the executor — the policy gate, the audit chain, the PII sweep — is
**stdlib-only Python**, so the safety-critical path has zero third-party dependency surface. The
`ui/` folder has no dependency and no build step at all.

**Optional — for "Ask Your Findings" (`make ask`) only.** Create a local, gitignored `.env`:

```bash
echo "ANTHROPIC_API_KEY=sk-ant-..." > .env
```

The key is read server-side by a minimal stdlib `.env` parser, never embedded in `ui/index.html` or
any other client-side file, never committed, and never printed after it's read — see
[`docs/DECISIONS.md`](docs/DECISIONS.md) `DL-26` for why this is a CLI tool and not a live text box
in the browser. Every other command below works with no API key at all.

`make` targets below assume the venv is active, or call `.venv/bin/python` directly as shown by
each target.

---

## Judge-facing commands

```bash
make check              # sweep + test  →  161 tests, zero PII findings across 212 files
make sandbox             # start the 7 synthetic insurer sites on :8801 (needed by `make run`)
make run                 # the full pipeline: execute → normalize → dedup → export → build UI
make demo                # the gate, demonstrated: a denied bind, rule ID + chain index,
                          #   then chain verification, then a deliberate tamper to show it can fail
make demo-fabrication    # the fabricated-premium incident, reproduced against real captured
                          #   content — the old buggy reader vs. the fix, side by side
make demo-injection      # a hidden prompt-injection payload, observed in evidence, never acted on
make ask Q="..."         # natural-language questions over FATHOM's own evidence, retrieval-gated
                          #   (needs ANTHROPIC_API_KEY in .env — see Setup)
make verify              # re-verify the policy audit chain, judge-facing, no code reading required
make rules                # list every registered policy rule and what it denies
make build-ui             # rebuild only the UI from whatever is already in out/, without
                          #   re-running every route
make sweep                # PII sweep across the whole repo, including out/ and docs/
make test                 # unit tests only (stdlib unittest)
```

Run `make sandbox` in one terminal, then `make run` in another to regenerate every deliverable —
`out/registry.json`, `out/results.json`, `out/run_report.md`, `ui/index.html`, and the residual
manual panel — from a live pipeline run. `make demo`, `make demo-fabrication`, `make demo-injection`
and `make verify` are self-contained and need nothing else running, and none of them touch the real
audit log or a real insurer.

After `make run`, open `ui/index.html` directly in a browser (double-click works, `file://` and
all) — or `make ui` does the same and opens it for you.

---

## Where to find each deliverable

| Deliverable | Path |
| --- | --- |
| Machine-readable market registry | `out/registry.json`, `out/registry.csv` |
| Normalized outcomes, common schema | `out/results.json` |
| Redacted run report — named findings, coverage ledger, metrics | `out/run_report.md` |
| Residual-market extraction, provenanced | `out/residual_manual_extract.json` |
| Six-view UI (Sounding / Outcomes / Market / Frontier / Gate / Evidence) | `ui/index.html` |
| Presentation deck (12 slides, real screenshots, speaker notes) | `out/FATHOM_deck.pptx` |
| Architecture and safety notes | `docs/ARCHITECTURE.md`, `docs/SAFETY.md` |
| Known limitations, stated plainly | `docs/LIMITATIONS.md` |
| Residual-market extraction explainer | `docs/RESIDUAL_MARKET.md` |
| Day 0 hand-run probe record | `docs/DAY0_PROBE.md` |
| Demo walkthrough script (recording-ready, timed beats) | `docs/DEMO_SCRIPT.md` |
| Build-time decisions log, with rationale for every call | `docs/DECISIONS.md` |
| Open questions, incidents, spec amendments | `docs/OPEN_QUESTIONS.md` |
| The hard constraints, verbatim, and current enforcement status | `docs/PRIME_DIRECTIVES.md` |
| Hash-chained policy audit log (raw) | `out/audit/policy_audit.jsonl` |
| Hash-chained, content-addressed evidence store (raw) | `out/evidence/` |

---

## The PII sweep

The hard constraint — no real licence number, full address, payment data, or raw call audio
anywhere in the repo, logs, prompts, traces, screenshots, or exports — is enforced by a check that
runs identically in CI and locally, and gates every commit if `make hooks` is installed.

```bash
make sweep                       # scan the whole repo, including out/ and docs/
python3 tools/pii_sweep.py       # identical, no make required
python3 tools/pii_sweep.py --list-rules
python3 tools/pii_sweep.py --json
```

Exit code `0` clean, `1` on any finding. Eight rule classes — `DL_ONTARIO`, `PC_FULL_POSTAL`,
`VIN`, `PHONE_NANP`, `EMAIL`, `PAYMENT_CARD`, `STREET_ADDRESS`, `DOB_LABELLED` — each permitting the
specific *redacted* forms this project actually records (an FSA like `M5V`, a bare birth year, a
licence class like `G1`), never a real value. Findings are reported as file/line/rule and a masked
excerpt, **never the matched value itself**. Binary files are listed for manual review, never
silently skipped. Three real false-positive classes were found and fixed against real content
during this build (a header-scoped pragma leak, and two hex-digest collisions) — see
[`docs/SAFETY.md`](docs/SAFETY.md). Current state: **212 text files scanned, zero findings.**

---

## Tests

```bash
make test          # python3 -m unittest discover -s tests
```

Stdlib `unittest`, no test framework dependency. **161 tests**, including: a real 6-process
concurrency stress test for the audit and evidence chains
(`tests/test_audit_concurrency.py`); a regression test for the fabricated-premium fix
(`tests/test_price_reader.py`); full denial/over-block pairs for every gate rule
(`tests/test_policy_rules.py`, `tests/test_policy_engine.py`); and a test that structurally
verifies "Ask Your Findings" refuses to call the model at all when nothing relevant retrieves
(`tests/test_ask_findings.py`) — the retrieval gate is enforced in code, not by a prompt
instruction alone.

---

## Repository layout

```
fathom/
├── fathom.md              the specification — governs
├── finish.md               the completion instruction one build pass executed
├── final.md                 the UI-overhaul-plus-features instruction a later pass executed
├── ppt.md                    the instruction that produced out/FATHOM_deck.pptx
├── LICENSE                    personal-use-only, not open source — see Scope above
├── README.md                   this file
├── requirements.txt
├── Makefile                    every judge-facing command; see above
│
├── docs/
│   ├── PRIME_DIRECTIVES.md      the hard constraints, verbatim, + current enforcement status
│   ├── ARCHITECTURE.md           the pipeline as it actually runs, module by module
│   ├── SAFETY.md                  including the fabricated-premium incident, worked in full
│   ├── LIMITATIONS.md              written honestly, itemized, no hedging
│   ├── RESIDUAL_MARKET.md          what the manual extraction is and is not
│   ├── DAY0_PROBE.md                the hand-run reconnaissance before any executor existed
│   ├── DEMO_SCRIPT.md                recording-ready walkthrough, one command per beat
│   ├── DECISIONS.md                   every build-time judgment call, with rationale
│   └── OPEN_QUESTIONS.md               organizer Q&A, incidents, spec amendments
│
├── packages/
│   ├── policy/               the gate — actions, rules, hash-chained audit log, engine
│   ├── profiles/              profile registry — hypothetical/sandbox/operator, as records not code
│   ├── vault/                  encrypted operator store (Fernet, key held outside the repo)
│   ├── evidence/                 content-addressed, hash-chained evidence store
│   ├── redactor/                  regex redaction — shares its rule set with the PII sweep
│   ├── registry/                   market registry, brand → distinct-rate-source dedup
│   ├── executors/web/               the web executor — every action gate-mediated, no exceptions
│   ├── normalizer/                    common outcome schema, PASS/CAUTION/FAIL, coverage parity
│   └── rater/, analysis/, planner/, mcp/, intake/
│       reserved scaffold directories from the initial milestone, intentionally never populated
│       — no MCP servers or planner/rater code exist in this build; see docs/ARCHITECTURE.md
│       "MCP servers" section for why, stated plainly rather than silently dropped
│
├── sandbox/server.py         7 synthetic insurer sites — the only thing `make demo`-adjacent
│                                commands are ever allowed to run automated form-fills against
│                                without an explicit payload approval
│
├── scripts/
│   ├── run_all.py              orchestration: execute every registered route → normalize →
│   │                              dedup → export → rebuild the UI
│   ├── build_ui.py               rebuilds ui/index.html from whatever is already in out/
│   ├── extract_residual_manual.py  the one-time, offline Facility Association manual parse
│   ├── ask_findings.py            retrieval-gated Q&A over FATHOM's own evidence
│   ├── demo_gate.py, demo_fabrication.py, demo_injection.py, verify_chain.py
│   │                                self-contained, judge-facing demonstrations
│   ├── approve_payload.py, prepare_payload.py    the payload-approval flow (P-APPROVAL-01)
│   ├── build_seed.py                registry seed construction from evidenced sources
│   └── run_route.py                  single-route runner, used for targeted re-runs
│
├── ui/                        the six-view static UI — vanilla JS, no framework, no build step
│   ├── _shell.html               page skeleton; scripts/build_ui.py injects the data blob
│   ├── app.js                     all view logic
│   ├── styles.css                  FATHOM's design tokens (abyss/deep/shelf/chart/sounding/…)
│   └── index.html, data.json       generated by `make run` / `make build-ui` — do not hand-edit
│
├── tools/pii_sweep.py         the PII sweep, shared by CI, the pre-commit hook, and `make sweep`
│
├── tests/                     stdlib unittest, 161 cases — see Tests above
│
├── data/
│   ├── profiles/                the three profile records (hypothetical / operator / sandbox sim)
│   └── seed/                      registry seed data — Appendix A plus independently evidenced rows
│
├── out/                        every generated deliverable — registry, results, run report,
│                                   residual-market extract, presentation deck, audit + evidence
│                                   chains, sandbox fixtures. Tracked in git on purpose: this is
│                                   the submission.
│
└── .github/workflows/ci.yml   CI: the PII sweep and the full test suite, on every push
```

`fathom.md` is the specification and governs. `finish.md` and `final.md` are the completion
instructions two later build passes executed top to bottom; `ppt.md` is the instruction behind the
presentation deck. `docs/PRIME_DIRECTIVES.md` is a verbatim copy of `fathom.md` §2 carried in-repo
for judges who don't want to read the full specification; if the two ever diverge, `fathom.md` §2
governs and the copy is the defect.

---

## Reading order

1. [`docs/DEMO_SCRIPT.md`](docs/DEMO_SCRIPT.md) — the fastest way to see everything that matters,
   one command or view per beat, nothing to hunt for
2. [`out/FATHOM_deck.pptx`](out/FATHOM_deck.pptx) — the same ground, visually, in twelve slides
3. [`docs/PRIME_DIRECTIVES.md`](docs/PRIME_DIRECTIVES.md) — the hard constraints and an honest,
   current statement of what actually enforces each one today
4. [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — the pipeline as it actually runs, one section
   per module, and an explicit, non-euphemistic "not built" list
5. [`docs/SAFETY.md`](docs/SAFETY.md) — including the fabricated-premium incident and every other
   control that failed open and was caught during this build, not swept under the rug
6. [`docs/LIMITATIONS.md`](docs/LIMITATIONS.md) — written honestly, itemized, no hedging language
7. [`docs/RESIDUAL_MARKET.md`](docs/RESIDUAL_MARKET.md) — the manual extraction, in full
8. [`docs/DAY0_PROBE.md`](docs/DAY0_PROBE.md) — the hand-run reconnaissance that mapped Sonnet's
   licence wall before any executor existed
9. [`docs/DECISIONS.md`](docs/DECISIONS.md) and
   [`docs/OPEN_QUESTIONS.md`](docs/OPEN_QUESTIONS.md) — every build-time judgment call, spec
   amendment, and incident, each with its rationale attached

---

## Known limitations

Stated in full, itemized detail in [`docs/LIMITATIONS.md`](docs/LIMITATIONS.md) — headline items:
no real insurer route returned a price under the hypothetical profile; two aggregators are
Cloudflare-fronted and were not bypassed; three direct writers hit this build's own page-reading
capability limit rather than an evidenced market refusal; `profile_operator` was deliberately never
run against any real destination; the Eligibility Frontier currently has exactly one populated
rung; and a full list of features scoped out of this build entirely (a voice executor, a rulebook
compiler / computed premium, a benefit price probe, vehicle inversion, channel arbitrage, a dark
pattern detector) — omitted deliberately rather than shipped half-built, on the stated principle
that a smaller number of trustworthy results with excellent evidence beats a fuller-looking report
with silent guesses inside it.
