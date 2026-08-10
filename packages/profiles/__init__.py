"""FATHOM profile registry (§4). Profiles are records, not code paths."""

from .registry import (
    DEFAULT_PROFILE_DIR,
    FORBIDDEN_UNDER_HYPOTHETICAL,
    Profile,
    ProfileError,
    ProfileRegistry,
    validate,
)

__all__ = [
    "DEFAULT_PROFILE_DIR",
    "FORBIDDEN_UNDER_HYPOTHETICAL",
    "Profile",
    "ProfileError",
    "ProfileRegistry",
    "validate",
]
