# The residual market, and what FATHOM extracted from it

## What the residual market is

Ontario's private auto insurers are not required to accept every applicant. Facility Association
is the industry-run mechanism that fills that gap: it is the insurer of last resort for drivers
who cannot get, or cannot afford, coverage in the regular ("voluntary") market — a bad driving
record, a lapse in coverage, a high-risk vehicle, or simply a driver history too thin for a
voluntary insurer's underwriting rules. By design and by regulation, Facility Association **must
accept any eligible applicant** who applies through a licensed broker; it cannot decline on the
basis of risk the way a voluntary-market insurer can. That "must accept" property is exactly why
it exists, and it is why its Manual of Rules and Rates is a public, published document rather than
proprietary underwriting criteria — the rates have to be knowable in advance by anyone who might
be placed there.

FATHOM does not place applicants and does not quote. This document exists only because the manual
itself is a legitimate, citable public source, and reading it accurately is different from
computing a premium from it.

## What was extracted

One table type: the **territory definitions table** — a lookup from Ontario location (city, town,
or municipality) to a numeric territory code and a statistical code, spanning pages 1398-1605 of
the manual. This table was chosen, and every other candidate was rejected, because it was the only
section that produced clean, unambiguous, machine-parseable rows without any interpretive step.
See `scripts/extract_residual_manual.py`'s module docstring for the full list of what was tried
and why each alternative was left out (vehicle rate-group tables spanning hundreds of pages with
no stable column structure; annual premium tables whose cells pack multiple stacked figures with
no unambiguous mapping to a rate group; driver class rules and endorsement charges, which are
prose, not tables).

Every extracted row carries three things: the value, the source page number, and the table name it
came from (`out/residual_manual_extract.json` → `extracted.rows[]`). Rows where the territory or
statistical code was a cross-reference rather than a plain value (e.g. "See Toronto territories")
were dropped rather than guessed — they are listed under `dropped_rows_detail` in the same file,
with the reason.

## What this is not

- **Not a quote.** No premium, no dollar figure, no computed price appears anywhere in this
  extract or in the UI panel that displays it.
- **Not an estimate.** A territory code is a lookup key, not a rate.
- **Not a substitute for a licensed intermediary.** Real placement in the residual market requires
  a licensed insurance broker who can determine actual eligibility, apply the full current rule
  set, and bind coverage. FATHOM cannot and does not do any of that.

Every place this data surfaces — the JSON file, this document, and the UI panel — is labelled
**UNVERIFIED EXTRACTION**.

## Source

- Publisher: Facility Association
- Document: Manual of Rules and Rates, Ontario, effective November 1, 2025
- URL: https://www.facilityassociation.com/docs/ON_Manual_Effective_November_1_2025.pdf
- Retrieval and file hash: recorded per-run in `out/residual_manual_extract.json` → `source`
