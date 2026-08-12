"""Evidence chain — FATHOM §9.5, scoped by DL-03.

Content-addressed by sha256 of the **redacted** bytes, hash-chained, append-only. Same construction
as the policy audit chain, for the same reason: a judge can recompute it and see nothing was edited.

`redact before write` is enforced structurally — `append()` runs the redactor itself rather than
trusting the caller to have done it, so there is no path that stores a raw byte.
"""

from __future__ import annotations

import hashlib
import json
import sys
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from packages.redactor import redact  # noqa: E402

try:
    import fcntl
    _HAS_FLOCK = True
except ImportError:
    _HAS_FLOCK = False

GENESIS = "0" * 64
DEFAULT_EVIDENCE_DIR = _REPO_ROOT / "out" / "evidence"


class EvidenceError(RuntimeError):
    pass


@dataclass(frozen=True)
class Artifact:
    index: int
    cid: str
    timestamp: str
    route_id: str
    profile_id: str
    kind: str
    source: str
    redaction_rules_fired: tuple[str, ...]
    byte_length: int
    prev_hash: str
    entry_hash: str

    def hashable(self) -> dict:
        data = asdict(self)
        data.pop("entry_hash")
        data["redaction_rules_fired"] = list(data["redaction_rules_fired"])
        return data

    def compute_hash(self) -> str:
        blob = json.dumps(self.hashable(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(blob.encode("utf-8")).hexdigest()


class EvidenceStore:
    """Safe for concurrent multi-process writers — see `packages.policy.audit.AuditLog` for the
    exact failure this mirrors and fixes: `index = len(self._artifacts)` from a stale in-memory
    snapshot let two concurrent processes both claim the same index. `append()` now locks and
    re-reads the file fresh before computing the next index."""

    def __init__(self, directory: Path | str | None = None) -> None:
        self.dir = Path(directory) if directory else DEFAULT_EVIDENCE_DIR
        self.index_path = self.dir / "chain.jsonl"
        self.blobs = self.dir / "blobs"
        self._artifacts: list[Artifact] = []
        if self.index_path.exists():
            self._load()

    def _load(self) -> None:
        self._artifacts = []
        for line in self.index_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                row = json.loads(line)
                row["redaction_rules_fired"] = tuple(row["redaction_rules_fired"])
                self._artifacts.append(Artifact(**row))

    @contextmanager
    def _locked(self):
        if not _HAS_FLOCK:
            yield
            return
        self.dir.mkdir(parents=True, exist_ok=True)
        lock_path = self.index_path.with_suffix(".lock")
        with open(lock_path, "a+") as lock_handle:
            fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(lock_handle.fileno(), fcntl.LOCK_UN)

    def __len__(self) -> int:
        return len(self._artifacts)

    @property
    def artifacts(self) -> list[Artifact]:
        return list(self._artifacts)

    @property
    def head(self) -> str:
        return self._artifacts[-1].entry_hash if self._artifacts else GENESIS

    def append(self, *, content: str, route_id: str, profile_id: str, kind: str,
               source: str) -> Artifact:
        """Redact, content-address, chain, persist. Returns the artifact."""
        report = redact(content)
        blob = report.text.encode("utf-8")
        cid = "cid:sha256-" + hashlib.sha256(blob).hexdigest()
        safe_source = redact(source).text

        with self._locked():
            if self.index_path.exists():
                self._load()

            unsealed = Artifact(
                index=len(self._artifacts),
                cid=cid,
                timestamp=datetime.now(timezone.utc).isoformat(timespec="seconds"),
                route_id=route_id, profile_id=profile_id, kind=kind,
                source=safe_source,
                redaction_rules_fired=tuple(report.rules_fired),
                byte_length=len(blob),
                prev_hash=self.head,
                entry_hash="",
            )
            sealed = Artifact(**{**unsealed.hashable(),
                                 "redaction_rules_fired": unsealed.redaction_rules_fired,
                                 "entry_hash": unsealed.compute_hash()})

            self.blobs.mkdir(parents=True, exist_ok=True)
            (self.blobs / f"{cid.split('-', 1)[1]}.txt").write_bytes(blob)
            with self.index_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(
                    {**asdict(sealed), "redaction_rules_fired": list(sealed.redaction_rules_fired)},
                    sort_keys=True) + "\n")
            self._artifacts.append(sealed)
            return sealed

    def fetch(self, cid: str) -> str:
        path = self.blobs / f"{cid.split('-', 1)[1]}.txt"
        if not path.exists():
            raise EvidenceError(f"no artifact for {cid}")
        return path.read_text(encoding="utf-8")

    def verify_chain(self) -> tuple[bool, int | None, str]:
        prev = GENESIS
        for position, artifact in enumerate(self._artifacts):
            if artifact.index != position:
                return False, position, "index out of sequence"
            if artifact.prev_hash != prev:
                return False, position, "prev_hash mismatch"
            if artifact.compute_hash() != artifact.entry_hash:
                return False, position, "entry_hash does not match contents"
            prev = artifact.entry_hash
        return True, None, f"chain intact — {len(self._artifacts)} artifacts"
