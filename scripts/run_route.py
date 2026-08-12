#!/usr/bin/env python3
"""Run one route end-to-end through the gate.

    .venv/bin/python scripts/run_route.py --route rt_sandbox_alpha \
        --url http://localhost:8801/alpha --profile profile_hypo_clean

Real destinations additionally require an approval recorded by scripts/approve_payload.py
(P-APPROVAL-01, default deny).
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from packages.evidence import EvidenceStore                      # noqa: E402
from packages.executors.web import WebExecutor                   # noqa: E402
from packages.policy import (ApprovalStore, PolicyEngine, RouteBudget,  # noqa: E402
                             SessionContext)
from packages.profiles import ProfileRegistry                    # noqa: E402


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--route", required=True)
    ap.add_argument("--url", required=True)
    ap.add_argument("--profile", default="profile_hypo_clean")
    ap.add_argument("--headed", action="store_true", help="show the browser")
    ap.add_argument("--out", default=None, help="write the RunResult as JSON here")
    ap.add_argument("--seconds", type=int, default=150,
                    help="wall-clock budget for this route (P-BUDGET-01 enforces it)")
    args = ap.parse_args(argv)

    registry = ProfileRegistry()
    profile = registry.get(args.profile)
    approvals = ApprovalStore()

    engine = PolicyEngine()
    ctx = SessionContext(
        session_id=f"ses_{args.route}",
        profile_id=profile.profile_id,
        hypothetical=profile.hypothetical,
        sandbox_only=profile.sandbox_only,
        fact_lock=profile.fact_lock(),
        approved_routes=approvals.approved_route_ids,
        # A real journey can stall on a JS page forever. §9.4's time budget is the existing
        # answer; it just was not being populated.
        budgets={args.route: RouteBudget(
            max_attempts=2,
            deadline=datetime.now(timezone.utc) + timedelta(seconds=args.seconds))},
    )

    executor = WebExecutor(engine, EvidenceStore(), slow_mo_ms=120 if args.headed else 0)
    result = executor.run(route_id=args.route, entry_url=args.url, profile=profile, ctx=ctx,
                          headless=not args.headed)

    print("\n" + result.summary())
    print(f"  steps            {len(result.steps)}")
    print(f"  fields filled    {sum(len(s.fields_filled) for s in result.steps)}")
    print(f"  modals handled   {len(result.modals)}")
    for modal in result.modals:
        print(f"     step {modal.step}: {modal.text[:70]!r} dismissed={modal.dismissed}")
    print(f"  policy denials   {len(result.policy_denials)}")
    for rule_id, _ in result.policy_denials[:6]:
        print(f"     {rule_id}")
    print(f"  evidence         {len(result.evidence_cids)} artifacts")
    if result.stopping_step:
        print(f"  stopping step    {result.stopping_step}")
    if result.premium:
        print(f"  premium          ${result.premium:,.2f}  ref {result.quote_reference}")
        print(f"  coverage         {result.coverage}")

    if args.out:
        from dataclasses import asdict
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(asdict(result), indent=2), encoding="utf-8")
        print(f"  written          {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
