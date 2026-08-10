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
first wall on every route. No automation touched a real insurer. Per OQ-004, **no screenshots were
taken**: the local vision redactor does not exist until Milestone 3, §2.1 makes an unredacted
screenshot a hard failure, and verbatim redacted quotes satisfy the evidence requirement on their
own.

---

## Not yet enforced

Everything else in §2.1 and §2.2 depends on the Policy Engine (Milestone 2) and the spine
(Milestone 3). Until those exist, the honest statement is that **no automated action of any kind
has been taken against any real destination.** The enforcement-status table in
[`PRIME_DIRECTIVES.md`](PRIME_DIRECTIVES.md) tracks each mechanism as it lands.

---

## Sections to write at their milestones

| Section | Milestone |
| --- | --- |
| The Policy Engine: rules, decision record, audit chain, and a demonstrated denial | 2 |
| Fact-lock and licence binding | 2–3 |
| Sandbox-profile isolation: how a simulated profile is prevented from reaching a real destination | 3 |
| The redaction pipeline: local text and vision, redact-before-write | 3 |
| Bounded attempts: per-channel budgets and the no-retry-on-rejection rule | 4 |
| Injection resistance: sandboxed reader, typed extraction, incident log | 7 |
| Voice: disclosure prelude, consent state machine, recording gate, live escalation | 8 |
| Final PII sweep across repo, `out/`, screenshots and the recorded walkthrough | 9 |
