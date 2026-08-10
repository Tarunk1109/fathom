"""Hash-chained, append-only audit log for the Policy Engine — FATHOM §9.1.

Every decision, allow or deny, appends here. That is what makes the safety claim demonstrable
rather than aspirational (§7.1): a judge can recompute the chain and see that no entry was edited,
reordered or removed after the fact.

Chain construction
------------------
Each entry stores `prev_hash`, the previous entry's `entry_hash`. The first entry's `prev_hash` is
the genesis constant. `entry_hash` is the SHA-256 of the entry's canonical JSON with `entry_hash`
itself excluded. Changing any field of any entry breaks that entry's hash and every subsequent
link, and `verify_chain()` reports the first index where it diverges.

No PII, by construction
-----------------------
The log stores **no payload values, ever**. It stores the payload's field *names* and a SHA-256
digest of the whole payload — enough to prove what was proposed and to detect tampering, and
insufficient to reconstruct a single value. Targets are stripped of query strings and fragments,
which is where insurer journeys carry identifiers. Caller-supplied rationale is scrubbed through
the shared PII rule set before it is written.

This is stronger than redacting values, and it is deliberate: an append-only file is exactly the
wrong place to discover a leak, because there is no clean way to remove it afterwards.
"""

from __future__ import annotations

import hashlib
import json
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse, urlunparse

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:  # no packaging in this repo; imports are path-based
    sys.path.insert(0, str(_REPO_ROOT))

from tools.pii_sweep import redact_text  # noqa: E402

GENESIS_HASH = "0" * 64
DEFAULT_AUDIT_PATH = _REPO_ROOT / "out" / "audit" / "policy_audit.jsonl"
MAX_RATIONALE_CHARS = 240


# --------------------------------------------------------------------------------------
# Entry
# --------------------------------------------------------------------------------------


@dataclass(frozen=True)
class AuditEntry:
    index: int
    timestamp: str
    session_id: str
    route_id: str
    profile_id: str
    action_kind: str
    target_safe: str
    payload_fields: tuple[str, ...]
    payload_digest: str
    rationale_redacted: str
    verdict: str
    rule_id: str
    explanation: str
    prev_hash: str
    entry_hash: str

    def hashable(self) -> dict:
        data = asdict(self)
        data.pop("entry_hash")
        data["payload_fields"] = list(data["payload_fields"])
        return data

    def compute_hash(self) -> str:
        return hashlib.sha256(canonical_json(self.hashable()).encode("utf-8")).hexdigest()

    def to_json(self) -> str:
        data = asdict(self)
        data["payload_fields"] = list(data["payload_fields"])
        return json.dumps(data, ensure_ascii=False, sort_keys=True)

    @staticmethod
    def from_dict(data: dict) -> "AuditEntry":
        payload = dict(data)
        payload["payload_fields"] = tuple(payload.get("payload_fields") or ())
        return AuditEntry(**payload)


def canonical_json(data: dict) -> str:
    return json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


# --------------------------------------------------------------------------------------
# Sanitising inputs before they are written
# --------------------------------------------------------------------------------------


def safe_target(target: str) -> str:
    """Strip everything from a target that could carry an identifier.

    Query strings and fragments are dropped — insurer journeys routinely put quote references and
    session tokens there. Phone numbers are reduced to a scheme marker; the number itself is a
    published business line, but the log has no use for it and the rule is simpler when nothing
    dialable is written.
    """
    if not target:
        return ""
    lowered = target.strip()
    if lowered.lower().startswith(("tel:", "sip:")):
        return f"{lowered.split(':', 1)[0].lower()}:[REDACTED_ROUTE]"
    if "://" not in lowered:
        return redact_text(lowered.split("?", 1)[0].split("#", 1)[0])
    parsed = urlparse(lowered)
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", "", ""))


def payload_digest(payload: dict | None) -> str:
    """SHA-256 of the payload. Proves what was proposed without storing any value."""
    if not payload:
        return hashlib.sha256(b"{}").hexdigest()
    try:
        serialised = canonical_json({str(k): _stringify(v) for k, v in payload.items()})
    except (TypeError, ValueError):
        serialised = canonical_json({str(k): repr(v) for k, v in payload.items()})
    return hashlib.sha256(serialised.encode("utf-8")).hexdigest()


def _stringify(value: object) -> str:
    return value if isinstance(value, str) else repr(value)


def payload_field_names(payload: dict | None) -> tuple[str, ...]:
    """Field names only. Names describe structure; values are the PII."""
    if not payload:
        return ()
    return tuple(sorted(str(key) for key in payload))


# --------------------------------------------------------------------------------------
# Verification
# --------------------------------------------------------------------------------------


@dataclass(frozen=True)
class ChainVerification:
    ok: bool
    entries_checked: int
    first_bad_index: int | None = None
    reason: str | None = None

    def describe(self) -> str:
        if self.ok:
            return f"chain intact — {self.entries_checked} entries verified"
        return (
            f"chain BROKEN at index {self.first_bad_index} "
            f"after {self.entries_checked} intact entries: {self.reason}"
        )


def verify_entries(entries: list[AuditEntry]) -> ChainVerification:
    """Recompute the whole chain and report the first divergence.

    Reports the *first* divergence rather than a list, because after the first break every
    subsequent link is broken as a consequence and reporting them all obscures where it happened.
    """
    previous = GENESIS_HASH
    for position, entry in enumerate(entries):
        if entry.index != position:
            return ChainVerification(False, position, position,
                                     f"index is {entry.index}, expected {position}")
        if entry.prev_hash != previous:
            return ChainVerification(False, position, position,
                                     "prev_hash does not match the preceding entry's hash")
        recomputed = entry.compute_hash()
        if recomputed != entry.entry_hash:
            return ChainVerification(False, position, position,
                                     "entry_hash does not match the entry's contents")
        previous = entry.entry_hash
    return ChainVerification(True, len(entries))


# --------------------------------------------------------------------------------------
# The log
# --------------------------------------------------------------------------------------


class AuditLog:
    """Append-only JSONL log. Existing entries are read but never rewritten."""

    def __init__(self, path: Path | str | None = None) -> None:
        self.path = Path(path) if path is not None else DEFAULT_AUDIT_PATH
        self._entries: list[AuditEntry] = []
        if self.path.exists():
            self._load()

    def _load(self) -> None:
        with self.path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if line:
                    self._entries.append(AuditEntry.from_dict(json.loads(line)))

    @property
    def entries(self) -> list[AuditEntry]:
        return list(self._entries)

    def __len__(self) -> int:
        return len(self._entries)

    @property
    def head_hash(self) -> str:
        return self._entries[-1].entry_hash if self._entries else GENESIS_HASH

    def append(
        self,
        *,
        session_id: str,
        route_id: str,
        profile_id: str,
        action_kind: str,
        target: str,
        payload: dict | None,
        rationale: str,
        verdict: str,
        rule_id: str,
        explanation: str,
        timestamp: str | None = None,
    ) -> AuditEntry:
        index = len(self._entries)
        unsealed = AuditEntry(
            index=index,
            timestamp=timestamp or datetime.now(timezone.utc).isoformat(timespec="seconds"),
            session_id=session_id,
            route_id=route_id,
            profile_id=profile_id,
            action_kind=action_kind,
            target_safe=safe_target(target),
            payload_fields=payload_field_names(payload),
            payload_digest=payload_digest(payload),
            rationale_redacted=redact_text(rationale, MAX_RATIONALE_CHARS),
            verdict=verdict,
            rule_id=rule_id,
            explanation=explanation,
            prev_hash=self.head_hash,
            entry_hash="",
        )
        sealed = AuditEntry(**{**unsealed.hashable(),
                               "payload_fields": unsealed.payload_fields,
                               "entry_hash": unsealed.compute_hash()})
        self._entries.append(sealed)
        self._persist(sealed)
        return sealed

    def _persist(self, entry: AuditEntry) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(entry.to_json() + "\n")

    def verify_chain(self) -> ChainVerification:
        return verify_entries(self._entries)
