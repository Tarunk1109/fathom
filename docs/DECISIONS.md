# Decisions log

Working mode from 2026-08-10: hackathon pace. Calls are made and noted here rather than escalated.
One line each. Reversible unless marked otherwise.

| # | Decision | Why |
| --- | --- | --- |
| DL-01 | Dependencies land in a local `.venv`; `requirements.txt` lists them with the milestone that introduced them | Playwright and cryptography cannot be stdlib-substituted |
| DL-02 | Vault uses Fernet with a key file outside the repo (`~/.fathom/vault.key`), auto-created 0600 | Simplest thing that genuinely encrypts at rest; no rotation, no ceremony |
| DL-03 | Evidence chain = sha256 content address + prev_hash + JSONL, mirroring the policy audit chain | Operator instruction; the audit chain already proved the pattern |
| DL-04 | Redactor is regex-only, reusing the PII sweep's rule set | Vision redaction has no consumer — screenshots are out of the submission per OQ-004 |
| DL-05 | Sandbox is one local HTTP server with five site paths, not five servers | Fewer moving parts; the executor only needs distinct origins-by-path |
| DL-06 | `sandbox-alpha` reproduces the Sonnet journey shape: multi-step, mid-journey modal, licence-number wall | Day 0 mapped it; building against the real shape is the point |
| DL-07 | Field ontology maps canonical profile keys to page inputs by label/name/id/placeholder, scored | No schema exists across insurers; heuristics with a confidence score beat a brittle map |
| DL-08 | Every executor action goes through `PolicyEngine.evaluate` — no direct Playwright calls | §7.1 load-bearing decision; also the only way P-APPROVAL-01 can bite |
| DL-09 | Modals are polled for before and after every action, not caught as exceptions | Day 0 constraint 1; Sonnet's address modal proved they appear mid-journey |
| DL-10 | Registry seeds from `data/seed/appendix_a.json`; ships with the Day-0-evidenced rows only until Appendix A is supplied | §6.1 — an invented insurer row ends the submission |
| DL-11 | Dedup asserts `same_rate_source_as` only at >= 2 agreeing signals, per §9.3; single-signal matches render as hypotheses | Spec requirement, kept despite hackathon pace |
| DL-12 | Tests: full denial/over-block pairs for gate rules only; one happy-path test elsewhere | Operator instruction, 2026-08-10 |
| DL-13 | Route budget counts `navigate` and `dial`, not `submit` | §9.4 budgets attempts on a route; a six-step form is one attempt, and counting steps exhausted the budget mid-journey |
| DL-14 | A gated control is skipped where the journey can advance without it, and only becomes terminal where it cannot | The §2.1 licence-plate pattern generalised. Otherwise a hypothetical profile stops at the first optional fraud checkbox, and most journeys carry one |
| DL-15 | Fingerprinting gains a fifth signal, `regulatory_amalgamation`, carrying its source URL | A completed amalgamation filed with the regulator is stronger evidence of shared filed rates than a form-set hash. Counts as one signal, never two — the >=2 rule is unchanged |
| DL-16 | Registry seeded from evidenced public sources, not Appendix A | Appendix A is not present in the working conversation. Every row carries source_url and last_verified_at; unverified fields say `unknown`. No entity or relationship is invented (§6.1) |
