"""Normalizer, assessment and parity — FATHOM §8.4, §9.7.

Turns a `RunResult` into the common quote-result schema, assigns a PASS / CAUTION / FAIL verdict
with reason codes and an evidence status, and states the coverage variance against the §8.5
benchmark in plain language.

The rule that matters: **coverage differences render above price differences, and the lowest
number is never labelled "best"** (§12.3, §9.7). A cheaper quote carrying a lower liability limit
and a missing endorsement is not a cheaper quote; it is a different product. Where the delta cannot
be measured, parity is reported as `not_possible` rather than estimated — §18 forbids filling a
parity gap with an invented number.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field

#: §8.5 benchmark coverage. Every route requests this package.
BENCHMARK = {
    "third_party_liability_limit": 2000000,
    "collision_deductible": 1000,
    "comprehensive_deductible": 1000,
    "dcpd": "included",
    "opcf_44r_family_protection": "included",
    "term_months": 12,
}

#: Plain-language names for the variance list a judge reads.
FRIENDLY = {
    "third_party_liability_limit": "third-party liability limit",
    "collision_deductible": "collision deductible",
    "comprehensive_deductible": "comprehensive deductible",
    "dcpd": "direct compensation property damage",
    "opcf_44r_family_protection": "OPCF 44R family protection",
    "income_replacement": "income replacement benefit",
    "term_months": "policy term (months)",
}


@dataclass
class Assessment:
    verdict: str
    reason_codes: list[str] = field(default_factory=list)
    confidence_indicator: str = "medium"
    evidence_status: str = "absent"


@dataclass
class NormalizedResult:
    result_id: str
    profile_id: str
    registry_id: str
    distinct_rate_source_id: str
    route_id: str
    status: str
    reason_code: str | None
    channel: str
    assessment: Assessment
    price: dict
    coverage: dict
    variance_from_benchmark: list[str]
    parity: dict
    validity: dict
    evidence: dict
    decline: dict

    def to_dict(self) -> dict:
        data = asdict(self)
        return data


def compare_to_benchmark(coverage: dict) -> tuple[list[str], list[str]]:
    """Return (plain-language variances, machine reason codes)."""
    variances: list[str] = []
    codes: list[str] = []

    for key, expected in BENCHMARK.items():
        actual = coverage.get(key)
        name = FRIENDLY.get(key, key)
        if actual is None:
            variances.append(f"{name}: not stated by this route")
            codes.append("coverage_item_unknown")
            continue
        if actual == expected:
            continue
        if isinstance(expected, int) and isinstance(actual, int):
            direction = "lower" if actual < expected else "higher"
            variances.append(f"{name}: {actual:,} vs benchmark {expected:,} ({direction})")
        else:
            variances.append(f"{name}: {actual} vs benchmark {expected}")
        codes.append("coverage_variance_unpriced")

    for key, actual in coverage.items():
        if key in BENCHMARK or key == "income_replacement":
            continue
        variances.append(f"{FRIENDLY.get(key, key)}: {actual} (not in benchmark)")

    income = coverage.get("income_replacement")
    if income is not None and income != "excluded":
        variances.append(
            f"{FRIENDLY['income_replacement']}: {income} — an optional benefit since 1 July 2026, "
            f"included here and not in the benchmark")
        codes.append("optional_benefit_included_unpriced")

    return variances, codes


def assess(status: str, variances: list[str], codes: list[str],
           evidence_cids: list[str], premium: float | None) -> Assessment:
    """§8.4 assessment rules."""
    evidence_status = "verified" if evidence_cids else "absent"

    if premium is None:
        return Assessment("FAIL", codes or ["no_premium_returned"], "high", evidence_status)
    if not evidence_cids:
        return Assessment("FAIL", codes + ["evidence_absent"], "low", "absent")
    if variances:
        return Assessment("CAUTION", codes, "medium", evidence_status)
    return Assessment("PASS", [], "high", evidence_status)


def normalize(run, *, result_id: str, registry_id: str, rate_source_id: str,
              channel: str = "web") -> NormalizedResult:
    """Map an executor `RunResult` into the §8.4 schema."""
    variances, codes = ([], []) if run.premium is None else compare_to_benchmark(run.coverage)

    parity_possible = run.premium is not None and not variances
    parity = {
        "price_at_benchmark": run.premium if parity_possible else None,
        "adjustments_applied": [],
        # §18: never fill a parity gap with an invented number. The Benefit Price Probe that
        # would measure these deltas is deferred, so the honest value is not_possible.
        "parity_confidence": "measured" if parity_possible else "not_possible",
        "parity_note": ("Coverage matches the benchmark, so the quoted price is the benchmark "
                        "price." if parity_possible else
                        "This route's coverage differs from the benchmark and the per-item deltas "
                        "have not been measured, so no benchmark-equivalent price is stated."),
    }

    return NormalizedResult(
        result_id=result_id,
        profile_id=run.profile_id,
        registry_id=registry_id,
        distinct_rate_source_id=rate_source_id,
        route_id=run.route_id,
        status=run.status,
        reason_code=run.reason_code,
        channel=channel,
        assessment=assess(run.status, variances, codes, run.evidence_cids, run.premium),
        price={
            "annual_premium": run.premium,
            "currency": "CAD",
            "total_estimated_cost": run.premium,
        },
        coverage=dict(run.coverage),
        variance_from_benchmark=variances,
        parity=parity,
        validity={"quote_reference_id": run.quote_reference,
                  "verification_may_change_premium": True},
        evidence={
            "timestamp": None,
            "source_url_or_phone_route": run.entry_url,
            "artifact_cids": list(run.evidence_cids),
            "artifact_count": len(run.evidence_cids),
        },
        decline={
            "stated_reason_redacted": run.stated_reason,
            "reason_code": run.reason_code,
            "stopping_step": run.stopping_step,
            "policy_rules_fired": sorted({rule for rule, _ in run.policy_denials}),
        } if run.premium is None else {},
    )


def rank(results: list[NormalizedResult]) -> list[NormalizedResult]:
    """Order priced results by price — but never label the cheapest 'best'.

    Sorting by price is what a user wants; calling the top row the best answer is what §9.7
    forbids, because the row above may be cheaper only by carrying less coverage.
    """
    priced = [r for r in results if r.price.get("annual_premium") is not None]
    unpriced = [r for r in results if r.price.get("annual_premium") is None]
    priced.sort(key=lambda r: r.price["annual_premium"])
    return priced + unpriced


def comparability_note(results: list[NormalizedResult]) -> str:
    """One sentence a judge can read that says whether the prices are comparable at all."""
    priced = [r for r in results if r.price.get("annual_premium") is not None]
    if len(priced) < 2:
        return "Fewer than two priced results; no price comparison is possible."
    at_benchmark = [r for r in priced if not r.variance_from_benchmark]
    if len(at_benchmark) == len(priced):
        return "All priced results match the benchmark package, so the prices are directly comparable."
    cheapest = min(priced, key=lambda r: r.price["annual_premium"])
    if cheapest.variance_from_benchmark:
        return (f"The lowest price ({cheapest.route_id}) does not match the benchmark package — it "
                f"differs in {len(cheapest.variance_from_benchmark)} respect(s). It is a different "
                f"product, not a cheaper one, and the difference has not been priced.")
    return "Priced results differ in coverage; compare the variance lists before the prices."
