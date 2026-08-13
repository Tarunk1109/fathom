# Demo script

One page. Each beat: the claim, the exact command or view that produces it, and what appears on
screen. Nothing here needs hunting during recording — every path and command is copy-pasteable.

**Before recording:** `make sandbox` in one terminal (leave running), `make run` in another to
regenerate every export from a live pipeline run, then open `ui/index.html` in a browser.

---

| # | Beat | Command / view | What appears |
| --- | --- | --- | --- |
| 1 | Premise and scope | `README.md` | Three-sentence description, the personal-use boundary, the honest summary paragraph up front — not buried at the end |
| 2 | Fact-lock: facts sealed at session start, cannot drift between insurers | `tests/test_policy_rules.py` → `TestFactLockRule`, or narrate over `packages/policy/rules.py::_fact_drift` | `P-FACT-01` denies any submitted value diverging from the session's fact-lock — shown live: `.venv/bin/python -c` snippet below reproduces a denial in seconds |
| 3 | Market graph: 70 brands/entities collapse to 67 rate sources; the Aviva amalgamation on two evidenced signals | `ui/index.html` → **Market graph** section (green-highlighted row, `rs_0010`) | Table row: Aviva Insurance, Pilot Insurance, Elite Insurance, Traders General Insurance → one legal underwriter, 2 signals, "merged" |
| 4 | Two normalized outcomes with visible coverage differences; cheaper one is a different product, not a better deal, and both are labelled SANDBOX | `ui/index.html` → **Results** section, `rt_reg_9006`/`rt_reg_9007` | $1,712 PASS at benchmark vs. $1,634 CAUTION with 5 listed variances; both carry a purple `SANDBOX` badge; the comparability note above the table states the cheaper one is not comparable |
| 5 | The gate: bind attempt denied, rule ID and chain index on screen | `make demo` | Section 2: `submit` action with label "Confirm purchase and buy policy" → `VERDICT DENY`, `RULE P-BIND-01`, `CHAIN IDX 1` |
| 6 | Tamper detection: edit an entry, verification fails | `make demo` (same run, section 4) | Entry 1 edited on disk (verdict flipped to ALLOW), re-verification reports `chain BROKEN ... entry_hash does not match` |
| 7 | **The fabricated premium: caught, and the fix demonstrated** | `make demo-fabrication` | Old (quarantined) reader returns `$223.50` from real MyChoice marketing copy with zero fields filled; current reader refuses, printing why; closing note ties it to §6.1 |
| 8 | Real-route outcomes: Cloudflare blocks detected not bypassed, licence walls, every one evidenced | `out/run_report.md` → **Named findings** and **Coverage ledger** | Four named findings up top (no real price, D-AGG, Aviva, fabrication); ledger table lists all 13 attempted routes with registry ID, legal underwriter, status, reason, timestamp, evidence CID |
| 9 | Metrics with denominators, unresolved kept in the denominator | `out/run_report.md` → **Metrics** | `market_completion 3/7 (43%)`, `evidence_rate 7/7 (100%)`, etc., each with the denominator note explaining why 45 never-attempted Appendix A rows are excluded rather than counted as failures |
| 10 | Limitations, stated plainly | `docs/LIMITATIONS.md` | Section 1: per-route reason no real insurer priced the hypothetical profile; sections 2–10 cover aggregators, licence walls, D-OPER, sandbox labelling, Appendix A validation status, the fabrication incident, and the full deferred-module list |

---

## Beat 2, reproducible live in one command

For the fact-lock beat, this prints a real denial in under a second, no setup beyond the repo.
Target is a sandbox URL deliberately, so `P-APPROVAL-01` (default-deny on real destinations) does
not intercept the action before `P-FACT-01` gets a chance to fire — verified working exactly as
shown:

```bash
.venv/bin/python -c "
import sys; sys.path.insert(0,'.')
from packages.policy import PolicyEngine, ProposedAction, SessionContext, fact_hash
engine = PolicyEngine(audit_path='/tmp/demo_factlock.jsonl')
ctx = SessionContext(session_id='s', profile_id='profile_hypo_clean', hypothetical=True,
                     fact_lock={'annual_km': fact_hash('12000')})
decision = engine.evaluate(ProposedAction(
    kind='fill', target='http://localhost:8801/alpha', payload={'annual_km': '5000'},
    route_id='r', session_id='s', profile_id='profile_hypo_clean',
    rationale='Attempt to submit a different mileage than the sealed session fact.'
), ctx)
print(f'{decision.verdict}  {decision.rule_id}  {decision.explanation}')
"
```

Output: `DENY  P-FACT-01  Field 'annual_km' diverges from the session fact-lock. §2.1: material facts
are hashed at session start and may not change across insurers.`

---

## Notes for the walkthrough

- Beats 3–4 and 8–10 all read from files `make run` regenerates — run it fresh before recording so
  timestamps and evidence CIDs are current, not stale from a prior session.
- Beats 5–7 (`make demo`, `make demo-fabrication`) are self-contained and need nothing else
  running; they use their own temporary/fixture state and never touch the real audit log or a real
  insurer.
- If asked live "why no real price," the answer is beat 1's honest summary plus beat 8's ledger:
  two aggregators are Cloudflare-fronted (detected, not bypassed), the direct writers hit either a
  licence wall (Sonnet) or this build's own page-reading capability limit (belairdirect, RBC,
  Desjardins) — itemized in full in `docs/LIMITATIONS.md` §1.
- If asked "what would you build next," the answer is the Rulebook Compiler and the `COMPUTED`
  residual-market premium — `docs/LIMITATIONS.md` §10 names it as the single most significant
  absence in this build.
