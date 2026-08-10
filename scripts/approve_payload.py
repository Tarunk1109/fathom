#!/usr/bin/env python3
"""Review and approve a route's intended payload before any real destination is touched.

    python3 scripts/approve_payload.py --payload out/pending/rt_sonnet.json
    python3 scripts/approve_payload.py --list
    python3 scripts/approve_payload.py --revoke rt_sonnet

Operator constraint following INC-001. The payload is printed field by field with the profile each
value came from, PII-redacted for display, and nothing is approved without an explicit typed
confirmation. One approval per route.

The approval is bound to the payload's digest, not just the route id — so approving a route once
does not approve whatever that route later decides to send.

Payload file format:

    {
      "route_id": "rt_sonnet",
      "target": "https://www.sonnet.ca/...",
      "profile_id": "profile_hypo_clean",
      "fields": {"first_name": {"value": "...", "source_profile_id": "profile_hypo_clean"}, ...}
    }

Exit codes:  0 approved or listed · 1 declined · 2 bad input
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from packages.policy.approvals import ApprovalStore  # noqa: E402
from tools.pii_sweep import redact_text  # noqa: E402

RULE = "─" * 78


def load_payload(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    for key in ("route_id", "target", "profile_id", "fields"):
        if key not in data:
            raise ValueError(f"payload file is missing '{key}'")
    return data


def render(data: dict) -> tuple[dict, set[str]]:
    """Print the payload field by field. Returns the flat payload and the profiles seen."""
    fields = data["fields"]
    profiles: set[str] = set()

    print(f"\n{RULE}\n  PAYLOAD REVIEW — route {data['route_id']}\n{RULE}")
    print(f"\n  target           {data['target']}")
    print(f"  running as       {data['profile_id']}")
    print(f"  fields           {len(fields)}\n")

    width = max((len(name) for name in fields), default=10)
    header = f"  {'field'.ljust(width)}  {'source profile'.ljust(20)}  value (redacted)"
    print(header)
    print("  " + "-" * (len(header) - 2))

    flat: dict[str, object] = {}
    for name, entry in sorted(fields.items()):
        if isinstance(entry, dict):
            value, source = entry.get("value"), entry.get("source_profile_id", "UNTAGGED")
        else:
            value, source = entry, "UNTAGGED"
        profiles.add(source)
        flat[name] = value
        marker = " " if source == data["profile_id"] else "!"
        shown = redact_text(str(value), 40)
        print(f" {marker}{name.ljust(width)}  {str(source).ljust(20)}  {shown}")

    return flat, profiles


def warn(data: dict, profiles: set[str]) -> bool:
    """Print anything that should stop an approval. Returns True if a hard problem was found."""
    problems: list[str] = []
    foreign = profiles - {data["profile_id"]}
    if "UNTAGGED" in profiles:
        problems.append("Some fields carry no source profile. Provenance is required before a "
                        "real destination is touched (P-PROFILE-BLEED-01).")
    if foreign - {"UNTAGGED"}:
        problems.append(f"Fields originate from other profiles: {sorted(foreign - {'UNTAGGED'})}. "
                        f"This is the INC-001 failure. A submission must resolve to one profile.")

    if problems:
        print(f"\n{RULE}\n  PROBLEMS\n{RULE}\n")
        for problem in problems:
            print(f"  ! {problem}")
        return True
    return False


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Approve a route payload before it is sent.")
    parser.add_argument("--payload", help="path to the intended-payload JSON file")
    parser.add_argument("--store", default=None, help="approvals file (default out/approvals.json)")
    parser.add_argument("--list", action="store_true", help="list current approvals")
    parser.add_argument("--revoke", metavar="ROUTE_ID", help="revoke a route's approval")
    parser.add_argument("--by", default="operator", help="who is approving")
    args = parser.parse_args(argv)

    store = ApprovalStore(args.store)

    if args.list:
        if not len(store):
            print("no routes approved")
            return 0
        print(f"{'route':<20} {'profile':<22} {'approved':<22} digest")
        for route_id in sorted(store.approved_route_ids):
            a = store.get(route_id)
            print(f"{a.route_id:<20} {a.profile_id:<22} {a.approved_at:<22} "
                  f"{a.payload_digest[:12]}…")
        return 0

    if args.revoke:
        print("revoked" if store.revoke(args.revoke) else "no such approval")
        return 0

    if not args.payload:
        parser.error("one of --payload, --list or --revoke is required")

    try:
        data = load_payload(Path(args.payload))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    flat, profiles = render(data)
    blocked = warn(data, profiles)

    print(f"\n{RULE}")
    if blocked:
        print("  Fix the problems above and regenerate the payload. Not approving.")
        return 1

    print("  Approving allows the agent to send exactly this payload to this route, once.")
    print("  Any change to the payload invalidates the approval.")
    try:
        answer = input(f"\n  Type the route id ({data['route_id']}) to approve, or anything else "
                       f"to decline: ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\n  declined")
        return 1

    if answer != data["route_id"]:
        print("  declined — nothing approved")
        return 1

    approval = store.approve(
        route_id=data["route_id"], target=data["target"], profile_id=data["profile_id"],
        payload=flat, approved_by=args.by,
    )
    print(f"\n  APPROVED  {approval.route_id}  digest {approval.payload_digest[:12]}…  "
          f"{approval.approved_at}")
    print(f"  recorded in {store.path}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
