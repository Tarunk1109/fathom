# Registry seed

`appendix_a.json` is the regulatory seed from the brief's Appendix A (32 groups, 60 legal entities).

**It currently contains only rows FATHOM has evidenced itself** — the four Day 0 direct writers,
the three excluded-but-carried brands, and the sandbox sites used for reliability numbers.

**Appendix A itself has not been supplied to the build.** It is a discovery seed, and §6.1 is
explicit that a single invented number ends the submission — so no insurer, group or corporate
relationship is written here that has not been evidenced. When the appendix is available, append
its rows to `records` and re-run `scripts/build_registry.py`; every row still requires its own
`last_verified_at` and evidence before it counts toward any metric (§9.3).

Rows carrying `"status": "reconnaissance_pending"` have never been attempted. They are reported
separately from failures and are excluded from the attempted-route denominators, by design.
