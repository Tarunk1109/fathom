#!/usr/bin/env python3
"""Build the intended-payload file for a route, straight from the profile record.

    .venv/bin/python scripts/prepare_payload.py --route rt_reg_0002 --registry-id reg_0002

Every field is emitted through `Profile.tagged()`, so each value carries its source profile and
`P-PROFILE-BLEED-01` can see it. Nothing is hand-assembled — that is what produced INC-001.
"""
from __future__ import annotations

import argparse, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from packages.profiles import ProfileRegistry   # noqa: E402
from packages.registry import MarketRegistry    # noqa: E402

#: What a standard Ontario direct-writer journey asks for, per the Day 0 Sonnet taxonomy.
JOURNEY_FIELDS = [
    "first_name", "last_name", "date_of_birth", "gender", "marital_status",
    "address_line_1", "city", "province", "postal_code", "residence_type", "years_at_address",
    "licence_class", "licence_province", "years_licensed_g", "date_first_licensed",
    "driver_training", "prior_insurance", "years_continuously_insured",
    "at_fault_accidents_6y", "not_at_fault_accidents_6y", "convictions_3y",
    "licence_suspensions_3y", "claims_6y", "lapse_in_coverage",
    "vehicle_year", "vehicle_make", "vehicle_model", "vehicle_trim", "vehicle_ownership",
    "vehicle_purchase_type", "annual_km", "commute_one_way_km", "primary_use",
    "parking_location", "winter_tires", "other_drivers", "requested_effective_date",
    "third_party_liability_limit", "collision_deductible", "comprehensive_deductible",
    "dcpd_included", "opcf_49_elected", "opcf_44r_requested", "term_months", "telematics",
]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--route", required=True)
    ap.add_argument("--registry-id", required=True)
    ap.add_argument("--profile", default="profile_hypo_clean")
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)

    profile = ProfileRegistry().get(args.profile)
    record = MarketRegistry().get(args.registry_id)

    available = {**profile.facts, **profile.elections}
    fields = [f for f in JOURNEY_FIELDS if f in available]
    tagged = profile.tagged(fields)

    # Values come from a fully synthetic profile, so the file-scoped allowance is honest here —
    # and it is backed by ProfileRegistry.validate(), which refuses to load a hypothetical profile
    # carrying any vault-held operator value.
    synthetic = profile.hypothetical
    payload = {}
    if synthetic:
        payload["_pii_sweep"] = (
            "pii-sweep: allow-file STREET_ADDRESS,PC_FULL_POSTAL,DOB_LABELLED — every value in "
            f"this payload comes from {profile.profile_id}, which is synthetic in every field.")
    payload |= {
        "route_id": args.route,
        "target": record.quote_url,
        "profile_id": profile.profile_id,
        "brand": record.brand_or_program,
        "legal_underwriter": record.legal_underwriter,
        "_withheld": {
            "licence_number": "NEVER SUBMITTED — P-HYPO-LICENCE-01",
            "licence_plate": "NEVER SUBMITTED — P-PLATE-01",
            "contact_email": "not in profile; a callback-enrolment field is denied by P-HYPO-STEP-01",
            "contact_phone": "not in profile; human contact is denied by P-HYPO-HUMAN-01",
        },
        "fields": {name: {"value": str(value), "source_profile_id": value.source_profile_id}
                   for name, value in tagged.items()},
    }

    out = Path(args.out or f"out/pending/{args.route}.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"{out}  ({len(payload['fields'])} fields, all from {profile.profile_id})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
