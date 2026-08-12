# Archived: corrupted audit log, 2026-08-12

`policy_audit_corrupted_2026-08-12.jsonl` is the policy audit log as it stood when
`scripts/verify_chain.py` reported:

    chain BROKEN at index 119 after 119 intact entries: index is 118, expected 119

**Root cause, confirmed by direct inspection of the raw file:** two separate `run_route.py`
invocations were launched as background processes close together in wall-clock time
(2026-08-12T14:42:18Z and 14:42:21Z, one running the Desjardins D-URLS retry, the other
recapturing MyChoice evidence). Each opened its own `AuditLog`, both read the same 118 existing
entries at construction, and both independently computed `index=118` for their next append —
a genuine race condition in `packages/policy/audit.py`, not tampering, not a fabricated entry,
and not a security incident. Every individual entry's hash is internally valid; the entries at
index 118 and its duplicate are both real, honestly-recorded decisions. The chain is broken only
in the sense that two entries claim the same sequence position.

**This is not the same class of event as the fabricated-price incident** (`docs/SAFETY.md`).
That was a wrong *value*. This is a wrong *sequence number*, produced by a concurrency bug in
this session's own process management (running overlapping background jobs), not by anything an
adversary or a misread page could produce.

**Fix:** `AuditLog.append()` and `EvidenceStore.append()` (same bug, same fix) now hold an
exclusive OS file lock across the entire read-current-state-then-write sequence, and re-read the
file fresh under that lock. Verified against a real 6-process, 240-write concurrent stress test
in `tests/test_audit_concurrency.py`. See `docs/SAFETY.md` § "Controls that failed open, and
were caught" and `docs/DECISIONS.md` DL-23.

The corrupted log is kept here, unmodified, rather than deleted — the same principle as every
other evidence artifact in this project: nothing is quietly dropped. It was never distributed as
a deliverable; `out/audit/policy_audit.jsonl` was rebuilt from a clean state using the fixed code
before this project's audit chain was used in any exported deliverable or demo.
