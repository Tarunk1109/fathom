"""Encrypted vault for the operator's real values — FATHOM §9.2.

Fernet (AES-128-CBC + HMAC) with a key file held **outside the repository** at `~/.fathom/vault.key`,
created 0600 on first use. Deliberately minimal: no rotation, no envelope keys, no threat model
beyond "the repo must never contain a real value" (§2.1).

Two properties the rest of the system depends on:

**Values are returned tagged, never raw into a payload.** `inject()` returns `FieldValue` objects
carrying `profile_operator`, so anything the vault supplies is provenanced and `P-PROFILE-BLEED-01`
can see it.

**Hashes are available without decryption of intent.** `value_hashes()` lets the profile registry
detect an operator value pasted into a synthetic profile (INC-001) without that check ever handling
a plaintext value.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from packages.policy.actions import FieldValue, fact_hash  # noqa: E402

DEFAULT_KEY_PATH = Path.home() / ".fathom" / "vault.key"
DEFAULT_VAULT_PATH = Path.home() / ".fathom" / "vault.enc"


class VaultError(RuntimeError):
    pass


class Vault:
    def __init__(self, vault_path: Path | str | None = None, key_path: Path | str | None = None,
                 profile_id: str = "profile_operator") -> None:
        self.path = Path(vault_path) if vault_path else DEFAULT_VAULT_PATH
        self.key_path = Path(key_path) if key_path else DEFAULT_KEY_PATH
        self.profile_id = profile_id
        self._fernet = Fernet(self._load_or_create_key())
        self._values: dict[str, str] = self._load()

    # -- key ----------------------------------------------------------------------------

    def _load_or_create_key(self) -> bytes:
        if self.key_path.exists():
            return self.key_path.read_bytes().strip()
        self.key_path.parent.mkdir(parents=True, exist_ok=True)
        key = Fernet.generate_key()
        self.key_path.write_bytes(key)
        os.chmod(self.key_path, 0o600)
        return key

    # -- storage ------------------------------------------------------------------------

    def _load(self) -> dict[str, str]:
        if not self.path.exists():
            return {}
        try:
            return json.loads(self._fernet.decrypt(self.path.read_bytes()).decode("utf-8"))
        except InvalidToken as exc:
            raise VaultError(f"cannot decrypt {self.path} with {self.key_path}") from exc

    def _persist(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        blob = self._fernet.encrypt(json.dumps(self._values, sort_keys=True).encode("utf-8"))
        self.path.write_bytes(blob)
        os.chmod(self.path, 0o600)

    # -- api ----------------------------------------------------------------------------

    def set(self, key: str, value: str) -> None:
        self._values[key] = value
        self._persist()

    def set_many(self, values: dict[str, str]) -> None:
        self._values.update(values)
        self._persist()

    def keys(self) -> tuple[str, ...]:
        return tuple(sorted(self._values))

    def has(self, key: str) -> bool:
        return key in self._values

    def __len__(self) -> int:
        return len(self._values)

    def value_hashes(self) -> frozenset[str]:
        """Hashes only. Lets the profile registry catch INC-001 without touching a raw value."""
        return frozenset(fact_hash(v) for v in self._values.values())

    def inject(self, vault_refs: dict[str, str]) -> dict[str, FieldValue]:
        """Resolve a profile's `vault_refs` into provenanced field values.

        The only way a real value enters a payload. Never returns raw strings.
        """
        missing = sorted(ref for ref in vault_refs.values() if ref not in self._values)
        if missing:
            raise VaultError(f"vault has no value for {missing}. Run scripts/vault_init.py")
        return {field: FieldValue(self._values[ref], self.profile_id)
                for field, ref in vault_refs.items()}
