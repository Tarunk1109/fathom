"""Encrypted operator vault (§9.2). Values never leave it in the clear except at injection."""
from .vault import Vault, VaultError, DEFAULT_KEY_PATH, DEFAULT_VAULT_PATH
__all__ = ["Vault", "VaultError", "DEFAULT_KEY_PATH", "DEFAULT_VAULT_PATH"]
