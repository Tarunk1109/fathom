# Safety note

Deliverable per FATHOM §15. **Populated as each mechanism is built** — this file states what is
enforced today, not what is intended. A claim without a gate behind it is the failure mode this
document exists to prevent (§7.1: the safety claim must be demonstrable rather than aspirational).

The authoritative constraint list is [`PRIME_DIRECTIVES.md`](PRIME_DIRECTIVES.md), a verbatim copy
of §2. That file also carries the enforcement-status table tracking which mechanism exists.

---

## Enforced today (Milestone 1)

### No PII in the repository, logs or submission

§2.1: *never let a real licence number, full address, payment data or raw call audio reach the
repo, logs, prompts, traces, screenshots or the submission.*

- `tools/pii_sweep.py` scans every text file under the repository root, including `out/` and
  `docs/`, and exits non-zero on a hit.
- Runs in CI on every push and pull request, and locally via `make sweep` or the optional
  pre-commit hook (`make hooks`). One implementation, invoked identically in both places.
- Findings are reported as file, line, rule and a **masked** excerpt. The sweep never prints the
  value it found; doing so would write PII into CI logs.
- Binary files are listed for manual review rather than silently skipped, so the tool does not
  imply coverage it lacks.
- `.gitignore` additionally refuses raw audio, pre-redaction staging directories, the vault
  directory and secrets by pattern.

**Limits, stated honestly.** Regex cannot see inside an image, cannot detect an address written in
prose, and cannot catch a value split across lines. This check is a floor. The local redactor
(Milestone 3) is the actual defence, and §15.1 still requires a manual sweep of screenshots and the
recorded walkthrough before submission.

#### Three design decisions, and why

Recorded because the reasoning matters more than the code, and because each one is a place where
the obvious implementation is the wrong one. Approved by the operator 2026-08-09.

**1. The sweep reports a masked excerpt, never the matched value.**
A checker that prints PII into CI logs defeats itself. The finding would be duplicated into build
output, job artifacts and anywhere those logs are shipped — turning a single leak into several, in
places that are harder to purge than the source file. File, line, rule and a masked excerpt are
enough to locate and fix a hit. The value itself adds nothing a developer with the file open does
not already have.

**2. Binary files are listed for manual review, not skipped silently.**
A screenshot, a PDF or a call recording cannot be grepped. Passing over them quietly would let the
sweep report `PASS` on a repository containing an unredacted screenshot, which is worse than having
no sweep at all, because it manufactures false confidence. §15.1 requires the final sweep to cover
screenshots and the recorded walkthrough, so the tool names every file it could not read and leaves
the check with a human. **A tool must not imply coverage it does not have.**

**3. The rules permit the redacted forms actually recorded.**
An FSA such as `M5V` does not trip `PC_FULL_POSTAL`; a bare birth year does not trip
`DOB_LABELLED`; a licence class such as `G1` does not trip `DL_ONTARIO`. These are exactly the
forms the Day 0 redaction rules and §9.6 tell the operator to write down. A checker that forbids
the redacted form gives its user a choice between complying with the redaction policy and passing
CI — and the reliable outcome of that choice is that the work moves outside the checker, into
untracked notes and unswept files. **A gate that punishes correct behaviour gets routed around.**

The same principle produced the fix for the one defect found in testing: a line can legitimately
trip two rules, so the allow-pragma takes a comma-separated rule list. Narrowing a single line
beats loosening a rule for the whole repository.

### Personal use only

§2.1: *never sell, license, publish for public use, or deploy this as a service.*

- [`LICENSE`](../LICENSE) is not an open source licence. It grants no right of use to anyone but
  the operator, and grants judges read access for evaluation only.
- Licence clauses 4(e)–(i) restate the system's hard constraints — no binding, no payment or
  signature submission, no CAPTCHA or auth bypass, no fabricated licence number, and no disabling
  of the Policy Engine, redaction layer, disclosure prelude, consent state machine or evidence
  chain — so the licence and the running code say the same thing.
- `README.md` states the scope and the boundary in the first screen.

### The Policy Engine (Milestone 2)

Every proposed action passes a deterministic gate before any executor acts. 18 deny rules plus one
escalate rule, evaluated in a fixed, documented order, first match wins. **No LLM in the decision
path** — the same action in the same session always produces the same verdict, which is the only
reason the audit log means anything.

Every decision, allow or deny, appends to a hash-chained append-only log. `make verify` recomputes
the chain and reports the first divergence; `make demo` shows a bind attempt being denied with its
rule ID and chain index, then verifies the chain, then tampers with it on disk to show the check
failing. A verification that has never been seen to fail is not evidence of anything.

**The audit log cannot carry PII.** It stores payload field *names* and a SHA-256 digest — never a
value — strips query strings and fragments from targets, and scrubs caller rationale through the
same rule set as the PII sweep. A test writes a deliberately PII-laden action and then runs the
real sweep over the resulting file.

**Over-blocking is treated as a failure, not a safe default.** Every rule carries a test proving it
permits the nearest legitimate neighbour: recording that a CAPTCHA was encountered, filling
`payment_frequency` and `down_payment`, entering a licence *class*, varying a coverage deductible,
viewing a declarations page, running a hypothetical profile against a real quote form. Those cases
assert `ALLOW` outright, so a neighbour caught by any other rule fails too.

See `docs/PRIME_DIRECTIVES.md` for the per-directive enforcement status, including the rules that
are live but read session state a later milestone populates.

### Day 0 probe conduct

The viability probe (§5) runs by hand, with the operator's own real information, and stops at the
first wall on every route. No automation touched a real insurer during the probe. Per OQ-004, **no
screenshots were taken**: the local vision redactor was never built (see below), §2.1 makes an
unredacted screenshot a hard failure, and verbatim redacted quotes satisfy the evidence requirement
on their own.

### The vault, evidence chain and redactor (Milestone 3)

- **Vault:** Fernet symmetric encryption, key held at `~/.fathom/vault.key` (0600), outside the
  repository. `inject()` returns values wrapped in `FieldValue(value, source_profile_id)` — never a
  raw string into a payload — so anything the vault supplies is provenanced and
  `P-PROFILE-BLEED-01` can see it. `value_hashes()` exposes hashes only, so the profile registry can
  detect an operator value pasted into a synthetic profile without ever handling the plaintext.
- **Evidence chain:** sha256 content address of *redacted* bytes, prev-hash chained, append-only
  JSONL — the same construction as the policy audit chain, for the same reason. `append()` runs the
  redactor itself; there is no code path that stores a raw byte.
- **Redactor:** regex only, reusing the PII sweep's rule set so detection and redaction cannot
  drift apart (DL-04). **No vision model was built.** Screenshots are excluded from the submission
  per OQ-004, so vision redaction has no consumer — a real scope decision, not an oversight, made
  and logged as DL-04 in `docs/DECISIONS.md`.

### Profile bleed — INC-001 and its rules (Milestone 3)

On 2026-08-09, during a hand-driven hypothetical-profile pass, a real third-party address was
entered mid-journey and an address-accuracy attestation checkbox was ticked. Nothing was submitted.
Root cause: a hypothetical profile was populated with real-world data, and no gate covered the
mixing because it happened outside the system entirely.

Three rules close this, all live and tested:

- **`P-PROFILE-BLEED-01`** — every submitted field carries a `source_profile_id`; a single action
  must resolve to exactly one profile, or it is denied and both profiles are named in the denial.
- **`P-HYPO-ATTEST-01`** — no accuracy, truthfulness or fraud-acknowledgement control may be
  actioned under a hypothetical profile. Emits `manual_handoff`.
- **`P-APPROVAL-01`** — no real-destination action proceeds on a route without a recorded operator
  approval of that route's exact intended payload (`scripts/approve_payload.py`), bound to the
  payload's content digest so a changed payload invalidates the approval. Default deny.

Full record: `docs/OPEN_QUESTIONS.md`, incident INC-001.

### The web executor and route budgets (Milestone 4)

Every action the executor proposes — navigate, fill, click, submit — is submitted to
`PolicyEngine.evaluate()` before Playwright touches the page. There is no direct browser call in
`packages/executors/web/executor.py` that bypasses the gate. Modals are polled before every action
and logged with their text (not caught as exceptions), and a per-route wall-clock deadline
(`RouteBudget.deadline`, §9.4) stops a stalled real-page run rather than hanging indefinitely.

---

## Worked example: the fabricated premium

**The most important entry in this document, because the failure actually happened.**

On 2026-08-11, during a live run against MyChoice.ca (a comparison platform) under
`profile_hypo_clean`, the price reader (`WebExecutor._read_price`) returned `$177.83` as a quoted
premium. **Zero form fields had been submitted at that point.** The figure was scraped from
marketing copy on the landing page — a "recent quotes" ticker showing example premiums for
unrelated applicants — not a response to anything FATHOM had sent. It was one run away from being
written into `out/results.json` and presented as a retrieved rate.

**Why it was wrong.** The old reader had no concept of *whether a submission had occurred*. It
searched the whole page's rendered text for anything shaped like `$X,XXX.XX` and believed the first
match, whether that match sat inside an explicit price container or inside ad copy above a form the
agent had not yet touched. A landing page advertising "rates from $94/month" and a comparison
platform's own social-proof table of other people's example quotes are exactly the kind of content
that shape-matches a real price and means nothing.

**The three-part fix**, in `WebExecutor._read_price` and its call site in `_walk`:

1. **Precondition: a price is only read if this run actually filled at least one field.**
   `any(step.fields_filled for step in result.steps)` gates the call entirely — no field filled,
   no price believed, regardless of what the page contains.
2. **Prefer an explicit price container.** The reader looks for `.price`,
   `[data-testid*=premium]`, `[class*=quote-price]` and similar selectors before ever falling back
   to free page text.
3. **Reject figures adjacent to advertising language.** Even in the free-text fallback, a match
   next to phrases like "as low as", "starting at", "from $", "average", "save up to" is refused.

**What this demonstrates.** A system that returns numbers is not the same as a system that returns
evidence. A price with no submission behind it is not a quote, and the executor now knows that
structurally — as a precondition checked in code before any figure is trusted — rather than by
convention or by hoping the page never carries a number that looks like one. §6.1 states plainly
that a single invented number ends the submission; this control exists because the failure actually
occurred, not because it was anticipated in advance.

**Reproduce it:**

```
make demo-fabrication
```

Runs the old (quarantined, never imported from the executor) and current readers side by side
against a real, honestly captured artifact of the actual MyChoice landing page — see
`out/fixtures/fabrication_demo/manifest.json` for exactly what was recaptured and why the
byte-identical original artifact was not retained. `tests/test_price_reader.py` locks the fix down
as an assertion.

---

## Controls that failed open, and were caught

Three worked examples of a control behaving wrongly under real conditions rather than under the
scenario it was designed for. Each is a submission asset, not an embarrassment: it demonstrates the
system was actually run against real content, not only unit-tested against invented fixtures.

| # | What failed open | How it was caught | Fix |
| --- | --- | --- | --- |
| 1 | The PII sweep's `allow-file` pragma was honoured anywhere in a file, so a test file that merely *discussed* the pragma in a string granted itself a file-wide allowance it never intended | `tests/test_profiles.py` acquired an unintended `STREET_ADDRESS` allowance from its own test body, caught by reading the sweep's own report output | `allow-file` is now honoured only in the first 20 lines of a file (its header). A test asserts this test file grants itself nothing |
| 2 | `PHONE_NANP` and `PAYMENT_CARD` used digit-only lookaround boundaries, so a sha256 hex digest — which contains 10- and 16-digit runs flanked by hex letters — matched both rules | 19 false-positive findings on the first real policy audit log, before it could be committed | Boundaries changed from `(?<!\d)` to `(?<![A-Za-z0-9])` on both rules |
| 3 | The price reader had no concept of whether a submission had occurred, and believed any dollar-shaped figure on any page | A live run against MyChoice.ca returned `$177.83` sourced from marketing copy, with zero fields filled — caught by inspecting the run before it was written to `out/results.json` | See "Worked example: the fabricated premium" above |

---

## Not yet enforced

The parts of §2.1/§2.2 that depend on modules never built in this timeframe: the voice executor's
consent state machine and disclosure prelude, the broker harvester's carrier-list and
written-confirmation asks, and injection-resistant reading against untrusted page content beyond
what the sandboxed `echo` site exercises informally. See `docs/LIMITATIONS.md` for the complete,
itemized list of what was deferred and why.

The enforcement-status table in [`PRIME_DIRECTIVES.md`](PRIME_DIRECTIVES.md) tracks each rule's
status as LIVE, PARTIAL or DOCUMENTED ONLY — never marked LIVE before the session state it reads is
actually populated.
