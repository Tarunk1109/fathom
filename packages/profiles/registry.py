"""Profile registry — FATHOM §4, with per-field provenance added after INC-001.

Profiles are **records, not code paths** (§4.1). Nothing in FATHOM is hardcoded to a licence class;
the Route Planner reads the active profile and lights up the corresponding modules.

Two independent flags (§2.3, amendment D-003):

- `hypothetical` — conduct: no licence number, no human contact, no commitment steps.
- `sandbox_only` — reach: whether the profile may touch a real destination at all.

Provenance
----------
Every value a profile emits is wrapped in `FieldValue(value, source_profile_id)`. That is what
`P-PROFILE-BLEED-01` reads. Before INC-001 a value was just a string, so a real third-party address
and a synthetic one were indistinguishable once typed into a form — which is precisely why nothing
caught the mixing.

Loading a hypothetical profile is validated, not trusted
--------------------------------------------------------
`§2.1: a hypothetical profile is hypothetical in every field or it is not hypothetical.` The
registry refuses to load one that carries a licence number, or a value matching anything the vault
holds for the operator. A profile that fails validation raises rather than loading in a degraded
state — a half-synthetic profile is the INC-001 condition, and it must not be representable.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from packages.policy.actions import FieldValue, fact_hash  # noqa: E402

DEFAULT_PROFILE_DIR = _REPO_ROOT / "data" / "profiles"

#: Fields a hypothetical profile may never carry, in any form. Checked on load.
FORBIDDEN_UNDER_HYPOTHETICAL = frozenset({
    "licence_number", "license_number", "dl_number", "drivers_licence_number",
    "sin", "social_insurance_number",
})


class ProfileError(ValueError):
    """A profile is invalid. Raised rather than returning a degraded profile."""


@dataclass(frozen=True)
class Profile:
    profile_id: str
    hypothetical: bool
    sandbox_only: bool
    label: str
    description: str

    #: Material facts. Sealed into the session fact-lock at session start and never varied.
    facts: dict[str, str] = field(default_factory=dict)

    #: Coverage elections and other values that may legitimately vary (§10.2).
    elections: dict[str, str] = field(default_factory=dict)

    #: Vault key names for values the repo must never hold. Non-hypothetical profiles only.
    vault_refs: dict[str, str] = field(default_factory=dict)

    active_modules: tuple[str, ...] = ()
    gated_modules: tuple[str, ...] = ()

    # -- provenance ---------------------------------------------------------------------

    def tagged(self, field_names: list[str] | None = None) -> dict[str, FieldValue]:
        """Emit fields wrapped with this profile's id, ready for a payload.

        This is the only supported way to build a submission payload. A value that did not come
        through here has no provenance, and `P-PROFILE-BLEED-01` can refuse it.
        """
        available = {**self.facts, **self.elections}
        names = field_names if field_names is not None else list(available)
        missing = [name for name in names if name not in available]
        if missing:
            raise ProfileError(
                f"profile '{self.profile_id}' has no value for {missing}. Add it to the profile "
                f"record — do not source it from elsewhere (INC-001)."
            )
        return {name: FieldValue(available[name], self.profile_id) for name in names}

    def fact_lock(self) -> dict[str, str]:
        """Hash every material fact. Sealed at session start; §9.2, `P-FACT-01`.

        Applies to hypothetical profiles exactly as to the operator's: if the clean profile's
        facts drift between insurers, every parity and channel-arbitrage claim is invalid.
        """
        return {name: fact_hash(value) for name, value in self.facts.items()}

    def is_labelled_simulation(self) -> bool:
        """§2.3: hypothetical and sandbox-only profiles are labelled everywhere they appear."""
        return self.hypothetical or self.sandbox_only


# --------------------------------------------------------------------------------------
# Validation
# --------------------------------------------------------------------------------------


def validate(profile: Profile, operator_value_hashes: frozenset[str] = frozenset()) -> None:
    """Raise `ProfileError` unless the profile is internally consistent and safe to load.

    `operator_value_hashes` is the set of hashes of every value the vault holds for the operator.
    Passing it lets the registry detect a real-world value that has been copied into a synthetic
    profile — the INC-001 failure — without the registry ever seeing a raw operator value.
    """
    if not profile.profile_id:
        raise ProfileError("profile_id is required")

    if profile.hypothetical:
        offending = sorted(
            name for name in {**profile.facts, **profile.elections}
            if name.lower() in FORBIDDEN_UNDER_HYPOTHETICAL
        )
        if offending:
            raise ProfileError(
                f"hypothetical profile '{profile.profile_id}' carries {offending}. §2.1: a "
                f"hypothetical profile may never hold a licence number. It cannot be loaded."
            )

        if profile.vault_refs:
            raise ProfileError(
                f"hypothetical profile '{profile.profile_id}' references vault keys "
                f"{sorted(profile.vault_refs)}. The vault holds the operator's real values; a "
                f"hypothetical profile must not reach into it (INC-001)."
            )

        bleed = sorted(
            name for name, value in {**profile.facts, **profile.elections}.items()
            if fact_hash(value) in operator_value_hashes
        )
        if bleed:
            raise ProfileError(
                f"hypothetical profile '{profile.profile_id}' carries operator values in {bleed}. "
                f"§2.1: hypothetical in every field or it is not hypothetical (INC-001)."
            )

    if not profile.hypothetical and not profile.sandbox_only and not profile.vault_refs:
        raise ProfileError(
            f"profile '{profile.profile_id}' is neither hypothetical nor sandbox-only, so its "
            f"real values must come from the vault. No vault_refs are declared."
        )


# --------------------------------------------------------------------------------------
# Registry
# --------------------------------------------------------------------------------------


class ProfileRegistry:
    def __init__(self, directory: Path | str | None = None,
                 operator_value_hashes: frozenset[str] = frozenset()) -> None:
        self.directory = Path(directory) if directory is not None else DEFAULT_PROFILE_DIR
        self.operator_value_hashes = operator_value_hashes
        self._profiles: dict[str, Profile] = {}
        if self.directory.is_dir():
            self.load_all()

    def load_all(self) -> None:
        for path in sorted(self.directory.glob("*.json")):
            profile = self.load(path)
            self._profiles[profile.profile_id] = profile

    def load(self, path: Path) -> Profile:
        data = json.loads(path.read_text(encoding="utf-8"))
        try:
            profile = Profile(
                profile_id=data["profile_id"],
                hypothetical=bool(data["hypothetical"]),
                sandbox_only=bool(data["sandbox_only"]),
                label=data.get("label", data["profile_id"]),
                description=data.get("description", ""),
                facts=dict(data.get("facts", {})),
                elections=dict(data.get("elections", {})),
                vault_refs=dict(data.get("vault_refs", {})),
                active_modules=tuple(data.get("active_modules", ())),
                gated_modules=tuple(data.get("gated_modules", ())),
            )
        except KeyError as exc:
            raise ProfileError(f"{path.name} is missing required field {exc}") from exc

        validate(profile, self.operator_value_hashes)
        return profile

    def __len__(self) -> int:
        return len(self._profiles)

    def __contains__(self, profile_id: object) -> bool:
        return profile_id in self._profiles

    def get(self, profile_id: str) -> Profile:
        if profile_id not in self._profiles:
            raise ProfileError(f"no such profile: {profile_id}")
        return self._profiles[profile_id]

    def ids(self) -> tuple[str, ...]:
        return tuple(sorted(self._profiles))

    def primary(self) -> Profile:
        """The profile that does the broad retrieval (§3 as reframed)."""
        return self.get("profile_hypo_clean")
