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
    fingerprint: Fingerprint = field(default_factory=Fingerprint)
    signals_agreeing: int = 0
    dedup_hypothesis_with: str = ""

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
        """§11.9, with denominators visible. Unresolved stays in every denominator."""
        market = [r for r in self.records.values() if not r.is_synthetic]
        total = len(market)
        pending = [r for r in market if r.status == "reconnaissance_pending"]
        applicable = [r for r in market if r.status != "reconnaissance_pending"]
        evidenced = [r for r in applicable if r.evidence_artifact and r.last_verified_at]
        comparable = [r for r in applicable if r.status == "quoted_comparable"]
        terminal = [r for r in applicable if r.status not in ("unresolved", "")]
        groups = {r.distinct_rate_source_id for r in market if r.distinct_rate_source_id}
        merged = sum(1 for r in market if r.signals_agreeing >= 2)

        def ratio(num: int, den: int) -> str:
            return f"{num}/{den}" + (f" ({num / den:.0%})" if den else " (n/a)")

        return {
            "verified_applicable_rate_sources": len(groups),
            "records_total": total,
            "records_attempted": len(applicable),
            "records_reconnaissance_pending": len(pending),
            "market_completion": ratio(len(terminal), len(applicable)),
            "comparable_quote_yield": ratio(len(comparable), len(applicable)),
            "evidence_rate": ratio(len(evidenced), len(applicable)),
            "duplicate_suppression": ratio(merged, total),
            "freshness": ratio(sum(1 for r in applicable if r.last_verified_at), len(applicable)),
            "synthetic_records_excluded": len(self.records) - len(market),
            "denominator_note": (
                "reconnaissance_pending routes were never attempted and are reported separately "
                "rather than counted as failures. Unresolved routes stay in every denominator."
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

    def export_csv(self, path: Path | str) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        columns = ["registry_id", "legal_underwriter", "insurer_group", "brand_or_program",
                   "distribution_type", "product_scope", "distinct_rate_source_id",
                   "signals_agreeing", "dedup_hypothesis_with", "status", "reason_code",
                   "quote_url", "source_url", "last_verified_at", "evidence_artifact",
                   "automation_notes"]
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
            writer.writeheader()
            for record in sorted(self.records.values(), key=lambda r: r.registry_id):
                writer.writerow(record.to_dict())
        return path
