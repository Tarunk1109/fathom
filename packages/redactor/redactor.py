"""Regex redactor — FATHOM §9.6, scoped by DL-04.

Runs entirely locally and reuses the PII sweep's rule set, so detection and redaction cannot drift
apart. Vision redaction is deliberately not built: screenshots are excluded from the submission
(OQ-004), so it has no consumer.

**Redact before write.** There is no raw-then-clean path — callers pass values here on the way into
the evidence store, not afterwards.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from tools.pii_sweep import RULES, redact_text  # noqa: E402


@dataclass
class RedactionReport:
    text: str
    rules_fired: list[str] = field(default_factory=list)

    @property
    def clean(self) -> bool:
        return not self.rules_fired


def redact(text: str, max_length: int | None = None) -> RedactionReport:
    """Scrub a string and report which categories were found."""
    # `rule.findings(...)` is a generator; `any(gen)` is truthy for the object itself, so the
    # matches have to be consumed. Reported every rule as fired before this was caught.
    fired = [rule.rule_id for rule in RULES
             if any(list(rule.findings(line)) for line in text.splitlines())]
    return RedactionReport(text=redact_text(text, max_length), rules_fired=fired)


def redact_mapping(data: dict) -> tuple[dict, list[str]]:
    """Redact every string value in a flat mapping. Keys are structure, values are the risk."""
    out, fired = {}, []
    for key, value in data.items():
        if isinstance(value, str):
            report = redact(value)
            out[key] = report.text
            fired.extend(report.rules_fired)
        else:
            out[key] = value
    return out, sorted(set(fired))
