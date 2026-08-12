"""Regression test for a real chain-break incident found during finish.md's final integrity pass.

2026-08-12: `make verify` reported "chain BROKEN at index 119 ... index is 118, expected 119".
Root cause: two separate `run_route.py` invocations, launched as background processes close
together in wall-clock time, both computed `index = len(self._entries)` from an in-memory
snapshot taken once at construction and both appended an entry claiming index 118 — a genuine
race, not tampering. The evidence store (`packages.evidence.store.EvidenceStore`) had the
identical bug pattern and was fixed the same way.

Fix: `AuditLog.append()` and `EvidenceStore.append()` now hold an OS-level exclusive file lock
(`fcntl.flock`) across the entire read-current-state-then-write sequence, re-reading the file
fresh under the lock rather than trusting a stale in-memory count.

This test proves it holds under real concurrent multi-process writers, not just a mocked
scenario — the original bug only appeared under genuine process concurrency, so a single-process
test would not have caught it and would not catch a regression.
"""

from __future__ import annotations

import multiprocessing
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def _audit_worker(path: str, n: int) -> None:
    from packages.policy.audit import AuditLog
    log = AuditLog(path)
    for _ in range(n):
        log.append(session_id="s", route_id="r", profile_id="p", action_kind="fill",
                   target="https://x.example.com", payload={"a": "1"}, rationale="race test",
                   verdict="ALLOW", rule_id="P-ALLOW-00", explanation="x")


def _evidence_worker(directory: str, n: int) -> None:
    from packages.evidence import EvidenceStore
    store = EvidenceStore(directory)
    for i in range(n):
        store.append(content=f"artifact {i}", route_id="r", profile_id="p",
                     kind="page_text", source="https://x.example.com")


class TestAuditLogConcurrency(unittest.TestCase):
    PROCESSES = 6
    WRITES_EACH = 40

    def test_concurrent_processes_do_not_corrupt_the_chain(self):
        from packages.policy.audit import AuditLog

        with tempfile.TemporaryDirectory() as tmp:
            path = f"{tmp}/audit.jsonl"
            procs = [multiprocessing.Process(target=_audit_worker, args=(path, self.WRITES_EACH))
                    for _ in range(self.PROCESSES)]
            for p in procs:
                p.start()
            for p in procs:
                p.join(timeout=30)
                self.assertEqual(p.exitcode, 0, "worker process failed or hung")

            log = AuditLog(path)
            expected = self.PROCESSES * self.WRITES_EACH
            self.assertEqual(len(log), expected, "writes were lost under concurrency")
            result = log.verify_chain()
            self.assertTrue(result.ok, f"chain broken under concurrency: {result.describe()}")


class TestEvidenceStoreConcurrency(unittest.TestCase):
    PROCESSES = 4
    WRITES_EACH = 25

    def test_concurrent_processes_do_not_corrupt_the_chain(self):
        from packages.evidence import EvidenceStore

        with tempfile.TemporaryDirectory() as tmp:
            procs = [multiprocessing.Process(target=_evidence_worker, args=(tmp, self.WRITES_EACH))
                    for _ in range(self.PROCESSES)]
            for p in procs:
                p.start()
            for p in procs:
                p.join(timeout=30)
                self.assertEqual(p.exitcode, 0, "worker process failed or hung")

            store = EvidenceStore(tmp)
            expected = self.PROCESSES * self.WRITES_EACH
            self.assertEqual(len(store), expected, "writes were lost under concurrency")
            ok, _, message = store.verify_chain()
            self.assertTrue(ok, f"chain broken under concurrency: {message}")


if __name__ == "__main__":
    unittest.main()
