#!/usr/bin/env python3
"""End-to-end run: execute routes, normalize, dedup, export, build the UI.

    .venv/bin/python scripts/run_all.py                    # sandbox routes
    .venv/bin/python scripts/run_all.py --include-real     # + approved real routes only

Produces every §15 deliverable that exists today:

    out/registry.json  out/registry.csv  out/results.json  out/run_report.md  ui/index.html

Real destinations are included only when the route carries a recorded approval (`P-APPROVAL-01`,
default deny). Without `--include-real` they are not attempted at all.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from packages.evidence import EvidenceStore                             # noqa: E402
from packages.executors.web import WebExecutor                          # noqa: E402
from packages.normalizer import BENCHMARK, comparability_note, normalize, rank  # noqa: E402
from packages.policy import ApprovalStore, PolicyEngine, SessionContext  # noqa: E402
from packages.profiles import ProfileRegistry                           # noqa: E402
from packages.registry import MarketRegistry                            # noqa: E402

OUT = Path(__file__).resolve().parents[1] / "out"
UI = Path(__file__).resolve().parents[1] / "ui"

SANDBOX_TAG = "SANDBOX"


# The old Python-templated UI generator that lived here (run_parameters_html + build_ui)
# is superseded by final.md Part A's UI overhaul. The UI is now built by scripts/build_ui.py,
# invoked at the end of main() below, reading the exports this script just wrote.


def collapse_section(registry, groups) -> list[str]:
    """The dedup finding, written out. §9.3 asserts only at >=2 agreeing signals."""
    market = [r for r in registry.records.values() if not r.is_synthetic]
    sources = {r.distinct_rate_source_id for r in market}
    lines = ["## Rate-source collapse", "",
             f"**{len(market)} market brands and legal entities resolve to "
             f"{len(sources)} distinct rate sources.**", "",
             "FATHOM counts distinct rate sources, not brands. `same_rate_source_as` is asserted "
             "only where at least two independent signals agree (§9.3); a single-signal match is "
             "recorded as a hypothesis and never merged.", ""]

    merges = []
    for rate_source, members in sorted(groups.items()):
        records = [registry.get(m) for m in members]
        if len(records) < 2 or all(r.is_synthetic for r in records):
            continue
        merges.append((rate_source, records))

    if not merges:
        lines += ["No merges were evidenced.", ""]
    for rate_source, records in merges:
        signals = max(r.signals_agreeing for r in records)
        lines += [
            f"### `{rate_source}` — {len(records)} brands, {signals} agreeing signals", "",
            f"**Legal underwriter: {records[0].legal_underwriter}**", "",
        ]
        lines += [f"- {r.brand_or_program}" for r in records]
        lines += ["", f"Evidence: {records[0].automation_notes[:400]}", ""]

    hypotheses = [r for r in market if r.dedup_hypothesis_with]
    lines += [f"Single-signal hypotheses recorded but **not** merged: {len(hypotheses)}.", "",
              "The true number of distinct rate sources is very likely lower than "
              f"{len(sources)} — several entities within the same group probably share filed "
              "rates and FATHOM has not evidenced it. An unevidenced merge would inflate the "
              "dedup metric, which §18 names directly as an anti-goal.", ""]
    return lines


def sandbox_tag(r) -> str:
    return f" `[{SANDBOX_TAG}]`" if r.sandbox else ""


def write_run_report(results, registry, note, evidence, engine, groups=None, profile=None) -> Path:
    metrics = registry.metrics()
    chain_ok, _, chain_note = evidence.verify_chain()
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")

    lines = ["# FATHOM run report", "", f"Generated {now}.", ""]

    # --- Header: run parameters -----------------------------------------------------------
    lines += ["## Run parameters", ""]
    if profile:
        facts = profile.facts
        vehicle = " ".join(str(facts.get(k, "")) for k in
                           ("vehicle_year", "vehicle_make", "vehicle_model", "vehicle_trim")).strip()
        lines += [
            f"- **Profile:** `{profile.profile_id}` "
            f"({'hypothetical' if profile.hypothetical else 'real, vault-held'})",
            f"- **Vehicle:** {vehicle or 'unspecified'}",
            f"- **Requested effective date:** {facts.get('requested_effective_date', 'unspecified')}",
            "- **Benchmark coverage package (§8.5):** "
            f"${BENCHMARK['third_party_liability_limit']:,} third-party liability, "
            f"${BENCHMARK['collision_deductible']} collision deductible, "
            f"${BENCHMARK['comprehensive_deductible']} comprehensive deductible, "
            f"DCPD {BENCHMARK['dcpd']}, OPCF 44R {BENCHMARK['opcf_44r_family_protection']}, "
            f"{BENCHMARK['term_months']}-month term",
        ]
    lines += [""]

    lines += [
        "All results below were retrieved under `profile_hypo_clean`, a **hypothetical** "
        "clean-record driver permitted by the organizer Q&A (AC-001), unless otherwise noted. "
        "They are not quotes for the operator, and they are labelled as hypothetical everywhere "
        f"they appear. Rows tagged `[{SANDBOX_TAG}]` are from the local synthetic test sites "
        "(§11.5), never a real destination, and are excluded from every market metric.", "",
    ]

    # --- Named findings ---------------------------------------------------------------------
    lines += [
        "## Named findings", "",
        "**No real insurer route returned a price under the hypothetical profile.** Every "
        f"priced, benchmark-comparable outcome below is tagged `[{SANDBOX_TAG}]`. Real routes "
        "returned either a terminal blocker or an unresolved capability limit; the itemized "
        "reason per route is in the coverage ledger below and in `docs/LIMITATIONS.md`.", "",
        "**Aggregator routes are Cloudflare-fronted (D-AGG).** Rates.ca and LowestRates.ca both "
        "returned a managed challenge at the entry page. Detected and respected, never bypassed "
        "(§2.1). The two broadest Ontario comparison routes are closed to an agent that acts "
        "honestly — a real, evidenced property of this market. Accepted; not retried.", "",
        "**The Aviva amalgamation, evidenced.** Aviva Insurance, Pilot Insurance, Elite Insurance "
        "and Traders General Insurance collapse to one legal entity, Aviva Insurance Company of "
        "Canada, effective 2026-01-01, on two agreeing signals "
        "(`underwriter_disclosed` + `regulatory_amalgamation`, source: "
        "https://www.avivacanada.com/). See § Rate-source collapse below.", "",
        "**A fabricated premium was caught before it reached this report.** A live run against "
        "MyChoice.ca returned `$177.83` from landing-page marketing copy with zero fields filled. "
        "Fixed and locked down as a regression test. Full account in `docs/SAFETY.md` § "
        '"Worked example: the fabricated premium"; reproduce with `make demo-fabrication`.', "",
    ]

    # --- Coverage ledger: every route ever attempted, registry-level ------------------------
    # Built from the registry, not just this run's `results` — Sonnet (reg_0001) was attempted
    # by hand on Day 0, before this executor existed, and its finding (RC_HYPO_LICENCE_REQUIRED,
    # the market-wide pattern this build repeatedly confirmed) belongs here even though it has
    # no entry in results.json, which covers only outcomes from an automated executor run.
    channel_by_registry_id = {r.registry_id: r.channel for r in results}
    lines += [
        "## Coverage ledger", "",
        "Every route ever attempted, hand-probed or automated. `unresolved` stays `unresolved` — "
        "never silently reclassified. Rows never attempted (reconnaissance-pending routes and "
        "unvalidated Appendix A rows) are not listed here — see § Metrics for their counts.", "",
        "| Registry ID | Brand | Legal underwriter | Rate source | Channel | Status | Reason | "
        "Timestamp | Evidence CID |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    attempted_records = [
        r for r in registry.records.values()
        if r.status != "reconnaissance_pending" and not r.requires_current_validation
    ]
    for rec in sorted(attempted_records, key=lambda r: r.registry_id):
        sandbox_row = rec.is_synthetic
        tag = f" **[{SANDBOX_TAG}]**" if sandbox_row else ""
        channel = channel_by_registry_id.get(rec.registry_id,
                                              "web_manual_probe" if rec.registry_id == "reg_0001"
                                              else "web")
        cid = (rec.evidence_artifact[:28] + "…") if rec.evidence_artifact else "—"
        lines.append(
            f"| `{rec.registry_id}`{tag} | {rec.brand_or_program} | {rec.legal_underwriter} | "
            f"`{rec.distinct_rate_source_id}` | {channel} | `{rec.status}` | "
            f"{rec.reason_code or '—'} | {rec.last_verified_at or '—'} | `{cid}` |")
    lines += [""]

    # --- Outcomes summary ---------------------------------------------------------------------
    lines += [
        "## Outcomes", "",
        "| Route | Profile | Status | Reason | Annual | Assessment | Parity | Evidence |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for r in results:
        premium = r.price.get("annual_premium")
        lines.append(
            f"| `{r.route_id}`{sandbox_tag(r)} | `{r.profile_id}` | `{r.status}` | "
            f"{r.reason_code or '—'} | {f'${premium:,.2f}' if premium else '—'} | "
            f"{r.assessment.verdict} | {r.parity['parity_confidence']} | "
            f"{len(r.evidence['artifact_cids'])} artifacts |")

    lines += ["", "## Comparability", "", note, "", "## Coverage variance", ""]
    for r in results:
        if not r.variance_from_benchmark:
            continue
        lines.append(f"**`{r.route_id}`{sandbox_tag(r)}** differs from the §8.5 benchmark in "
                     f"{len(r.variance_from_benchmark)} respect(s):")
        lines += [f"- {v}" for v in r.variance_from_benchmark] + [""]

    lines += ["## Terminal blockers", ""]
    for r in results:
        if not r.decline:
            continue
        lines.append(f"**`{r.route_id}`{sandbox_tag(r)}** — `{r.status}` / `{r.reason_code}`  ")
        lines.append(f"Stopping step: {r.decline['stopping_step']}  ")
        lines.append(f"Policy rules fired: {', '.join(r.decline['policy_rules_fired']) or '—'}  ")
        lines.append(f"Stated reason: {r.decline['stated_reason_redacted'][:220]}")
        lines.append("")

    if groups:
        lines += collapse_section(registry, groups)

    lines += ["## Metrics", "", "| Metric | Value |", "| --- | --- |"]
    lines += [f"| {k.replace('_', ' ')} | {v} |" for k, v in metrics.items()
              if k != "denominator_note"]
    lines += ["", metrics["denominator_note"], "",
              "## Chain verification", "",
              f"- Evidence chain: {chain_note}",
              f"- Policy audit chain: {engine.verify_chain().describe()}", ""]

    path = OUT / "run_report.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--include-real", action="store_true",
                    help="also attempt real routes that carry a recorded approval")
    ap.add_argument("--profile", default="profile_hypo_clean")
    args = ap.parse_args(argv)

    profiles = ProfileRegistry()
    profile = profiles.get(args.profile)
    registry = MarketRegistry()
    approvals = ApprovalStore()
    engine = PolicyEngine()
    evidence = EvidenceStore()
    executor = WebExecutor(engine, evidence)

    targets = [(rec.registry_id, rec.quote_url, f"rt_{rec.registry_id}")
               for rec in registry.records.values()
               if rec.is_synthetic and rec.quote_url]
    if args.include_real:
        targets += [(rec.registry_id, rec.quote_url, f"rt_{rec.registry_id}")
                    for rec in registry.records.values()
                    if not rec.is_synthetic and rec.quote_url
                    and f"rt_{rec.registry_id}" in approvals.approved_route_ids]

    # Real routes are expensive and rate-limited; reuse a captured RunResult when one exists so
    # the deliverables can be regenerated without hammering a live insurer (§18).
    def cached(route_id: str):
        path = OUT / "runs" / f"{route_id.replace('rt_', '')}.json"
        if not path.exists():
            return None
        from packages.executors.web import RunResult
        data = json.loads(path.read_text(encoding="utf-8"))
        known = {f for f in RunResult.__dataclass_fields__}
        return RunResult(**{k: v for k, v in data.items() if k in known})

    # Evidence timestamp for a result traces to the actual artifact's capture time, not to when
    # this script happened to run — the artifact is the evidence, so its own timestamp is the
    # honest one to report (finish.md §3.1 header requirement).
    artifact_by_cid = {a.cid: a for a in evidence.artifacts}

    results, runs = [], []
    for index, (registry_id, url, route_id) in enumerate(sorted(targets), start=1):
        is_synthetic = registry.get(registry_id).is_synthetic
        ctx = SessionContext(
            session_id=f"ses_{route_id}", profile_id=profile.profile_id,
            hypothetical=profile.hypothetical, sandbox_only=profile.sandbox_only,
            fact_lock=profile.fact_lock(), approved_routes=approvals.approved_route_ids)
        run = cached(route_id) if not is_synthetic else None
        if run is None:
            run = executor.run(route_id=route_id, entry_url=url, profile=profile, ctx=ctx)
        runs.append(run)
        print(f"  {run.summary()}" + ("   [cached]" if not is_synthetic else ""))

        registry.record_outcome(
            registry_id, status=run.status, reason_code=run.reason_code,
            evidence_cid=run.evidence_cids[0] if run.evidence_cids else "",
            quote_reference=run.quote_reference, premium=run.premium)

        result_timestamp = ""
        for cid in run.evidence_cids:
            artifact = artifact_by_cid.get(cid)
            if artifact:
                result_timestamp = artifact.timestamp
                break

        results.append(normalize(run, result_id=f"res_{index:04d}", registry_id=registry_id,
                                 rate_source_id="", sandbox=is_synthetic,
                                 timestamp=result_timestamp))

    groups = registry.resolve_rate_sources()
    for result in results:
        result.distinct_rate_source_id = registry.get(result.registry_id).distinct_rate_source_id

    ordered = rank(results)
    note = comparability_note(results)

    OUT.mkdir(parents=True, exist_ok=True)
    registry.export_json(OUT / "registry.json")
    registry.export_csv(OUT / "registry.csv")
    (OUT / "results.json").write_text(
        json.dumps([r.to_dict() for r in ordered], indent=2, default=str) + "\n", encoding="utf-8")
    (OUT / "runs.json").write_text(
        json.dumps([asdict(r) for r in runs], indent=2, default=str) + "\n", encoding="utf-8")
    report = write_run_report(ordered, registry, note, evidence, engine, groups, profile)

    # final.md Part A's UI reads these exports fresh from disk rather than the in-memory
    # objects above, so it must run as a separate process after every write above lands —
    # otherwise it would build against the previous run's registry.json/results.json.
    ui_proc = subprocess.run([sys.executable, str(Path(__file__).parent / "build_ui.py")],
                             capture_output=True, text=True)
    if ui_proc.returncode != 0:
        print(ui_proc.stdout, ui_proc.stderr, sep="\n")
        print("  WARNING: UI build failed — see output above. Other deliverables are still current.")
    else:
        print(ui_proc.stdout.strip())

    print(f"\n{note}\n")
    print(f"  registry     {OUT / 'registry.json'}  ({len(registry)} records)")
    print(f"  results      {OUT / 'results.json'}  ({len(results)} outcomes)")
    print(f"  report       {report}")

    # Re-check against the final on-disk state, not the pre-loop snapshot — artifacts appended
    # during this run (e.g. sandbox routes) are not in `artifact_by_cid`, which was built once
    # before the loop, and would otherwise be misreported as unresolvable.
    final_known_cids = {a.cid for a in EvidenceStore().artifacts}
    unresolved_evidence = [r for r in ordered
                           if r.evidence["artifact_cids"]
                           and not all(c in final_known_cids for c in r.evidence["artifact_cids"])]
    if unresolved_evidence:
        print(f"\n  WARNING: {len(unresolved_evidence)} result(s) reference an evidence CID not "
              f"resolvable in the current store: "
              f"{[r.route_id for r in unresolved_evidence]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
