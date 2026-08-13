#!/usr/bin/env python3
"""Build the FATHOM UI — final.md Part A.

    .venv/bin/python scripts/build_ui.py     # called automatically by scripts/run_all.py

Reads the live exports (`out/registry.json`, `out/results.json`, `out/runs.json`, the policy
audit chain, the evidence chain) and the profile/registry sources, and emits one self-contained
payload embedded in `ui/index.html` alongside the hand-written `ui/styles.css` and `ui/app.js`.
No new API layer (final.md §A4) — the browser reads a JSON blob embedded in the page, not a
fetch() call, so the page works from a plain double-click (`file://`) as well as from a server.

**Depth is derived from real data, not invented per-site stage labels.** The web executor does not
tag which of "entry / intake / vehicle / driver / coverage / price" a given step belongs to — each
insurer's journey shape differs, and asserting a per-site stage would be a guess dressed as a
measurement. Instead, depth is the highest *canonical field category* actually filled across a
route's real steps (`STAGE_FIELDS` below, sourced from the same ontology the executor fills from),
with a returned price as the deepest state. This is honest: it says exactly what data the route
actually collected, nothing more.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from packages.evidence import EvidenceStore                      # noqa: E402
from packages.policy.audit import AuditLog, DEFAULT_AUDIT_PATH    # noqa: E402
from packages.policy.rules import DEFAULT_RULES                  # noqa: E402
from packages.profiles import ProfileRegistry                    # noqa: E402
from packages.registry import MarketRegistry                     # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "out"
UI = ROOT / "ui"

# --------------------------------------------------------------------------------------
# Depth model — six stages, matching final.md §A1's "entry page -> intake -> vehicle ->
# driver -> coverage -> price". Field buckets sourced from packages/executors/web/ontology.py's
# canonical field set, so the mapping is the same one the executor actually fills from.
# --------------------------------------------------------------------------------------

STAGE_LABELS = ["surface", "entry", "intake", "vehicle", "driver", "coverage", "price"]

STAGE_FIELDS = {
    "intake": {"first_name", "last_name", "date_of_birth", "gender", "marital_status",
              "address_line_1", "city", "province", "postal_code", "residence_type",
              "years_at_address", "contact_email", "contact_phone"},
    "vehicle": {"vehicle_year", "vehicle_make", "vehicle_model", "vehicle_trim",
               "vehicle_ownership", "vehicle_purchase_type", "annual_km",
               "commute_one_way_km", "primary_use", "parking_location", "winter_tires",
               "licence_plate"},
    "driver": {"licence_class", "licence_number", "licence_province", "years_licensed_g",
              "date_first_licensed", "driver_training", "prior_insurance",
              "years_continuously_insured", "at_fault_accidents_6y",
              "not_at_fault_accidents_6y", "convictions_3y", "licence_suspensions_3y",
              "claims_6y", "lapse_in_coverage", "other_drivers"},
    "coverage": {"third_party_liability_limit", "collision_deductible",
                "comprehensive_deductible", "dcpd_included", "opcf_49_elected",
                "opcf_44r_requested", "term_months", "telematics", "income_replacement"},
}


def stage_of(field_name: str) -> str | None:
    for stage, fields in STAGE_FIELDS.items():
        if field_name in fields:
            return stage
    return None


def compute_depth(run: dict | None, registry_record: dict) -> dict:
    """Return {stage_index, stage_label, reached_fields, terminal} for one route.

    `run` is a `runs.json` entry if the route was executed this session, else None (never
    attempted, or attempted outside this session — e.g. Sonnet's Day 0 hand probe).
    """
    if run is None:
        if registry_record.get("status") in (None, "reconnaissance_pending") or \
                registry_record.get("requires_current_validation"):
            return {"stage_index": 0, "stage_label": "surface", "reached_fields": [],
                   "note": "not yet attempted"}
        # Attempted outside this session (Sonnet's Day 0 hand probe) — depth from its
        # recorded reason code alone, since no step-level data exists for a hand-run probe.
        if registry_record.get("reason_code") == "licence_number_required_hypothetical_profile":
            return {"stage_index": STAGE_LABELS.index("driver"), "stage_label": "driver",
                   "reached_fields": [], "note": "hand-probed 2026-08-09, see DAY0_PROBE.md"}
        return {"stage_index": 1, "stage_label": "entry", "reached_fields": [],
               "note": "attempted outside this session"}

    if run.get("premium") is not None:
        return {"stage_index": 6, "stage_label": "price", "reached_fields": [],
               "note": "returned a price"}

    filled = sorted({f for step in run.get("steps", []) for f in step.get("fields_filled", [])})
    reached_stages = {stage_of(f) for f in filled} - {None}
    if not reached_stages:
        # Something was attempted (a navigate happened) but no field was ever filled.
        stage_index = 1 if run.get("steps") else 0
        return {"stage_index": stage_index, "stage_label": STAGE_LABELS[stage_index],
               "reached_fields": filled, "note": run.get("stopping_step", "")}

    deepest = max(reached_stages, key=lambda s: STAGE_LABELS.index(s))
    return {"stage_index": STAGE_LABELS.index(deepest), "stage_label": deepest,
           "reached_fields": filled, "note": run.get("stopping_step", "")}


# --------------------------------------------------------------------------------------
# Eligibility Frontier (final.md B1) — pure inversion of reason codes already collected.
# --------------------------------------------------------------------------------------

#: fathom.md §8.2's ReasonCode -> unlock taxonomy. Keyed on both forms found in this codebase's
#: actual data: the full enum values §8.2 specifies (used where a registry row was hand-entered,
#: e.g. reg_0001) and the short RC_XXX codes the executor's `_reason_for()` emits in practice.
#: Reconciling the two here rather than picking one, because both are real, both are live in the
#: exported data, and silently matching only one would drop real rows from the ladder.
UNLOCK_CONDITIONS = {
    "licence_class_insufficient": "obtain_g2", "RC_LICENCE_CLASS": "obtain_g2",
    "licence_number_required_hypothetical_profile": "run_under_operator_profile",
    "RC_HYPO_LICENCE_REQUIRED": "run_under_operator_profile",
    "no_owned_vehicle": "own_vehicle", "RC_NO_VEHICLE": "own_vehicle",
    "insufficient_driving_history": "accumulate_history", "RC_NO_HISTORY": "accumulate_history",
    "no_prior_insurance_record": "hold_policy_12m", "RC_NO_PRIOR_INSURANCE": "hold_policy_12m",
    "membership_or_group_required": "join_group", "RC_MEMBERSHIP": "join_group",
    "licensed_intermediary_required": "engage_broker", "RC_BROKER_ONLY": "engage_broker",
    "product_not_standard_ppa": None, "RC_PRODUCT_SCOPE": None,
    "not_writing_new_business": None, "RC_NOT_WRITING": None,
    "access_control_encountered": None, "RC_ACCESS_CONTROL": None,
    "human_checkpoint_required": "operator_action", "RC_HUMAN_REQUIRED": "operator_action",
    "reason_not_stated": None, "RC_UNKNOWN": None,
}

UNLOCK_LABELS = {
    "obtain_g2": "Obtain a G2 licence",
    "run_under_operator_profile": "Run under the operator's own profile (real licence number)",
    "own_vehicle": "Own the vehicle being insured",
    "accumulate_history": "Accumulate Canadian driving history",
    "hold_policy_12m": "Hold a prior policy for 12 months",
    "join_group": "Join the required membership or group",
    "engage_broker": "Engage a licensed intermediary",
    "operator_action": "Operator personally engages — a human checkpoint was required",
}


def build_frontier(records: list[dict]) -> dict:
    """One rung per unlock condition; each rung counts the distinct rate sources it would open."""
    non_quoted = [r for r in records if r.get("status") not in
                 ("quoted_comparable", "quoted_non_comparable", None)
                 and not r.get("is_synthetic")
                 and not r.get("requires_current_validation")
                 and r.get("status") != "reconnaissance_pending"]

    rungs: dict[str, dict] = {}
    unlockable = 0
    for record in non_quoted:
        reason = record.get("reason_code")
        unlock = UNLOCK_CONDITIONS.get(reason)
        if unlock is None:
            continue
        unlockable += 1
        rung = rungs.setdefault(unlock, {"unlock": unlock,
                                         "label": UNLOCK_LABELS.get(unlock, unlock),
                                         "rate_sources": set(), "records": []})
        rung["rate_sources"].add(record.get("distinct_rate_source_id") or record["registry_id"])
        rung["records"].append({
            "registry_id": record["registry_id"],
            "brand": record.get("brand_or_program", ""),
            "reason_code": reason,
            "status": record.get("status"),
        })

    ladder = sorted(
        ({"unlock": r["unlock"], "label": r["label"], "opens_rate_sources": len(r["rate_sources"]),
          "records": r["records"]} for r in rungs.values()),
        key=lambda r: -r["opens_rate_sources"])

    closed = [{"registry_id": r["registry_id"], "brand": r.get("brand_or_program", ""),
              "reason_code": r.get("reason_code")}
             for r in non_quoted if UNLOCK_CONDITIONS.get(r.get("reason_code")) is None]

    return {"ladder": ladder, "total_non_quoted": len(non_quoted),
           "unlockable": unlockable, "closed_regardless": closed}


# --------------------------------------------------------------------------------------
# Assembly
# --------------------------------------------------------------------------------------


# Mirrors docs/PRIME_DIRECTIVES.md's enforcement table exactly. Curated, not re-derived, because
# "LIVE in this build's own operation" vs "tested but never naturally triggered" is a judgment
# call the audit log alone cannot make (a rule with zero DENY entries might be untriggered-but-live,
# or genuinely absent — the log can't tell those apart). Keep the two files in sync by hand.
ENFORCEMENT_TABLE = [
    {"area": "No PII in repo, logs or submission", "mechanism": "tools/pii_sweep.py, CI + pre-commit", "status": "LIVE"},
    {"area": "No PII in policy audit or evidence chain", "mechanism": "field names + digest only, redacted before write", "status": "LIVE"},
    {"area": "Never bind, purchase, renew, cancel, modify", "mechanism": "P-BIND-01", "status": "LIVE"},
    {"area": "Never submit a signature or declaration", "mechanism": "P-SIGN-01", "status": "LIVE"},
    {"area": "Never submit payment information", "mechanism": "P-PAY-01", "status": "LIVE"},
    {"area": "Never bypass a CAPTCHA or bot control", "mechanism": "P-CAPTCHA-01", "status": "LIVE"},
    {"area": "Never enter credentials to an unregistered service", "mechanism": "P-AUTH-01", "status": "LIVE"},
    {"area": "Never continue after a stop request", "mechanism": "P-STOP-01", "status": "LIVE"},
    {"area": "Attempt and time budgets", "mechanism": "P-BUDGET-01, drawn down by the gate itself", "status": "LIVE"},
    {"area": "Never record without affirmative consent", "mechanism": "P-RECORD-01", "status": "DOCUMENTED-ONLY"},
    {"area": "Disclose automation at start of every call", "mechanism": "P-DISCLOSE-01", "status": "DOCUMENTED-ONLY"},
    {"area": "No licence number under a hypothetical profile", "mechanism": "P-HYPO-LICENCE-01", "status": "LIVE"},
    {"area": "No human contact under a hypothetical profile", "mechanism": "P-HYPO-HUMAN-01", "status": "LIVE"},
    {"area": "No commitment steps under a hypothetical profile", "mechanism": "P-HYPO-STEP-01", "status": "LIVE"},
    {"area": "No attestation under a hypothetical profile", "mechanism": "P-HYPO-ATTEST-01", "status": "LIVE"},
    {"area": "One submission, one profile", "mechanism": "P-PROFILE-BLEED-01", "status": "LIVE"},
    {"area": "No real destination without recorded approval", "mechanism": "P-APPROVAL-01", "status": "LIVE"},
    {"area": "Skip optional plate fields; blocked if mandatory", "mechanism": "P-PLATE-01", "status": "LIVE"},
    {"area": "Escalate identity/consent/coverage-advice", "mechanism": "P-HUMAN-01 -> checkpoint queue", "status": "LIVE"},
    {"area": "Every decision in a verifiable chain", "mechanism": "AuditLog.verify_chain(), concurrency-safe", "status": "LIVE"},
    {"area": "Fact-lock across insurers", "mechanism": "P-FACT-01", "status": "LIVE"},
    {"area": "Operator's own real information", "mechanism": "P-REAL-FACT-01", "status": "PARTIAL"},
    {"area": "No fabricated licence number", "mechanism": "P-LICENCE-01", "status": "PARTIAL"},
    {"area": "No third-party data without consent", "mechanism": "P-THIRDPARTY-01", "status": "PARTIAL"},
    {"area": "Sandbox-only never reaches a real destination", "mechanism": "P-SANDBOX-01", "status": "LIVE"},
    {"area": "Redaction before every write", "mechanism": "packages/redactor/ (regex, no vision)", "status": "LIVE"},
    {"area": "Voice disclosure prelude, consent state machine", "mechanism": "packages/executors/voice/", "status": "NOT-BUILT"},
    {"area": "No legal characterization", "mechanism": "manual review discipline", "status": "DOCUMENTED-ONLY"},
    {"area": "Hypothetical/sandbox results visibly labelled", "mechanism": "results.json sandbox field, UI badges", "status": "LIVE"},
]


def load_json(path: Path, default):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def main() -> int:
    registry_export = load_json(OUT / "registry.json", {"records": [], "metrics": {}})
    results = load_json(OUT / "results.json", [])
    runs = load_json(OUT / "runs.json", [])
    runs_by_route = {r["route_id"]: r for r in runs}

    market_registry = MarketRegistry()
    groups = market_registry.resolve_rate_sources()

    audit = AuditLog(DEFAULT_AUDIT_PATH)
    chain_ok, first_bad, chain_msg = (
        audit.verify_chain().ok, audit.verify_chain().first_bad_index,
        audit.verify_chain().describe())

    evidence = EvidenceStore()
    ev_ok, ev_bad, ev_msg = evidence.verify_chain()

    # Depth per registry record (route-level, keyed by registry_id).
    depths = {}
    for record in registry_export["records"]:
        route_id = f"rt_{record['registry_id']}"
        depths[record["registry_id"]] = {
            **compute_depth(runs_by_route.get(route_id), record),
            "registry_id": record["registry_id"],
            "route_id": route_id,
            "brand": record.get("brand_or_program", ""),
            "legal_underwriter": record.get("legal_underwriter", ""),
            "distinct_rate_source_id": record.get("distinct_rate_source_id", ""),
            "status": record.get("status"),
            "reason_code": record.get("reason_code"),
            "is_synthetic": record.get("is_synthetic", False),
            "evidence_artifact": record.get("evidence_artifact", ""),
            "last_verified_at": record.get("last_verified_at", ""),
        }

    # Market graph edges: brand -> rate source, with signal counts and hypothesis flag.
    graph_nodes = []
    for rate_source, members in groups.items():
        member_records = [market_registry.get(m) for m in members]
        if all(m.is_synthetic for m in member_records):
            continue
        signals = max((m.signals_agreeing for m in member_records), default=0)
        graph_nodes.append({
            "rate_source_id": rate_source,
            "legal_underwriter": member_records[0].legal_underwriter if member_records else "",
            "insurer_group": member_records[0].insurer_group if member_records else "",
            "signals_agreeing": signals,
            "evidenced": signals >= 2,
            "brands": [{"registry_id": m.registry_id, "brand": m.brand_or_program,
                       "distribution_type": m.distribution_type,
                       "insurer_group": m.insurer_group,
                       "hypothesis_with": m.dedup_hypothesis_with}
                      for m in member_records],
        })

    # Audit log entries for the Gate view (redacted fields only, matches on-disk shape).
    # Every field of AuditEntry.hashable() must round-trip to the browser, or the in-browser
    # "Verify chain" control recomputes a different hash than Python did and reports a false
    # break. session_id was missing here originally — found by actually clicking the button
    # against the real chain, which reported BROKEN at index 0 on an intact chain.
    audit_entries = [{
        "index": e.index, "timestamp": e.timestamp, "session_id": e.session_id,
        "route_id": e.route_id, "profile_id": e.profile_id, "action_kind": e.action_kind,
        "target_safe": e.target_safe, "verdict": e.verdict, "rule_id": e.rule_id,
        "explanation": e.explanation, "prev_hash": e.prev_hash, "entry_hash": e.entry_hash,
        "payload_fields": list(e.payload_fields), "payload_digest": e.payload_digest,
        "rationale_redacted": e.rationale_redacted,
    } for e in audit.entries]

    rules_table = [{"rule_id": r.rule_id, "verdict": r.verdict, "directive": r.directive,
                    "summary": r.summary} for r in DEFAULT_RULES]

    # Evidence artifacts for the Evidence view, with fetched (already-redacted) text.
    evidence_artifacts = []
    for a in evidence.artifacts:
        try:
            text = evidence.fetch(a.cid)
        except Exception:
            text = ""
        evidence_artifacts.append({
            "index": a.index, "cid": a.cid, "timestamp": a.timestamp, "route_id": a.route_id,
            "profile_id": a.profile_id, "kind": a.kind, "source": a.source,
            "redaction_rules_fired": list(a.redaction_rules_fired),
            "prev_hash": a.prev_hash, "entry_hash": a.entry_hash,
            "text_excerpt": text[:4000],
        })

    frontier = build_frontier(registry_export["records"])

    # Fabrication incident + scorecard figures (final.md B5).
    scorecard = {
        "fabrications_caught_pre_report": 1,
        "fabrications_shipped": 0,
        "policy_rules_total": len(rules_table),
        "policy_rules_live": sum(1 for r in DEFAULT_RULES if r.rule_id not in
                                 {"P-REAL-FACT-01", "P-LICENCE-01", "P-THIRDPARTY-01"}),
        "policy_rules_partial": 3,
        "concurrency_bug_found_and_fixed": True,
        "sandbox_routes_run": sum(1 for r in registry_export["records"] if r.get("is_synthetic")),
    }

    payload = {
        "generated_at": registry_export.get("generated_at", ""),
        "profile": {},
        "metrics": registry_export.get("metrics", {}),
        "records": registry_export["records"],
        "results": results,
        "depths": list(depths.values()),
        "graph_nodes": graph_nodes,
        "audit": {"entries": audit_entries, "chain_ok": chain_ok,
                  "message": chain_msg, "total": len(audit_entries)},
        "evidence": {"artifacts": evidence_artifacts, "chain_ok": ev_ok, "message": ev_msg},
        "rules": rules_table,
        "frontier": frontier,
        "scorecard": scorecard,
        "enforcement": ENFORCEMENT_TABLE,
    }

    try:
        profile = ProfileRegistry().primary()
        payload["profile"] = {
            "profile_id": profile.profile_id, "hypothetical": profile.hypothetical,
            "vehicle": " ".join(str(profile.facts.get(k, "")) for k in
                                ("vehicle_year", "vehicle_make", "vehicle_model",
                                 "vehicle_trim")).strip(),
            "requested_effective_date": profile.facts.get("requested_effective_date", ""),
        }
    except Exception:
        pass

    UI.mkdir(parents=True, exist_ok=True)
    data_json = json.dumps(payload, indent=None, separators=(",", ":"), default=str)
    (UI / "data.json").write_text(data_json, encoding="utf-8")

    shell = (ROOT / "ui" / "_shell.html").read_text(encoding="utf-8")
    html = shell.replace("/*__FATHOM_DATA__*/", data_json)
    (UI / "index.html").write_text(html, encoding="utf-8")

    print(f"  ui/index.html   ({len(html):,} bytes, {len(audit_entries)} audit entries, "
          f"{len(evidence_artifacts)} evidence artifacts, {len(graph_nodes)} rate sources)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
