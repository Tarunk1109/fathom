"""Per-route payload approvals — the mechanism behind `P-APPROVAL-01`.

Operator constraint following INC-001:

> Before any real destination is touched, show me the full payload the agent intends to submit,
> field by field with its source profile, and wait for my approval. I approve each route once.
> No route runs unattended.

Two properties make this a control rather than a courtesy:

**It is recorded, not remembered.** INC-001 happened because the thing preventing profile bleed was
a person paying attention. Approvals are written to disk and read back by the gate.

**It is bound to the payload, not the route.** An approval stores the digest of the exact payload
shown. If the agent later proposes a different payload for the same route, the digest no longer
matches and `verify(...)` reports it. Approving a route once must not become approving whatever
that route decides to send afterwards.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from .audit import payload_digest

DEFAULT_APPROVALS_PATH = Path(__file__).resolve().parents[2] / "out" / "approvals.json"


@dataclass(frozen=True)
class Approval:
    route_id: str
    target: str
    profile_id: str
    payload_digest: str
    field_count: int
    approved_at: str
    approved_by: str
    note: str = ""


class ApprovalStore:
    def __init__(self, path: Path | str | None = None) -> None:
        self.path = Path(path) if path is not None else DEFAULT_APPROVALS_PATH
        self._approvals: dict[str, Approval] = {}
        if self.path.exists():
            for record in json.loads(self.path.read_text(encoding="utf-8")):
                approval = Approval(**record)
                self._approvals[approval.route_id] = approval

    def __len__(self) -> int:
        return len(self._approvals)

    @property
    def approved_route_ids(self) -> frozenset[str]:
        """Feed this to `SessionContext.approved_routes`."""
        return frozenset(self._approvals)

    def get(self, route_id: str) -> Approval | None:
        return self._approvals.get(route_id)

    def approve(self, *, route_id: str, target: str, profile_id: str, payload: dict,
                approved_by: str, note: str = "") -> Approval:
        approval = Approval(
            route_id=route_id,
            target=target,
            profile_id=profile_id,
            payload_digest=payload_digest(payload),
            field_count=len(payload or {}),
            approved_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            approved_by=approved_by,
            note=note,
        )
        self._approvals[route_id] = approval
        self._persist()
        return approval

    def revoke(self, route_id: str) -> bool:
        if route_id not in self._approvals:
            return False
        del self._approvals[route_id]
        self._persist()
        return True

    def verify(self, route_id: str, payload: dict) -> tuple[bool, str]:
        """Confirm the payload about to be sent is the one that was approved."""
        approval = self._approvals.get(route_id)
        if approval is None:
            return False, f"route '{route_id}' has no recorded approval"
        actual = payload_digest(payload)
        if actual != approval.payload_digest:
            return False, (
                f"route '{route_id}' was approved for a different payload "
                f"(approved {approval.payload_digest[:12]}…, proposed {actual[:12]}…). "
                f"Re-approve before sending."
            )
        return True, f"approved {approval.approved_at} by {approval.approved_by}"

    def _persist(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        records = [asdict(a) for a in sorted(self._approvals.values(), key=lambda a: a.route_id)]
        self.path.write_text(json.dumps(records, indent=2) + "\n", encoding="utf-8")
