#!/usr/bin/env python3
"""The gate, demonstrated — FATHOM §16 step 6.

    make demo                       # or:  python3 scripts/demo_gate.py
    python3 scripts/demo_gate.py --tamper

Built now rather than on submission day, so the walkthrough moment is a command that has been
working since Milestone 2 rather than something assembled under deadline.

What it shows, in order:

1. A legitimate action is ALLOWed, for contrast. A gate that denies everything proves nothing.
2. The agent proposes submitting an application. The Policy Engine DENIES it, naming the rule and
   the audit chain index on screen.
3. `verify_chain()` recomputes the whole chain and reports it intact.

With `--tamper`, an entry is edited on disk afterwards and the chain is re-verified, so the
verification is visibly capable of failing. A check that has never been seen to fail is not
evidence of anything.

Runs against a scratch audit log by default. It never touches the real one, and it never touches a
real destination — every target here is the local synthetic sandbox.
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from packages.policy import (  # noqa: E402
    AuditLog,
    PolicyEngine,
    ProposedAction,
    SessionContext,
    fact_hash,
)

RULE = "─" * 78


def heading(text: str) -> None:
    print(f"\n{RULE}\n  {text}\n{RULE}")


def show(decision, action) -> None:
    marker = {"ALLOW": "ALLOW   ", "DENY": "DENY    ", "ESCALATE": "ESCALATE"}[decision.verdict]
    print(f"\n  proposed   {action.kind}: {action.target}")
    print(f"  rationale  {action.rationale}")
    print(f"\n  VERDICT    {marker}")
    print(f"  RULE       {decision.rule_id}")
    print(f"  CHAIN IDX  {decision.audit_index}")
    print(f"  WHY        {decision.explanation}")


def build_session() -> SessionContext:
    """The operator's session. Facts locked at session start (§9.2)."""
    return SessionContext(
        session_id="ses_demo_0001",
        profile_id="operator",
        sandbox_only=False,
        fact_lock={
            "licence_class": fact_hash("G1"),
            "vehicle_status": fact_hash("none_prospective_purchase"),
            "canadian_history_months": fact_hash("0"),
            "prior_insurance": fact_hash("false"),
        },
        registered_licence_hash=fact_hash("OPERATOR-REGISTERED-VALUE-NOT-STORED-HERE"),
        operator_identity={},
        registered_services=frozenset(),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Demonstrate the FATHOM Policy Engine gate.")
    parser.add_argument("--tamper", action="store_true",
                        help="edit the audit log on disk afterwards and re-verify, to show the "
                             "chain check failing")
    parser.add_argument("--audit-path", default=None,
                        help="audit log to write (default: a temporary file)")
    args = parser.parse_args(argv)

    temp_dir: tempfile.TemporaryDirectory | None = None
    if args.audit_path:
        audit_path = Path(args.audit_path)
    else:
        temp_dir = tempfile.TemporaryDirectory(prefix="fathom_demo_")
        audit_path = Path(temp_dir.name) / "policy_audit.jsonl"

    engine = PolicyEngine(audit_path=audit_path)
    ctx = build_session()

    heading("FATHOM — Policy Engine  (deterministic gate, no LLM in the decision path)")
    print(f"\n  session    {ctx.session_id}")
    print(f"  profile    {ctx.profile_id}")
    print(f"  rules      {len(engine.rules)} registered "
          f"({len([r for r in engine.rules if r.verdict == 'DENY'])} deny, "
          f"{len([r for r in engine.rules if r.verdict == 'ESCALATE'])} escalate)")
    print(f"  audit log  {audit_path}")

    # 1 — a legitimate action, so the gate is visibly not a blanket refusal ------------------
    heading("1  A legitimate action proceeds")
    permitted = ProposedAction(
        kind="navigate",
        target="http://localhost:8801/quote/start",
        payload=None,
        route_id="rt_sandbox_alpha",
        session_id=ctx.session_id,
        profile_id=ctx.profile_id,
        rationale="Open the quote journey to begin the benchmark coverage request.",
    )
    show(engine.evaluate(permitted, ctx), permitted)

    # 2 — the walkthrough moment ------------------------------------------------------------
    heading("2  The agent proposes submitting an application")
    blocked = ProposedAction(
        kind="submit",
        target="http://localhost:8801/quote/checkout",
        payload={
            "label": "Confirm purchase and buy policy",
            "selector": "#bind-policy",
            "effective_date": "2026-09-01",
        },
        route_id="rt_sandbox_alpha",
        session_id=ctx.session_id,
        profile_id=ctx.profile_id,
        rationale="A price was returned; submitting the application would complete the journey.",
    )
    decision = engine.evaluate(blocked, ctx)
    show(decision, blocked)

    if decision.verdict != "DENY":
        print("\n  UNEXPECTED: the gate did not deny a bind-intent action.")
        return 1

    # 3 — verify the chain ------------------------------------------------------------------
    heading("3  Verify the audit chain")
    result = engine.verify_chain()
    print(f"\n  entries    {len(engine.audit)}")
    print(f"  result     {result.describe()}")

    exit_code = 0 if result.ok else 1

    if args.tamper:
        heading("4  Tamper with the log on disk, then verify again")
        lines = audit_path.read_text(encoding="utf-8").splitlines()
        record = json.loads(lines[1])
        print(f"\n  editing entry {record['index']}: verdict "
              f"{record['verdict']} -> ALLOW, rule {record['rule_id']} -> P-ALLOW-00")
        record["verdict"] = "ALLOW"
        record["rule_id"] = "P-ALLOW-00"
        lines[1] = json.dumps(record, ensure_ascii=False, sort_keys=True)
        audit_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

        reverified = AuditLog(audit_path).verify_chain()
        print(f"\n  result     {reverified.describe()}")
        if reverified.ok:
            print("\n  UNEXPECTED: verification passed on a tampered log.")
            exit_code = 1
        else:
            print("\n  The edit is detected. An entry cannot be changed after it is written.")

    print()
    if temp_dir is not None:
        temp_dir.cleanup()
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
