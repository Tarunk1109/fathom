"""Market registry and rate-source dedup — FATHOM §8.3, §9.3.

The registry counts **distinct rate sources**, not brands (§18). Several consumer brands can sit on
one legal underwriter's filed rates, and a comparison that counts them separately inflates its own
coverage number.

Fingerprinting (§9.3), kept intact despite hackathon pace (DL-11)
-----------------------------------------------------------------
`same_rate_source_as` is asserted only when **at least two independent signals agree**:

1. legal underwriter named on the quote or disclosure page
2. quote reference ID grammar
3. returned endorsement and form set, hashed
4. identical premium at identical inputs across two brands

`signals_agreeing` is recorded on every assertion. A single-signal match is a **hypothesis** and
renders dashed in the graph — it is never counted as a dedup.
"""

from __future__ import annotations

import csv
import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SEED = _REPO_ROOT / "data" / "seed" / "appendix_a.json"


@dataclass
class Fingerprint:
    underwriter_disclosed: str = ""
    quote_id_grammar: str = ""
    form_set_hash: str = ""
    premium_at_benchmark: float | None = None

    #: Documented extension to the four §9.3 signals (DL-15). A completed amalgamation filed with
    #: the regulator is stronger evidence that two brands share filed rates than a form-set hash
    #: is — the legal entity that files them has literally merged. Carries its source URL so the
    #: assertion is checkable, and counts as one signal, never two.
    regulatory_amalgamation: str = ""

    def signals(self) -> dict[str, object]:
        return {k: v for k, v in asdict(self).items() if v not in ("", None)}


@dataclass
class RegistryRecord:
    registry_id: str
    legal_underwriter: str
    insurer_group: str
    brand_or_program: str
    distribution_type: str          # direct|agent|broker|aggregator|affinity|MGA_program|mutual|residual
    product_scope: str = "standard_PPA"
    distinct_rate_source_id: str = ""
    quote_url: str = ""
    public_phone_route: str = ""
    licensed_intermediary: str = ""
    requirements: list[str] = field(default_factory=list)
    automation_notes: str = ""
    status: str = "unresolved"
    reason_code: str | None = None
    source_url: str = ""
    last_verified_at: str = ""
    evidence_artifact: str = ""

    #: §8.3 field. The Rate Filing Radar (§10.5) that would populate this from the regulator's
    #: published approved-change dataset was deferred (see docs/LIMITATIONS.md). Explicitly null
    #: on every row rather than omitted, so the schema is complete and the gap is checkable.
    rate_filing_delta: dict | None = None

    fingerprint: Fingerprint = field(default_factory=Fingerprint)
    signals_agreeing: int = 0
    dedup_hypothesis_with: str = ""

    #: Appendix A provenance. `requires_current_validation` marks a row that came from the
    #: regulator's public display dataset and has not been verified — §9.3 requires every row to
    #: carry its own validation, and the appendix's own header says it proves nothing on its own.
    appendix_group: str = ""
    appendix_legal_name: str = ""
    requires_current_validation: bool = False

    #: Sandbox sites live in the registry so the executor can be exercised against real records,
    #: but they are not the Ontario market. Excluded from every market metric; reliability
    #: numbers only (§11.5, §11.9).
    is_synthetic: bool = False

    def to_dict(self) -> dict:
        data = asdict(self)
        data["fingerprint"] = asdict(self.fingerprint)
        return data


def quote_id_grammar(reference: str) -> str:
    """Describe a reference's shape — the dedup signal, not the reference itself."""
    if not reference:
        return ""
    return re.sub(r"\d+", "N", re.sub(r"[A-Za-z]+", "A", reference))


class MarketRegistry:
    def __init__(self, seed_path: Path | str | None = None) -> None:
        self.seed_path = Path(seed_path) if seed_path else DEFAULT_SEED
        self.records: dict[str, RegistryRecord] = {}
        if self.seed_path.exists():
            self.load_seed()

    # -- loading ------------------------------------------------------------------------

    def load_seed(self) -> int:
        data = json.loads(self.seed_path.read_text(encoding="utf-8"))
        rows = data.get("records", data if isinstance(data, list) else [])
        for row in rows:
            fingerprint = Fingerprint(**row.pop("fingerprint", {}))
            record = RegistryRecord(**row, fingerprint=fingerprint)
            self.records[record.registry_id] = record
        return len(rows)

    def upsert(self, record: RegistryRecord) -> RegistryRecord:
        self.records[record.registry_id] = record
        return record

    def get(self, registry_id: str) -> RegistryRecord:
        return self.records[registry_id]

    def __len__(self) -> int:
        return len(self.records)

    # -- outcomes -----------------------------------------------------------------------

    def record_outcome(self, registry_id: str, *, status: str, reason_code: str | None,
                       evidence_cid: str = "", automation_notes: str = "",
                       quote_reference: str = "", premium: float | None = None) -> RegistryRecord:
        record = self.records[registry_id]
        record.status = status
        record.reason_code = reason_code
        record.last_verified_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
        if evidence_cid:
            record.evidence_artifact = evidence_cid
        if automation_notes:
            record.automation_notes = automation_notes
        if quote_reference:
            record.fingerprint.quote_id_grammar = quote_id_grammar(quote_reference)
        if premium is not None:
            record.fingerprint.premium_at_benchmark = premium
        return record

    # -- dedup --------------------------------------------------------------------------

    def agreeing_signals(self, a: RegistryRecord, b: RegistryRecord) -> list[str]:
        """Which of the four §9.3 signals agree between two records."""
        agreeing: list[str] = []
        fa, fb = a.fingerprint, b.fingerprint
        if fa.underwriter_disclosed and fa.underwriter_disclosed == fb.underwriter_disclosed:
            agreeing.append("underwriter_disclosed")
        if fa.quote_id_grammar and fa.quote_id_grammar == fb.quote_id_grammar:
            agreeing.append("quote_id_grammar")
        if fa.form_set_hash and fa.form_set_hash == fb.form_set_hash:
            agreeing.append("form_set_hash")
        if (fa.premium_at_benchmark is not None
                and fa.premium_at_benchmark == fb.premium_at_benchmark):
            agreeing.append("premium_at_benchmark")
        if fa.regulatory_amalgamation and fa.regulatory_amalgamation == fb.regulatory_amalgamation:
            agreeing.append("regulatory_amalgamation")
        return agreeing

    def resolve_rate_sources(self) -> dict[str, list[str]]:
        """Assign `distinct_rate_source_id`. Two agreeing signals to merge; one is a hypothesis."""
        ordered = sorted(self.records.values(), key=lambda r: r.registry_id)
        for record in ordered:
            record.distinct_rate_source_id = ""
            record.signals_agreeing = 0
            record.dedup_hypothesis_with = ""

        next_id = 1
        for index, record in enumerate(ordered):
            if not record.distinct_rate_source_id:
                record.distinct_rate_source_id = f"rs_{next_id:04d}"
                next_id += 1

            for other in ordered[index + 1:]:
                if other.distinct_rate_source_id:
                    continue
                agreeing = self.agreeing_signals(record, other)
                if len(agreeing) >= 2:
                    other.distinct_rate_source_id = record.distinct_rate_source_id
                    other.signals_agreeing = len(agreeing)
                    record.signals_agreeing = max(record.signals_agreeing, len(agreeing))
                elif len(agreeing) == 1:
                    # Recorded, never merged. §9.3: never assert on one signal.
                    other.dedup_hypothesis_with = record.registry_id

        groups: dict[str, list[str]] = {}
        for record in ordered:
            groups.setdefault(record.distinct_rate_source_id, []).append(record.registry_id)
        return groups

    # -- metrics ------------------------------------------------------------------------

    def metrics(self) -> dict:
        """§11.9's five metrics, exactly as specified, with denominators visible.

        Two granularities, by design — this mirrors the spec's own wording, not a simplification:

        - **Market completion** and **comparable quote yield** are computed over *distinct rate
          sources* ("verified applicable rate sources"), because that is literally what §11.9
          names as their denominator. A rate source counts as "applicable" once at least one of
          its member brands/entities has actually been attempted (excludes rate sources that are
          purely `reconnaissance_pending` appendix rows nobody has touched yet). It counts as
          meeting the numerator once at least one member achieved that outcome.
        - **Evidence rate**, **duplicate suppression** and **freshness** are computed over
          *records* (outcomes / brands / registry rows respectively), per §11.9's own wording for
          each.

        Unresolved stays in every denominator — it is never excluded or reclassified.
        """
        market = [r for r in self.records.values() if not r.is_synthetic]
        total = len(market)

        # "Never attempted" is two things, not one string. `reconnaissance_pending` is FATHOM's
        # own convention for a route it knows about but has not yet run. `requires_current_
        # validation` marks an Appendix A discovery-seed row that loads with status="unresolved"
        # by explicit operator instruction — its status field must read "unresolved" in every
        # export, but it was never attempted either, and counting 45 of those as "applicable"
        # would silently drag market completion, evidence rate and freshness down as if they
        # were failed attempts rather than untouched appendix rows. Both are excluded from the
        # "applicable" (attempted) set for METRICS purposes only; the exported status is untouched.
        never_attempted = lambda r: r.status == "reconnaissance_pending" or r.requires_current_validation
        pending = [r for r in market if never_attempted(r)]
        applicable = [r for r in market if not never_attempted(r)]
        evidenced = [r for r in applicable if r.evidence_artifact and r.last_verified_at]
        merged = sum(1 for r in market if r.signals_agreeing >= 2)

        # Rate-source-level denominator for market completion / comparable quote yield.
        applicable_rate_sources = {r.distinct_rate_source_id for r in applicable
                                   if r.distinct_rate_source_id}
        by_rate_source: dict[str, list] = {}
        for r in applicable:
            by_rate_source.setdefault(r.distinct_rate_source_id, []).append(r)

        rate_sources_with_evidenced_terminal = {
            rs for rs, members in by_rate_source.items()
            if any(m.status not in ("unresolved", "") and m.evidence_artifact and m.last_verified_at
                  for m in members)
        }
        rate_sources_with_comparable = {
            rs for rs, members in by_rate_source.items()
            if any(m.status == "quoted_comparable" for m in members)
        }

        all_rate_sources = {r.distinct_rate_source_id for r in market if r.distinct_rate_source_id}

        def ratio(num: int, den: int) -> str:
            return f"{num}/{den}" + (f" ({num / den:.0%})" if den else " (n/a)")

        return {
            "verified_applicable_rate_sources": len(applicable_rate_sources),
            "distinct_rate_sources_total": len(all_rate_sources),
            "records_total": total,
            "records_attempted": len(applicable),
            "records_never_attempted": len(pending),
            "records_never_attempted_reconnaissance_pending": sum(
                1 for r in pending if r.status == "reconnaissance_pending"),
            "records_never_attempted_appendix_unvalidated": sum(
                1 for r in pending if r.requires_current_validation),
            "market_completion": ratio(len(rate_sources_with_evidenced_terminal),
                                       len(applicable_rate_sources)),
            "comparable_quote_yield": ratio(len(rate_sources_with_comparable),
                                            len(applicable_rate_sources)),
            "evidence_rate": ratio(len(evidenced), len(applicable)),
            "duplicate_suppression": ratio(merged, total),
            "freshness": ratio(sum(1 for r in applicable if r.last_verified_at), len(applicable)),
            "synthetic_records_excluded": len(self.records) - len(market),
            "denominator_note": (
                "Market completion and comparable quote yield are computed over distinct rate "
                "sources that have been attempted ('verified applicable rate sources'), per §11.9. "
                "Evidence rate, duplicate suppression and freshness are computed over records. "
                "Records never attempted — either FATHOM's own reconnaissance_pending routes, or "
                "Appendix A discovery-seed rows carrying requires_current_validation=true (whose "
                "exported status field reads 'unresolved' by explicit instruction, not because an "
                "attempt was made) — are excluded from these denominators and reported separately, "
                "rather than counted as failed attempts. A route FATHOM did attempt and could not "
                "resolve keeps status 'unresolved' and stays in every denominator; that is a "
                "different thing from a row nobody has touched yet."
            ),
        }

    # -- export -------------------------------------------------------------------------

    def export_json(self, path: Path | str) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "metrics": self.metrics(),
            "records": [r.to_dict() for r in
                        sorted(self.records.values(), key=lambda r: r.registry_id)],
        }
        path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        return path

    #: §8.3's full field set (this build's operative registry schema — see docs/DECISIONS.md
    #: DL-16/DL-21 on why "Appendix B" from the hackathon brief could not be used verbatim: that
    #: document was never present in this session). Every column present on every row; genuinely
    #: unknown values are empty rather than omitted, so the schema's completeness is checkable.
    CSV_COLUMNS = [
        "registry_id", "legal_underwriter", "insurer_group", "brand_or_program",
        "distribution_type", "product_scope", "distinct_rate_source_id", "signals_agreeing",
        "dedup_hypothesis_with", "quote_url", "public_phone_route", "licensed_intermediary",
        "requirements", "automation_notes", "status", "reason_code", "source_url",
        "last_verified_at", "evidence_artifact", "rate_filing_delta",
        "underwriter_disclosed", "quote_id_grammar", "form_set_hash", "premium_at_benchmark",
        "regulatory_amalgamation", "appendix_group", "appendix_legal_name",
        "requires_current_validation", "is_synthetic",
    ]

    def export_csv(self, path: Path | str) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=self.CSV_COLUMNS, extrasaction="ignore")
            writer.writeheader()
            for record in sorted(self.records.values(), key=lambda r: r.registry_id):
                row = record.to_dict()
                row.update(row.pop("fingerprint"))  # flatten for CSV
                row["requirements"] = ";".join(row.get("requirements") or [])
                writer.writerow(row)
        return path
