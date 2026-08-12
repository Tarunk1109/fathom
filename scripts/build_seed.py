#!/usr/bin/env python3
"""Merge the Appendix A discovery seed with FATHOM's own evidenced rows.

    .venv/bin/python scripts/build_seed.py

Precedence (DL-17): where a legal entity appears in both, **the evidenced row wins**. Appendix A
is a discovery seed, not verified fact — its own header says so. What the appendix contributes to
an evidenced row is the group name and its starting-route note; what it never overwrites is a
source_url, a quote_url or an observed status.

Appendix-only rows load as `status: unresolved`, `last_verified_at: null`,
`requires_current_validation: true`, with the starting-route text stored as UNVERIFIED GUIDANCE.
"""
from __future__ import annotations

import json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "data" / "seed" / "appendix_a_source.json"
EVIDENCED = ROOT / "data" / "seed" / "evidenced_rows.json"
OUT = ROOT / "data" / "seed" / "appendix_a.json"


def key(name: str) -> str:
    """Normalise a legal entity name for matching across the two sources."""
    name = name.lower().strip()
    name = re.sub(r"^the\s+", "", name)
    name = re.sub(r"\s*\(.*?\)\s*", " ", name)
    name = re.sub(r"[^a-z0-9 ]+", " ", name)
    name = re.sub(r"\b(company|companies|inc|ltd|limited|corporation|corp|of|canada)\b", " ", name)
    return re.sub(r"\s+", " ", name).strip()


def main() -> int:
    src = json.loads(SRC.read_text(encoding="utf-8"))
    evidenced = json.loads(EVIDENCED.read_text(encoding="utf-8"))["records"]
    # Several consumer brands can share one legal entity — Aviva, Pilot, Elite and Traders
    # General are all Aviva Insurance Company of Canada since the 2026-01-01 amalgamation. Mapping
    # entity -> single record silently dropped three of them, so this maps entity -> list.
    by_entity: dict[str, list[dict]] = {}
    for record in evidenced:
        if record.get("is_synthetic"):
            continue
        by_entity.setdefault(key(record["legal_underwriter"]), []).append(record)

    records, used, next_id = [], set(), 200
    for group in src["groups"]:
        for entity in group["entities"]:
            k = key(entity)
            guidance = (f"UNVERIFIED GUIDANCE from the Appendix A discovery seed "
                        f"({src['_dataset_date']}): {group['route_note']}")
            matches = by_entity.get(k)
            if matches:
                used.add(k)
                for match in matches:
                    match["insurer_group"] = match.get("insurer_group") or group["group"]
                    match["appendix_group"] = group["group"]
                    match["appendix_legal_name"] = entity
                    match["automation_notes"] = (match.get("automation_notes", "") + " | " +
                                                 guidance).strip(" |")
                    records.append(match)
                continue
            next_id += 1
            records.append({
                "registry_id": f"reg_{next_id}",
                "legal_underwriter": entity,
                "insurer_group": group["group"],
                "appendix_group": group["group"],
                "appendix_legal_name": entity,
                "brand_or_program": entity,
                "distribution_type": "unknown",
                "product_scope": "unknown",
                "status": "unresolved",
                "reason_code": None,
                "source_url": "Ontario regulator public rate-approval dataset, 2026-08-06 "
                              "(discovery seed; display names, not verified legal names)",
                "last_verified_at": "",
                "requires_current_validation": True,
                "automation_notes": guidance,
            })

    # Evidenced rows with no Appendix A counterpart — aggregators, brands, sandbox.
    for record in evidenced:
        if record.get("is_synthetic") or key(record["legal_underwriter"]) not in used:
            records.append(record)

    seen, deduped = set(), []
    for record in records:
        if record["registry_id"] in seen:
            continue
        seen.add(record["registry_id"])
        deduped.append(record)

    OUT.write_text(json.dumps({
        "_header_note": src["_header_note"],
        "_trailing_note": src["_trailing_note"],
        "_handling": src["_handling"],
        "records": deduped}, indent=2) + "\n", encoding="utf-8")

    market = [r for r in deduped if not r.get("is_synthetic")]
    appendix_only = [r for r in market if r.get("requires_current_validation")]
    print(f"merged: {len(deduped)} records ({len(market)} market, "
          f"{len(appendix_only)} appendix-only awaiting validation, "
          f"{len(market) - len(appendix_only)} evidenced)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
