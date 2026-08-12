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
import sys
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from packages.evidence import EvidenceStore                             # noqa: E402
from packages.executors.web import WebExecutor                          # noqa: E402
from packages.normalizer import comparability_note, normalize, rank     # noqa: E402
from packages.policy import ApprovalStore, PolicyEngine, SessionContext  # noqa: E402
from packages.profiles import ProfileRegistry                           # noqa: E402
from packages.registry import MarketRegistry                            # noqa: E402

OUT = Path(__file__).resolve().parents[1] / "out"
UI = Path(__file__).resolve().parents[1] / "ui"


def build_ui(results, registry, groups, engine, evidence, note: str) -> Path:
    """Three views in one file: results, market graph, policy gate log (§12). Ugly is fine."""
    def esc(text) -> str:
        return (str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))

    rows = []
    for r in results:
        premium = r.price.get("annual_premium")
        price_cell = f"${premium:,.2f}" if premium else "—"
        variance = "".join(f"<li>{esc(v)}</li>" for v in r.variance_from_benchmark)
        verdict_class = r.assessment.verdict.lower()
        rows.append(f"""
        <tr class="{verdict_class}">
          <td><strong>{esc(r.route_id)}</strong><div class="sub">{esc(r.profile_id)}</div></td>
          <td><span class="pill {esc(r.status)}">{esc(r.status)}</span>
              {f'<div class="sub">{esc(r.reason_code)}</div>' if r.reason_code else ''}</td>
          <td class="cov">{'<ul>' + variance + '</ul>' if variance
                           else '<span class="ok">matches benchmark</span>'}</td>
          <td class="num">{price_cell}</td>
          <td><span class="verdict {verdict_class}">{esc(r.assessment.verdict)}</span>
              <div class="sub">conf {esc(r.assessment.confidence_indicator)} ·
              evidence {esc(r.assessment.evidence_status)}</div></td>
          <td class="sub">{esc(r.parity['parity_confidence'])}</td>
          <td class="sub">{len(r.evidence['artifact_cids'])} artifacts</td>
        </tr>""")

    graph_rows = []
    for rate_source, members in sorted(groups.items()):
        records = [registry.get(m) for m in members]
        if all(rec.is_synthetic for rec in records):
            continue
        brands = ", ".join(esc(rec.brand_or_program) for rec in records)
        underwriters = ", ".join(sorted({esc(rec.legal_underwriter) for rec in records}))
        signals = max(rec.signals_agreeing for rec in records)
        hypo = [rec for rec in records if rec.dedup_hypothesis_with]
        merged = signals >= 2 and len(records) > 1
        graph_rows.append(f"""
        <tr class="{'merged' if merged else ''}">
            <td><strong>{esc(rate_source)}</strong></td><td>{brands}</td>
            <td class="sub">{underwriters}</td>
            <td class="num">{signals or '—'}</td>
            <td class="sub">{'hypothesis: ' + esc(hypo[0].dedup_hypothesis_with) if hypo
                             else ('merged' if signals >= 2 else 'distinct')}</td></tr>""")

    audit_rows = "".join(
        f"<tr><td class='num'>{e.index}</td><td><span class='pill {e.verdict}'>{e.verdict}</span></td>"
        f"<td>{esc(e.rule_id)}</td><td class='sub'>{esc(e.action_kind)}</td>"
        f"<td class='sub'>{esc(e.target_safe)[:70]}</td></tr>"
        for e in engine.audit.entries[-60:])

    metrics = registry.metrics()
    metric_rows = "".join(
        f"<tr><td>{esc(k.replace('_', ' '))}</td><td class='num'>{esc(v)}</td></tr>"
        for k, v in metrics.items() if k != "denominator_note")

    chain_ok, _, chain_note = evidence.verify_chain()
    policy_chain = engine.verify_chain()

    html = f"""<!doctype html><html><head><meta charset="utf-8">
<title>FATHOM — Ontario auto market instrument</title>
<style>
 body{{font-family:system-ui,-apple-system,sans-serif;margin:0;background:#f6f7f9;color:#111}}
 header{{background:#0f172a;color:#fff;padding:22px 28px}}
 header h1{{margin:0;font-size:20px;letter-spacing:.5px}}
 header p{{margin:6px 0 0;color:#94a3b8;font-size:13px}}
 main{{padding:24px 28px;max-width:1240px}}
 h2{{font-size:15px;text-transform:uppercase;letter-spacing:.08em;color:#475569;
     margin:34px 0 10px}}
 table{{width:100%;border-collapse:collapse;background:#fff;border:1px solid #e2e8f0;
        border-radius:6px;overflow:hidden;font-size:14px}}
 th{{text-align:left;background:#f1f5f9;padding:9px 12px;font-size:12px;color:#475569;
     text-transform:uppercase;letter-spacing:.05em}}
 td{{padding:10px 12px;border-top:1px solid #eef2f7;vertical-align:top}}
 .num{{text-align:right;font-variant-numeric:tabular-nums}}
 .sub{{color:#64748b;font-size:12px}}
 .cov ul{{margin:0;padding-left:16px}} .cov li{{margin:2px 0;color:#b45309}}
 .ok{{color:#15803d}}
 .pill{{display:inline-block;padding:2px 8px;border-radius:99px;font-size:11px;font-weight:600;
        background:#e2e8f0;color:#334155}}
 .pill.quoted_comparable{{background:#dcfce7;color:#166534}}
 .pill.blocked{{background:#fee2e2;color:#991b1b}}
 .pill.manual_handoff{{background:#fef3c7;color:#92400e}}
 .pill.callback_required{{background:#e0e7ff;color:#3730a3}}
 .pill.DENY{{background:#fee2e2;color:#991b1b}} .pill.ALLOW{{background:#dcfce7;color:#166534}}
 .pill.ESCALATE{{background:#fef3c7;color:#92400e}}
 .verdict{{font-weight:700;font-size:12px}}
 .verdict.pass{{color:#15803d}} .verdict.caution{{color:#b45309}} .verdict.fail{{color:#991b1b}}
 .note{{background:#fff7ed;border:1px solid #fed7aa;color:#7c2d12;padding:12px 14px;
        border-radius:6px;font-size:14px;margin:10px 0 0}}
 .banner{{background:#fef3c7;border:1px solid #fcd34d;color:#78350f;padding:10px 14px;
          border-radius:6px;font-size:13px;font-weight:600}}
 tr.merged{{background:#ecfdf5}} tr.merged td:first-child{{border-left:3px solid #10b981}}
 .grid{{display:grid;grid-template-columns:1fr 1fr;gap:24px}}
 @media(max-width:900px){{.grid{{grid-template-columns:1fr}}}}
</style></head><body>
<header>
  <h1>FATHOM</h1>
  <p>Ontario private-passenger auto market instrument · generated
     {datetime.now(timezone.utc).isoformat(timespec='seconds')}</p>
</header>
<main>
  <div class="banner">Results below were retrieved under <code>profile_hypo_clean</code>, a
     <strong>hypothetical</strong> clean-record driver. They are not quotes for the operator.
     Synthetic sandbox routes are excluded from all market metrics.</div>

  <h2>Results</h2>
  <p class="note">{esc(note)}</p>
  <table>
    <tr><th>Route</th><th>Status</th><th>Coverage vs benchmark</th><th>Annual</th>
        <th>Assessment</th><th>Parity</th><th>Evidence</th></tr>
    {''.join(rows)}
  </table>
  <p class="sub">Sorted by price. Coverage differences render above price differences, and the
     lowest number is never labelled best (§9.7).</p>

  <div class="grid">
    <div>
      <h2>Market graph — brands to rate sources</h2>
      <table>
        <tr><th>Rate source</th><th>Brands</th><th>Legal underwriter</th><th>Signals</th>
            <th>Dedup</th></tr>
        {''.join(graph_rows)}
      </table>
      <p class="sub">§9.3: <code>same_rate_source_as</code> is asserted only at two or more
         agreeing signals. A single-signal match is recorded as a hypothesis, never merged.</p>
    </div>
    <div>
      <h2>Metrics</h2>
      <table>{metric_rows}</table>
      <p class="sub">{esc(metrics['denominator_note'])}</p>
      <p class="sub">Evidence chain: {esc(chain_note)}<br>
         Policy audit chain: {esc(policy_chain.describe())}</p>
    </div>
  </div>

  <h2>Policy gate — last 60 decisions</h2>
  <table>
    <tr><th>#</th><th>Verdict</th><th>Rule</th><th>Action</th><th>Target</th></tr>
    {audit_rows}
  </table>
  <p class="sub">Every decision, allow or deny, is appended to a hash-chained log. Verify with
     <code>make verify</code>.</p>
</main></body></html>"""

    UI.mkdir(parents=True, exist_ok=True)
    path = UI / "index.html"
    path.write_text(html, encoding="utf-8")
    return path


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


def write_run_report(results, registry, note, evidence, engine, groups=None) -> Path:
    metrics = registry.metrics()
    chain_ok, _, chain_note = evidence.verify_chain()
    lines = [
        "# FATHOM run report",
        "",
        f"Generated {datetime.now(timezone.utc).isoformat(timespec='seconds')}.",
        "",
        "All results below were retrieved under `profile_hypo_clean`, a **hypothetical** "
        "clean-record driver permitted by the organizer Q&A (AC-001). They are not quotes for the "
        "operator, and they are labelled as hypothetical everywhere they appear.",
        "",
        "## Outcomes",
        "",
        "| Route | Profile | Status | Reason | Annual | Assessment | Parity | Evidence |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for r in results:
        premium = r.price.get("annual_premium")
        lines.append(
            f"| `{r.route_id}` | `{r.profile_id}` | `{r.status}` | "
            f"{r.reason_code or '—'} | {f'${premium:,.2f}' if premium else '—'} | "
            f"{r.assessment.verdict} | {r.parity['parity_confidence']} | "
            f"{len(r.evidence['artifact_cids'])} artifacts |")

    lines += ["", "## Comparability", "", note, "", "## Coverage variance", ""]
    for r in results:
        if not r.variance_from_benchmark:
            continue
        lines.append(f"**`{r.route_id}`** differs from the §8.5 benchmark in "
                     f"{len(r.variance_from_benchmark)} respect(s):")
        lines += [f"- {v}" for v in r.variance_from_benchmark] + [""]

    lines += ["## Terminal blockers", ""]
    for r in results:
        if not r.decline:
            continue
        lines.append(f"**`{r.route_id}`** — `{r.status}` / `{r.reason_code}`  ")
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

    results, runs = [], []
    for index, (registry_id, url, route_id) in enumerate(sorted(targets), start=1):
        ctx = SessionContext(
            session_id=f"ses_{route_id}", profile_id=profile.profile_id,
            hypothetical=profile.hypothetical, sandbox_only=profile.sandbox_only,
            fact_lock=profile.fact_lock(), approved_routes=approvals.approved_route_ids)
        run = cached(route_id) if not registry.get(registry_id).is_synthetic else None
        if run is None:
            run = executor.run(route_id=route_id, entry_url=url, profile=profile, ctx=ctx)
        runs.append(run)
        print(f"  {run.summary()}"
              + ("   [cached]" if not registry.get(registry_id).is_synthetic else ""))

        registry.record_outcome(
            registry_id, status=run.status, reason_code=run.reason_code,
            evidence_cid=run.evidence_cids[0] if run.evidence_cids else "",
            quote_reference=run.quote_reference, premium=run.premium)
        results.append(normalize(run, result_id=f"res_{index:04d}", registry_id=registry_id,
                                 rate_source_id=""))

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
    report = write_run_report(ordered, registry, note, evidence, engine, groups)
    ui = build_ui(ordered, registry, groups, engine, evidence, note)

    print(f"\n{note}\n")
    print(f"  registry     {OUT / 'registry.json'}  ({len(registry)} records)")
    print(f"  results      {OUT / 'results.json'}  ({len(results)} outcomes)")
    print(f"  report       {report}")
    print(f"  ui           {ui}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
