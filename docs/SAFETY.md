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

### Personal use only

§2.1: *never sell, license, publish for public use, or deploy this as a service.*

- [`LICENSE`](../LICENSE) is not an open source licence. It grants no right of use to anyone but
  the operator, and grants judges read access for evaluation only.
- Licence clauses 4(e)–(i) restate the system's hard constraints — no binding, no payment or
  signature submission, no CAPTCHA or auth bypass, no fabricated licence number, and no disabling
  of the Policy Engine, redaction layer, disclosure prelude, consent state machine or evidence
  chain — so the licence and the running code say the same thing.
- `README.md` states the scope and the boundary in the first screen.

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
