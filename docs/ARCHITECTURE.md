# Architecture

Per FATHOM §0.5, **every module gets an entry here and a test in `tests/`.** An entry appears when
the module is built, not when it is planned — the "Planned" table below is a map, not a claim.

The load-bearing decision is §7.1: **everything routes through the Policy Engine.** No executor
calls a browser, phone or API directly. Every proposed action is a structured object submitted to
the gate, which returns `ALLOW`, `DENY` or `ESCALATE` plus the rule that fired, and appends the
decision to the hash-chained audit log.

---

## Built

### `tools/pii_sweep.py` — PII sweep

**Milestone 1. Tests: `tests/test_pii_sweep.py` (30 cases).**

Enforces §2.1: no real licence number, full address, payment data or raw call audio in the repo,
logs, prompts, traces, screenshots or the submission. Scans every text file under the repository
root — `out/` and `docs/` included — and exits non-zero on a hit.

| Aspect | Decision | Why |
| --- | --- | --- |
| Dependencies | stdlib only | The safety check must run before any dependency exists. §13 stack decisions belong to the milestone that uses them. |
| Local and CI parity | One implementation, invoked identically | `make sweep` and the CI job run the same file. Two implementations drift, and the one that drifts is the one that matters. |
| Output | File, line, rule, masked excerpt | Printing the match would write PII into CI logs — the exact failure the sweep exists to prevent. |
| Binary files | Listed for manual review, never silently skipped | A screenshot cannot be grepped. §15.1 requires the final sweep to cover screenshots and recordings; the tool must not imply coverage it lacks. |
| False positives | Inline `pii-sweep: allow` pragma, optionally scoped to a rule list | Narrowing one line beats weakening a rule for the whole repo. |

**Rules.** `DL_ONTARIO`, `PC_FULL_POSTAL`, `VIN`, `PHONE_NANP`, `EMAIL`, `PAYMENT_CARD`,
`STREET_ADDRESS`, `DOB_LABELLED`.

Three rules deliberately permit the redacted form the project actually records: an FSA such as
`M5V` does not trip `PC_FULL_POSTAL`, a bare birth year does not trip `DOB_LABELLED`, and a licence
*class* such as `G1` does not trip `DL_ONTARIO`. A checker that forbids the redacted form would
push work outside the checker, which is worse than not having one.

Three rules carry validators to survive contact with a real repository: `PAYMENT_CARD` requires a
Luhn-valid check digit, `VIN` requires a genuine letter/digit mix so content-addressed hashes do
not trip it, and `PHONE_NANP` rejects invalid NANP area and exchange codes and low-entropy digit
runs so ISO timestamps and placeholders do not.

**Known limits.** Regex cannot detect an address written in prose, a licence number split across
lines, or anything inside an image. It is a floor, not a ceiling. The local redactor
(`packages/redactor/`, Milestone 3) is the real defence; this is the check that catches what got
past it.

**Entry points.** `make sweep` · `make check` · `python3 tools/pii_sweep.py [root] [--json]
[--list-rules]` · `.githooks/pre-commit` (install with `make hooks`) · `.github/workflows/ci.yml`.

---

## Planned

Not yet built. Listed so the map is legible; each becomes a full entry at its milestone.

| Module | Path | Milestone | Role |
| --- | --- | --- | --- |
| Policy Engine | `packages/policy/` | 2 | Deterministic gate, no LLM in the decision path. 13 rules, hash-chained audit log, `verify_chain()`. |
| Profile registry | `packages/profiles/` | 3 | Profiles as records, not code paths. Module gating. `sandbox_only` enforcement. |
| Vault + fact-lock | `packages/vault/` | 3 | Encrypted at rest, injected by destination, never returned raw. Session fact hash. |
| Adaptive intake | `packages/intake/` | 3 | Uncertainty-ordered questioning, Field Passport, consent receipts. |
| Evidence chain | `packages/evidence/` | 3 | Content-addressed by sha256 of *redacted* bytes, append-only, verifiable. |
| Redactor | `packages/redactor/` | 3 | Local text NER + local vision masking. Redact before write; no raw-then-clean path. |
| Market registry + graph | `packages/registry/` | 3–6 | Underwriter/group/brand/distributor/rate source. Evidenced edges. Fingerprinting. |
| Route planner | `packages/planner/` | 4 | Channel selection, priority, bounded attempts. |
| Web executor | `packages/executors/web/` | 4 | Playwright + vision fallback, recipes, self-healing. |
| Normalizer + parity | `packages/normalizer/` | 4–5 | Common schema, PASS/CAUTION/FAIL assessment, parity solver. |
| Rulebook Compiler + rater | `packages/rater/` | 5 | Public rate manual → deterministic arithmetic rater. No model call at runtime. |
| Analysis | `packages/analysis/` | 6–9 | Eligibility Frontier, vehicle inversion, channel arbitrage, dark patterns. |
| Broker executor | `packages/executors/broker/` | 6 | Carrier-list and written-confirmation asks, by email then voice. |
| Synthetic sandbox | `sandbox/` | 7 | Five fake insurer sites. Reliability numbers come from here, not from live sites. |
| Voice executor | `packages/executors/voice/` | 8 | Disclosure prelude, consent state machine, live escalation, context handoff. |
| MCP servers | `packages/mcp/` | 3–9 | Seven servers per §7.2. |
| UI | `ui/` | 9 | Seven views. |
