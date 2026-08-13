# Architecture

Per FATHOM §0.5, **every module gets an entry here and a test in `tests/`.** This is a final pass
per `finish.md`: it describes what was actually built, not what `fathom.md` specifies. Where the
two diverge, this file says so explicitly rather than describing the unbuilt version as though it
existed.

The load-bearing decision is §7.1: **everything routes through the Policy Engine.** No executor
calls a browser, phone or API directly. Every proposed action is a structured object submitted to
the gate, which returns `ALLOW`, `DENY` or `ESCALATE` plus the rule that fired, and appends the
decision to a hash-chained audit log.

---

## The pipeline as it actually runs

```
sandbox/server.py (7 synthetic sites)  ──┐
                                          │
data/profiles/*.json ──► ProfileRegistry │
data/seed/*.json      ──► MarketRegistry ├──► scripts/run_all.py
~/.fathom/vault.enc   ──► Vault          │        │
out/approvals.json    ──► ApprovalStore  │        ▼
                                          │   for each approved/synthetic route:
                                          │     SessionContext (profile flags, fact-lock,
                                          │       approved_routes)
                                          │       │
                                          │       ▼
                                          │   WebExecutor.run()
                                          │     every proposed action ──► PolicyEngine.evaluate()
                                          │       ALLOW  → Playwright acts, evidence appended
                                          │       DENY   → route ends, terminal_status recorded
                                          │       ESCALATE → checkpoint queued, route stays open
                                          │       │
                                          │       ▼
                                          │   RunResult ──► normalize() ──► NormalizedResult
                                          └────────────────────┬──────────────────────────────
                                                                ▼
                                    MarketRegistry.resolve_rate_sources()  (§9.3 dedup)
                                                                │
                          ┌─────────────────────────────────────┼─────────────────────────────┐
                          ▼                                     ▼                             ▼
                 out/registry.json/csv              out/results.json / runs.json      ui/index.html
                                                                │
                                                       out/run_report.md
```

One command runs the whole right-hand side: `make run` (`scripts/run_all.py`). Real destinations
are attempted only for routes in `out/approvals.json`, and only when `--include-real` is passed —
otherwise only the local sandbox runs.

---

## The Policy Engine — the load-bearing decision

**`packages/policy/`. Tests: `test_policy_rules.py`, `test_policy_engine.py`,
`test_audit_chain.py`, `test_audit_concurrency.py` — 156 cases total across the whole test suite.**

Deterministic. No LLM in the decision path. Rules are pure functions of the proposed action and
the session context, evaluated in a fixed, documented order, first match wins.

### The rule list

| Rule | Verdict | Denies |
| --- | --- | --- |
| `P-STOP-01` | DENY | Any action after a stop request |
| `P-SANDBOX-01` | DENY | A `sandbox_only` profile touching a real destination |
| `P-APPROVAL-01` | DENY | A real-destination action on a route with no recorded payload approval (default deny) |
| `P-PROFILE-BLEED-01` | DENY | A payload whose fields resolve to more than one profile |
| `P-HYPO-ATTEST-01` | DENY | An accuracy/fraud-acknowledgement control under a hypothetical profile |
| `P-HYPO-LICENCE-01` | DENY | A driver's licence number under a hypothetical profile |
| `P-HYPO-HUMAN-01` | DENY | Voice/callback/human-contact under a hypothetical profile |
| `P-HYPO-STEP-01` | DENY | Identity/consent/declaration/callback/purchase steps under a hypothetical profile |
| `P-THIRDPARTY-01` | DENY | Third-party personal data |
| `P-LICENCE-01` | DENY | A licence value not matching the vault's registered value |
| `P-REAL-FACT-01` | DENY | A fabricated material fact under a non-hypothetical profile |
| `P-FACT-01` | DENY | Any value diverging from the session fact-lock (every profile) |
| `P-PLATE-01` | DENY | A licence plate value (skip if optional; `blocked` if mandatory) |
| `P-PAY-01` | DENY | Payment/banking fields |
| `P-SIGN-01` | DENY | Signature/declaration/attestation controls |
| `P-BIND-01` | DENY | Bind/purchase/buy/confirm-order controls |
| `P-CAPTCHA-01` | DENY | Interaction with a CAPTCHA or bot check |
| `P-AUTH-01` | DENY | Credentials to an unregistered service |
| `P-RECORD-01` | DENY | Recording without `GRANTED` consent |
| `P-DISCLOSE-01` | DENY | Speaking on a call before the disclosure prelude |
| `P-BUDGET-01` | DENY | Actions past the route's attempt or time budget |
| `P-HUMAN-01` | ESCALATE | Identity lookup, consent attestation, coverage advice — routes to the human checkpoint queue, route stays open |

19 DENY rules, 1 ESCALATE rule. Every rule has both a test proving it denies what it must and a
test proving it permits the nearest legitimate neighbour (`ALLOW` asserted outright, so a
neighbour caught by any *other* rule also fails).

### Enforcement status

| Status | Meaning |
| --- | --- |
| **LIVE** | The rule exists, is registered, is tested, and reads session state that is genuinely populated in this build's normal operation |
| **PARTIAL** | The rule exists, is registered, and is tested, but reads session state that a module never built in this timeframe would normally populate (so the rule is correct but the input feeding it is thinner than the full spec) |
| **DOCUMENTED ONLY** | Written in `fathom.md`, nothing enforces it |

| Directive area | Mechanism | Status |
| --- | --- | --- |
| No PII in repo/logs/exports | `tools/pii_sweep.py`, CI + pre-commit | **LIVE** |
| No PII in the audit or evidence chain | Field names + digest only, redactor on every write | **LIVE** |
| Bind/sign/pay/CAPTCHA/auth denial | `P-BIND-01`, `P-SIGN-01`, `P-PAY-01`, `P-CAPTCHA-01`, `P-AUTH-01` | **LIVE** |
| Stop request honoured | `P-STOP-01` | **LIVE** |
| Attempt/time budgets | `P-BUDGET-01`, drawn down by the gate itself | **LIVE** |
| Sandbox isolation | `P-SANDBOX-01` | **LIVE** |
| No real destination without approval | `P-APPROVAL-01`, `scripts/approve_payload.py` | **LIVE** |
| Hypothetical-profile conduct (no licence, no human contact, no commitment steps, no attestation) | `P-HYPO-*` family | **LIVE** |
| One submission, one profile | `P-PROFILE-BLEED-01`, `FieldValue` provenance | **LIVE** |
| Fact-lock across insurers | `P-FACT-01`, `P-REAL-FACT-01` | **LIVE** — populated by `Profile.fact_lock()` |
| Third-party data refusal | `P-THIRDPARTY-01` | **PARTIAL** — explicit third-party field names denied; full identity comparison needs vault-populated `operator_identity` |
| Every decision hash-chained | `AuditLog.verify_chain()` | **LIVE**, concurrency-safe (file-locked; see § Data storage below) |
| Recording consent / disclosure prelude | `P-RECORD-01`, `P-DISCLOSE-01` | **DOCUMENTED ONLY** — the rules exist and are tested against a stub `CallState`; no voice executor exists to drive them in real operation |
| Broker carrier-list / written-confirmation asks | — | **DOCUMENTED ONLY** — no broker executor was built |
| Redaction before every write | `packages/redactor/` (regex only) | **LIVE**, scoped — see § Data storage |
| Injection-resistant reading | Sandboxed `echo` site carries a payload | **PARTIAL** — the sandbox site exists; no dedicated sandboxed-reader module or incident-log demo was built |

---

## Human checkpoints and the approval flow

Two distinct human-in-the-loop mechanisms, serving different purposes:

**`P-HUMAN-01` → the checkpoint queue.** Fires on identity verification, consent attestation or
coverage-advice language in an action's rationale. Verdict is `ESCALATE`, not `DENY` — the route
**stays open**, and the request is appended to `PolicyEngine.checkpoint_queue` for the operator to
resolve. Nothing in this build currently drains that queue automatically (no voice/broker executor
exists to hand a live call to); it is demonstrated as a gate behaviour in `tests/test_policy_engine.py`.

**`P-APPROVAL-01` → the payload approval flow.** Independent of the checkpoint queue, and the
control that answers the operator's explicit post-INC-001 requirement: *no route runs unattended.*

1. `scripts/prepare_payload.py` builds an intended-payload file straight from `Profile.tagged()`,
   so every field carries its `source_profile_id` — nothing is hand-assembled.
2. `scripts/approve_payload.py` prints the payload field by field (PII-redacted for display),
   flags any field with missing or mismatched provenance, and requires the operator to type the
   route id back as confirmation.
3. The approval is recorded in `out/approvals.json`, bound to the payload's content digest — a
   changed payload invalidates the approval; approving a route once does not approve whatever it
   later decides to send.
4. `P-APPROVAL-01` denies any real-destination action on a route absent from that file. **Default
   deny.**

Six real routes were approved this way for this build: belairdirect, RBC Insurance, Desjardins,
Rates.ca, LowestRates.ca, MyChoice.

---

## Consent handling

**Data structures exist and are enforced at the gate; no live voice call ever exercised them.**

`CallState` (`packages/policy/actions.py`) tracks `disclosure_delivered: bool` and
`recording_consent: RecordingConsent` (`NO_AUDIO` / `GRANTED` / `REFUSED`, default `NO_AUDIO`).
`P-DISCLOSE-01` denies any `speak` action before disclosure, except the disclosure prelude itself.
`P-RECORD-01` denies any `record` action unless consent is `GRANTED`. Both rules are tested against
constructed `CallState` values, not against a real or simulated phone call — no voice executor was
built (§14, deferred). This is a real gap, not a documentation gap: the *rule* is live, the
*channel* it would gate does not exist. Recorded in `docs/LIMITATIONS.md`.

---

## Data storage, redaction, deletion

| Store | Path | Mechanism | Notes |
| --- | --- | --- | --- |
| Vault | `~/.fathom/vault.enc` + `~/.fathom/vault.key` (0600) | Fernet symmetric encryption, key held outside the repo | `inject()` returns `FieldValue`-wrapped values only; no raw string ever enters a payload from the vault |
| Policy audit log | `out/audit/policy_audit.jsonl` | sha256 content chain + prev-hash, append-only JSONL | No payload values, ever — field names + digest, targets stripped of query strings, rationale redacted. File-locked against concurrent writers (see below) |
| Evidence chain | `out/evidence/chain.jsonl` + `out/evidence/blobs/` | Content-addressed by sha256 of **redacted** bytes | `append()` runs the redactor itself — there is no raw-then-clean path. Same file-locking fix as the audit log |
| Registry | `data/seed/*.json` (source) → `out/registry.json`/`.csv` (export) | Plain JSON/CSV, no encryption (no PII by construction) | Appendix A rows carry `requires_current_validation: true`, `last_verified_at: null` |
| Profiles | `data/profiles/*.json` | Plain JSON | `profile_hypo_clean` is fully synthetic and file-scoped PII-sweep-allowed; `profile_operator` holds only `vault_refs`, never a real value |

**Redaction.** `packages/redactor/` is regex-only, reusing the PII sweep's own rule set so
detection and redaction cannot drift apart (`DL-04`). No local vision model was built —
screenshots are excluded from the submission per `OQ-004`, so vision redaction has no consumer.

**Deletion.** Not implemented. Nothing in this build issues a delete against the vault, the audit
log, or the evidence chain (all three are designed append-only by construction — a policy audit
trail and an evidence chain are supposed to resist deletion). Vault key rotation and vault entry
deletion were both out of scope under the operator's "simplest thing that encrypts at rest, no
rotation, no ceremony" instruction (`DL-02`).

**Concurrency.** Found during this final pass, not anticipated: `AuditLog.append()` and
`EvidenceStore.append()` both computed their next entry's index from an in-memory count taken once
at construction. Two background route runs launched close together both read the same count and
both appended an entry claiming the same index — `make verify` caught it directly (`chain BROKEN
... index is 118, expected 119`). Fixed with an exclusive OS file lock (`fcntl.flock`) held across
the entire read-current-state-then-write sequence in both classes, verified against a real 6-process
concurrent stress test (`tests/test_audit_concurrency.py`). Full account: `docs/SAFETY.md`.

---

## MCP servers

**None exist.** `fathom.md` §7.2 specifies seven (`fathom-registry`, `fathom-evidence`,
`fathom-policy`, `fathom-vault`, `fathom-rater`, `fathom-routes`, `fathom-profiles`). All packages
are called as plain Python modules; no MCP server process, FastMCP or otherwise, was stood up.
Judge-facing verification instead goes through direct CLI entry points: `make verify`, `make demo`,
`make demo-fabrication`, `make rules`.

---

## Built

### `tools/pii_sweep.py` — PII sweep

Milestone 1. Tests: `tests/test_pii_sweep.py` (30 cases). Scans every text file under the repo root
— `out/` and `docs/` included — for eight PII pattern classes, exits non-zero on a hit. Stdlib
only. Runs identically in CI and locally (`make sweep`). Findings are reported as file/line/rule
and a masked excerpt, never the matched value. Binary files are listed for manual review, never
silently skipped. Three real false-positive classes were found and fixed against real content
during this build — see `docs/SAFETY.md` § "Controls that failed open, and were caught".

### `packages/policy/` — Policy Engine

Milestone 2. Described in full above.

### `packages/vault/` — encrypted operator store

Milestone 3. Fernet encryption, `inject()` returns provenanced `FieldValue`s, `value_hashes()`
lets the profile registry detect a real value pasted into a synthetic profile (the INC-001 check)
without ever handling plaintext.

### `packages/evidence/` — content-addressed evidence chain

Milestone 3. sha256 of redacted bytes, prev-hash chained, append-only. Concurrency-safe as of this
final pass.

### `packages/redactor/` — regex redaction

Milestone 3. Reuses the PII sweep's rule set. No vision component (scope decision, `DL-04`).

### `packages/profiles/` — profile registry

Milestone 3. `Profile`, `ProfileRegistry`, `validate()`. Records, not code paths. `validate()`
makes the INC-001 failure state (a hypothetical profile carrying a real value) structurally
unrepresentable — it raises rather than loading degraded. Three shipped profiles:
`profile_hypo_clean` (primary, fully synthetic, 39+ facts), `profile_operator` (vault-refs only,
no real value in the repo), `profile_sim_g2` (sandbox-only simulation).

### `sandbox/server.py` — synthetic insurer sites

Milestone 4/7 (built ahead of schedule, since the executor needed something real to run against
before touching a live insurer). Seven sites on one server: `alpha` reproduces the exact Sonnet
journey shape Day 0 mapped (multi-step, mid-journey address-validation modal, fraud-acknowledgement
checkbox, mandatory licence-number wall); `bravo` a CAPTCHA; `charlie` a callback-only dead end;
`delta` intermittent failure with drifting field ids; `echo` a prompt-injection payload in page
text (present as a fixture; no dedicated injection-defense module reads it yet — see the
enforcement table above); `foxtrot`/`golf` price with deliberately different coverage.

### `packages/executors/web/` — the web executor

Milestone 4, the priority-1 deliverable per the operator's hackathon-pace instruction. Maps page
fields to a canonical ontology by scored label/name/id/placeholder signals
(`packages/executors/web/ontology.py`), fills from the active profile, walks a journey to a
terminal status. **Every action passes `PolicyEngine.evaluate()` before Playwright touches the
page** — there is no direct browser call that bypasses the gate. Modals are polled before every
action and logged with their text, not caught as exceptions. A per-route wall-clock deadline
(`RouteBudget.deadline`) stops a stalled real-page run. No route recipes, no self-healing, no twin
readers — a single extraction path, not a dual one.

### `packages/normalizer/` — normalizer, assessment, parity

Milestone 4/5. Maps a `RunResult` into the §8.4 common schema. `PASS`/`CAUTION`/`FAIL` per §8.4's
rules. Parity is `measured` only when coverage exactly matches the benchmark; otherwise
`not_possible` — no Benefit Price Probe exists to measure per-item deltas, and §18 forbids
inventing one. `sandbox: bool` is an explicit field on every result, not a naming convention.

### `packages/registry/` — market registry and dedup

Milestone 5/6. §8.3 record shape. §9.3 fingerprinting on five signals (four specified +
`regulatory_amalgamation`, a documented extension, `DL-15`): `same_rate_source_as` asserted only
at two or more agreeing signals; a single-signal match renders as a hypothesis, never merged.
`metrics()` computes the five §11.9 figures with visible denominators — market completion and
comparable quote yield at rate-source granularity, the rest at record granularity, matching the
spec's own mixed wording.

### `scripts/run_all.py` — orchestration and the UI

Execute → normalize → dedup → export → build UI, one command. `ui/index.html` — three views
(results, market graph, policy gate) in one static file, no JavaScript. Verified live in Chrome:
zero console errors, PII-free rendering, correct behaviour at 67-row scale.

### `scripts/demo_gate.py`, `scripts/demo_fabrication.py`, `scripts/verify_chain.py`

Judge-facing demonstrations, built to work standalone with no arguments. See `docs/DEMO_SCRIPT.md`.

---

## Not built

Present in `fathom.md`, absent from this repository, listed here so nothing is described as though
it existed: `packages/intake/` (adaptive questioning, Field Passport), `packages/planner/` (route
priority/scheduling beyond the fixed order in `run_all.py`), `packages/rater/` (Rulebook Compiler,
the `COMPUTED` residual-market premium — the most significant absence, see `LIMITATIONS.md`),
`packages/analysis/` (Eligibility Frontier, vehicle inversion, channel arbitrage, dark-pattern
detector), `packages/executors/voice/` and `packages/executors/broker/`, twin readers, self-healing
recipes, the seven MCP servers, Ask-Your-Own-Findings.
