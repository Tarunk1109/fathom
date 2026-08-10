#!/usr/bin/env python3
"""Verify the Policy Engine audit chain — FATHOM §9.1, §9.5.

    make verify
    python3 scripts/verify_chain.py
    python3 scripts/verify_chain.py --path out/audit/policy_audit.jsonl --show 20
    python3 scripts/verify_chain.py --json

A judge should be able to verify the chain live without reading any code, which is why this is a
command rather than a method. It recomputes every entry hash from the entry's own contents and
walks the `prev_hash` links, reporting the first index that diverges.

Exit codes:  0 chain intact · 1 chain broken · 2 no log found
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from packages.policy.audit import DEFAULT_AUDIT_PATH, AuditLog  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify the FATHOM policy audit chain.")
    parser.add_argument("--path", default=str(DEFAULT_AUDIT_PATH), help="audit log path")
    parser.add_argument("--show", type=int, default=0, metavar="N",
                        help="also print the last N decisions")
    parser.add_argument("--json", action="store_true", help="machine-readable result")
    args = parser.parse_args(argv)

    path = Path(args.path)
    if not path.exists():
        message = f"no audit log at {path}"
        print(json.dumps({"ok": False, "error": message}) if args.json else f"error: {message}",
              file=sys.stderr)
        return 2

    log = AuditLog(path)
    result = log.verify_chain()

    if args.json:
        print(json.dumps({
            "ok": result.ok,
            "path": str(path),
            "entries_checked": result.entries_checked,
            "first_bad_index": result.first_bad_index,
            "reason": result.reason,
        }, indent=2))
        return 0 if result.ok else 1

    print(f"FATHOM policy audit chain — {path}")
    print(f"  entries    {len(log)}")
    print(f"  head       {log.head_hash[:16]}…")
    print(f"  result     {result.describe()}")

    if args.show:
        print(f"\n  last {min(args.show, len(log))} decisions:\n")
        header = f"  {'idx':>5}  {'verdict':<8}  {'rule':<14}  {'kind':<8}  target"
        print(header)
        print("  " + "-" * (len(header) - 2))
        for entry in log.entries[-args.show:]:
            print(f"  {entry.index:>5}  {entry.verdict:<8}  {entry.rule_id:<14}  "
                  f"{entry.action_kind:<8}  {entry.target_safe}")

    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
