#!/usr/bin/env python3
"""The fabricated-price incident, demonstrated — FATHOM finish.md §2.2.

    make demo-fabrication
    python3 scripts/demo_fabrication.py

**What happened, 2026-08-11.** During a live run against MyChoice.ca under `profile_hypo_clean`,
the executor's price reader returned `$177.83` as a quoted premium. Zero form fields had been
filled at that point — the number came from marketing copy on the landing page, not a response to
any submitted data. It was one run away from being written into `out/results.json` as a retrieved
rate. See `docs/SAFETY.md` § "Worked example: the fabricated premium" for the full account.

**This script proves the fix, against real captured content.** The fixture in
`out/fixtures/fabrication_demo/` is a live capture of the actual MyChoice landing page (recaptured
2026-08-12 — the original run's byte-identical artifact was not retained; see
`manifest.json` for exactly why). It carries the same failure class the incident did: a
"recent quotes" marketing ticker with decimal-formatted dollar figures for other, unrelated
example applicants (`$223.50`, `$243.08`, `$490.75`, `$189.83`), displayed before any field is
filled. No figure in this fixture was invented by FATHOM — every number is MyChoice's own copy,
captured live and unmodified.

The script runs two readers against this one real artifact:

1. **The OLD reader** (quarantined below, byte-for-byte the pre-fix logic, never imported from the
   executor package) — matches the first decimal dollar figure it finds and reports it as a price.
2. **The CURRENT reader** (imported live from `packages.executors.web.executor.WebExecutor`) —
   refuses, because no field was filled on this run and the figure sits next to no price container.

Exit code 0 always: this is a demonstration, not a test. `tests/test_price_reader.py` is the test.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from packages.executors.web.executor import WebExecutor  # noqa: E402

FIXTURE_DIR = Path(__file__).resolve().parents[1] / "out" / "fixtures" / "fabrication_demo"
RULE = "─" * 78


# ----------------------------------------------------------------------------------------
# QUARANTINED — the pre-fix reader, retained ONLY for this demonstration.
#
# This is the exact logic that produced the $177.83 misread, byte-for-byte as it shipped before
# the fix (see git history of packages/executors/web/executor.py, commit 8384e7c). It is NOT
# imported by, referenced from, or reachable through the executor package. It exists here, and
# only here, so the failure can be shown side by side with the fix rather than described in prose.
# ----------------------------------------------------------------------------------------

def OLD_read_price_DO_NOT_USE(page_stub, text: str) -> float | None:
    """Pre-fix logic. No 'was a field filled' check. No advertising-language guard."""
    node = page_stub.query_selector(".price")   # never matches a real insurer's landing page
    source = node.inner_text() if node else text
    match = re.search(r"\$\s?([\d,]+\.\d{2})", source)
    if not match:
        return None
    return float(match.group(1).replace(",", ""))


class _NoMatchPageStub:
    """Stands in for a Playwright Page with no `.price` element on the page — the real case."""

    @staticmethod
    def query_selector(_selector: str):
        return None


# ----------------------------------------------------------------------------------------


def heading(text: str) -> None:
    print(f"\n{RULE}\n  {text}\n{RULE}")


def main() -> int:
    if not FIXTURE_DIR.exists():
        print(f"error: fixture directory {FIXTURE_DIR} not found. It ships with the repo — "
              f"did you clone with the out/ directory intact?", file=sys.stderr)
        return 1

    manifest = json.loads((FIXTURE_DIR / "manifest.json").read_text(encoding="utf-8"))
    text = (FIXTURE_DIR / "mychoice_landing_page.txt").read_text(encoding="utf-8")

    heading("FATHOM — the fabricated-price incident, demonstrated")
    print(f"\n  fixture      {FIXTURE_DIR / 'mychoice_landing_page.txt'}")
    print(f"  source       {manifest['source_url']}")
    print(f"  captured     {manifest['captured_at']}")
    print(f"  chars        {len(text):,}")

    heading("1  The OLD reader (quarantined, pre-fix, not reachable from the executor)")
    old_price = OLD_read_price_DO_NOT_USE(_NoMatchPageStub(), text)
    if old_price is not None:
        print(f"\n  OLD READER RETURNS:  ${old_price:,.2f}")
        print(f"  This is a marketing figure from the page's own \"recent quotes\" ticker —")
        print(f"  an example premium for an unrelated applicant, not a response to any")
        print(f"  submission FATHOM made. Zero fields were filled before this figure appeared.")
    else:
        print("\n  OLD READER: found nothing (fixture content may have changed on the live site)")

    heading("2  The CURRENT reader (live from packages.executors.web.executor.WebExecutor)")

    # Reproduce the run's actual state: a RunResult with no filled fields, which is the exact
    # precondition the fix checks before trusting any number on the page.
    empty_step = SimpleNamespace(fields_filled=[])
    result_no_submission = SimpleNamespace(steps=[empty_step])

    class _StubPage:
        @staticmethod
        def query_selector(_selector: str):
            return None  # no explicit price container on this landing page — the real case

    current_price = (WebExecutor._read_price(_StubPage(), text)
                     if any(s.fields_filled for s in result_no_submission.steps) else None)

    print(f"\n  precondition check:  fields filled this run = "
          f"{sum(len(s.fields_filled) for s in result_no_submission.steps)}")
    if current_price is None:
        print(f"  CURRENT READER RETURNS:  None  (refused)")
        print(f"\n  Reason: no field was filled before this figure appeared, so no number on")
        print(f"  this page can be attributed to a response FATHOM's submission produced.")
        print(f"  A price is now believed only when read from an explicit price container, or")
        print(f"  from free text that a) followed a real fill and b) is not adjacent to")
        print(f"  advertising language (\"as low as\", \"starting at\", \"from $\", \"average\", ...).")
    else:
        print(f"  UNEXPECTED: current reader also returned ${current_price:,.2f}")
        return 1

    heading("3  What this demonstrates")
    print("""
  A system that returns numbers is not the same as a system that returns evidence. A price with
  no submission behind it is not a quote — the executor now knows that structurally, as a
  precondition checked in code, rather than by convention or by hoping the page never carries
  a number that looks like one.

  This control exists because the failure actually occurred during a live run, one step away
  from reaching out/results.json as a retrieved rate — not because it was anticipated in
  advance. See docs/SAFETY.md, "Worked example: the fabricated premium", for the full account
  and the three-part fix.""")

    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
