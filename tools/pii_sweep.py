#!/usr/bin/env python3
"""FATHOM PII sweep.

Enforces the hard constraint in FATHOM Prime Directives §2.1:

    Never let a real licence number, full address, payment data or raw call audio reach
    the repo, logs, prompts, traces, screenshots or the submission.

Scans every text file in the repository — including `out/` and `docs/` — for PII-shaped
content and exits non-zero on a hit. Runs identically in CI and locally:

    make sweep                  # or:  python3 tools/pii_sweep.py

Stdlib only, by design. §13 stack decisions are made at the milestone that uses them, and
this check must run before any dependency exists.

Two properties matter as much as the detection itself:

1. **The sweep never prints what it found.** A finding is reported as file, line, rule and a
   masked excerpt. Printing the match would put PII into CI logs, which is the exact failure
   the sweep exists to prevent.
2. **Binary files are reported, not silently skipped.** A screenshot cannot be grepped, so it
   is listed for manual review rather than passed over. §15.1 requires the final sweep to
   cover screenshots too, and the tool should not imply a coverage it does not have.

False positives are expected and are handled with an inline pragma, never by weakening a rule:

    some_line_that_trips_a_rule    # pii-sweep: allow PC_FULL_POSTAL  (reason)
    a_line_that_trips_two_rules    # pii-sweep: allow PC_FULL_POSTAL,EMAIL  (reason)
    some_line_that_trips_anything  # pii-sweep: allow

Exit codes:  0 clean · 1 findings · 2 usage error
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterator

# --------------------------------------------------------------------------------------
# Scan surface
# --------------------------------------------------------------------------------------

EXCLUDED_DIRS = {
    ".git", ".hg", ".svn",
    "node_modules", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache",
    ".venv", "venv", "env",
    "dist", "build", ".next", ".turbo",
    ".claude",
}

# Extensions that cannot be swept as text. Reported for manual review, never silently dropped.
BINARY_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".tiff", ".ico", ".pdf",
    ".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg",
    ".mp4", ".mov", ".avi", ".mkv", ".webm",
    ".zip", ".gz", ".tar", ".bz2", ".xz", ".7z",
    ".sqlite", ".db", ".pyc", ".so", ".dylib", ".woff", ".woff2", ".ttf", ".otf",
}

MAX_FILE_BYTES = 8 * 1024 * 1024

ALLOW_PRAGMA = re.compile(r"pii-sweep:\s*allow(?:\s+([A-Z_]+(?:\s*,\s*[A-Z_]+)*))?")

# --------------------------------------------------------------------------------------
# Rules
# --------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Rule:
    rule_id: str
    description: str
    pattern: re.Pattern[str]
    directive: str
    validator: Callable[[str], bool] | None = None

    def findings(self, line: str) -> Iterator[re.Match[str]]:
        for match in self.pattern.finditer(line):
            if self.validator is None or self.validator(match.group(0)):
                yield match


def _luhn_ok(candidate: str) -> bool:
    """Payment-card check digit. Without it, any long digit run trips the rule."""
    digits = [int(c) for c in candidate if c.isdigit()]
    if not 13 <= len(digits) <= 19:
        return False
    checksum, parity = 0, len(digits) % 2
    for index, digit in enumerate(digits):
        if index % 2 == parity:
            digit *= 2
            if digit > 9:
                digit -= 9
        checksum += digit
    return checksum % 10 == 0


def _vin_plausible(candidate: str) -> bool:
    """A VIN is 17 chars, excludes I/O/Q, and mixes letters and digits.

    Content-addressed hashes and base32 blobs are the main false-positive source, so require
    a genuine mix rather than accepting any 17-character token.
    """
    letters = sum(c.isalpha() for c in candidate)
    digits = sum(c.isdigit() for c in candidate)
    return letters >= 2 and digits >= 2


def _phone_plausible(candidate: str) -> bool:
    """Reject digit runs that are really versions, ranges or ISO fragments."""
    digits = "".join(c for c in candidate if c.isdigit())
    core = digits[-10:]
    if len(core) != 10:
        return False
    if len(set(core)) <= 2:          # 0000000000, 1231231231
        return False
    if core[0] in "01" or core[3] in "01":   # invalid NANP area / exchange code
        return False
    return True


RULES: tuple[Rule, ...] = (
    Rule(
        rule_id="DL_ONTARIO",
        description="Ontario driver's licence number (1 letter + 14 digits)",
        pattern=re.compile(r"\b[A-Za-z]\d{4}[-\s]?\d{5}[-\s]?\d{5}\b"),
        directive="§2.1 never store a licence number; §9.1 P-LICENCE-01",
    ),
    Rule(
        rule_id="PC_FULL_POSTAL",
        description="Full Canadian postal code (FSA-only, e.g. M5V, is permitted)",
        pattern=re.compile(r"\b[ABCEGHJ-NPRSTVXY]\d[ABCEGHJ-NPRSTV-Z][-\s]?\d[ABCEGHJ-NPRSTV-Z]\d\b"),
        directive="§2.1 no full address; §9.6 redactor category",
    ),
    Rule(
        rule_id="VIN",
        description="Vehicle identification number (17 chars, no I/O/Q)",
        pattern=re.compile(r"\b[A-HJ-NPR-Z0-9]{17}\b"),
        directive="§9.6 redactor category",
        validator=_vin_plausible,
    ),
    Rule(
        rule_id="PHONE_NANP",
        description="North American phone number",
        pattern=re.compile(
            r"(?<!\d)(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}(?!\d)"
        ),
        directive="§9.6 redactor category",
        validator=_phone_plausible,
    ),
    Rule(
        rule_id="EMAIL",
        description="Email address",
        pattern=re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
        directive="§9.6 redactor category",
    ),
    Rule(
        rule_id="PAYMENT_CARD",
        description="Payment card number (Luhn-valid)",
        pattern=re.compile(r"(?<!\d)(?:\d[ -]?){13,19}(?!\d)"),
        directive="§2.1 no payment data; §9.1 P-PAY-01",
        validator=_luhn_ok,
    ),
    Rule(
        rule_id="STREET_ADDRESS",
        description="Street address (number + name + street type)",
        pattern=re.compile(
            r"\b\d{1,6}\s+[A-Z][A-Za-z.'-]*(?:\s+[A-Z][A-Za-z.'-]*){0,3}\s+"
            r"(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Drive|Dr|Crescent|Cres|Court|Ct|"
            r"Way|Lane|Ln|Place|Pl|Terrace|Terr|Trail|Trl|Parkway|Pkwy|Circle|Cir|Square|Sq)\b\.?",
        ),
        directive="§2.1 no full address",
    ),
    Rule(
        rule_id="DOB_LABELLED",
        description="A date adjacent to a date-of-birth label (birth year alone is permitted)",
        pattern=re.compile(
            r"(?i)\b(?:d\.?o\.?b\.?|date[\s_-]?of[\s_-]?birth|birth[\s_-]?date|birthdate)\b"
            r"[^\n]{0,24}?\b\d{1,4}[-/]\d{1,2}[-/]\d{1,4}\b"
        ),
        directive="§9.6 redactor category — record birth year only",
    ),
)

RULES_BY_ID = {rule.rule_id: rule for rule in RULES}


# --------------------------------------------------------------------------------------
# Findings
# --------------------------------------------------------------------------------------


@dataclass
class Finding:
    path: str
    line_number: int
    rule_id: str
    description: str
    directive: str
    masked: str

    def as_text(self) -> str:
        return (
            f"{self.path}:{self.line_number}: [{self.rule_id}] {self.description}\n"
            f"    matched: {self.masked}   ({self.directive})"
        )


def mask(value: str) -> str:
    """Report enough shape to locate the hit, never enough to reconstruct the value."""
    visible = value[:2]
    return f"{visible}{'*' * max(len(value) - 2, 1)} ({len(value)} chars)"


@dataclass
class SweepReport:
    findings: list[Finding] = field(default_factory=list)
    files_scanned: int = 0
    binaries_for_review: list[str] = field(default_factory=list)
    skipped_too_large: list[str] = field(default_factory=list)

    @property
    def clean(self) -> bool:
        return not self.findings


# --------------------------------------------------------------------------------------
# Scanning
# --------------------------------------------------------------------------------------


def iter_files(root: Path) -> Iterator[Path]:
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in EXCLUDED_DIRS)
        for filename in sorted(filenames):
            yield Path(dirpath) / filename


def allowed_rules_on_line(line: str) -> set[str] | None:
    """Return allowed rule ids for this line, or None when nothing is allowed.

    An empty set means a bare pragma: every rule is allowed on that line. A line can
    legitimately trip more than one rule, so the pragma accepts a comma-separated list —
    narrowing an allowance is always preferable to weakening a rule.
    """
    match = ALLOW_PRAGMA.search(line)
    if not match:
        return None
    rule_ids = match.group(1)
    if not rule_ids:
        return set()
    return {rule_id.strip() for rule_id in rule_ids.split(",") if rule_id.strip()}


def scan_line(path_label: str, line_number: int, line: str) -> Iterator[Finding]:
    allowed = allowed_rules_on_line(line)
    for rule in RULES:
        if allowed is not None and (not allowed or rule.rule_id in allowed):
            continue
        for match in rule.findings(line):
            yield Finding(
                path=path_label,
                line_number=line_number,
                rule_id=rule.rule_id,
                description=rule.description,
                directive=rule.directive,
                masked=mask(match.group(0)),
            )


def scan_file(path: Path, root: Path, report: SweepReport) -> None:
    label = str(path.relative_to(root))

    if path.suffix.lower() in BINARY_EXTENSIONS:
        report.binaries_for_review.append(label)
        return

    try:
        if path.stat().st_size > MAX_FILE_BYTES:
            report.skipped_too_large.append(label)
            return
        text = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, ValueError):
        report.binaries_for_review.append(label)
        return
    except OSError as exc:
        print(f"warning: cannot read {label}: {exc}", file=sys.stderr)
        return

    report.files_scanned += 1
    for line_number, line in enumerate(text.splitlines(), start=1):
        report.findings.extend(scan_line(label, line_number, line))


def sweep(root: Path) -> SweepReport:
    report = SweepReport()
    for path in iter_files(root):
        scan_file(path, root, report)
    return report


# --------------------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------------------


def render(report: SweepReport, root: Path) -> str:
    lines: list[str] = []
    lines.append(f"FATHOM PII sweep — {report.files_scanned} text files scanned under {root}")
    lines.append("")

    if report.findings:
        lines.append(f"FAIL — {len(report.findings)} finding(s). Prime Directives §2.1.")
        lines.append("")
        for finding in report.findings:
            lines.append(finding.as_text())
        lines.append("")
        lines.append(
            "Remove the value, or annotate the line with `# pii-sweep: allow <RULE_ID>` and a "
            "reason if it is genuinely not PII."
        )
    else:
        lines.append("PASS — no PII-shaped content found in text files.")

    if report.binaries_for_review:
        lines.append("")
        lines.append(
            f"Manual review required — {len(report.binaries_for_review)} binary file(s) cannot "
            "be swept as text (§15.1 covers screenshots and recordings):"
        )
        lines.extend(f"    {path}" for path in report.binaries_for_review)

    if report.skipped_too_large:
        lines.append("")
        lines.append(f"Skipped, over {MAX_FILE_BYTES // (1024 * 1024)}MB:")
        lines.extend(f"    {path}" for path in report.skipped_too_large)

    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="pii_sweep",
        description="Fail the build if PII-shaped content is present anywhere in the repo.",
    )
    parser.add_argument(
        "root", nargs="?", default=None,
        help="directory to sweep (default: the repository root containing this script)",
    )
    parser.add_argument("--json", action="store_true", help="emit machine-readable findings")
    parser.add_argument("--list-rules", action="store_true", help="print the rule set and exit")
    args = parser.parse_args(argv)

    if args.list_rules:
        for rule in RULES:
            print(f"{rule.rule_id:16} {rule.description}\n{'':16} {rule.directive}")
        return 0

    root = Path(args.root).resolve() if args.root else Path(__file__).resolve().parent.parent
    if not root.is_dir():
        print(f"error: {root} is not a directory", file=sys.stderr)
        return 2

    report = sweep(root)

    if args.json:
        print(json.dumps({
            "clean": report.clean,
            "files_scanned": report.files_scanned,
            "findings": [
                {
                    "path": f.path, "line": f.line_number, "rule_id": f.rule_id,
                    "description": f.description, "directive": f.directive, "masked": f.masked,
                }
                for f in report.findings
            ],
            "binaries_for_review": report.binaries_for_review,
            "skipped_too_large": report.skipped_too_large,
        }, indent=2))
    else:
        print(render(report, root))

    return 0 if report.clean else 1


if __name__ == "__main__":
    raise SystemExit(main())
