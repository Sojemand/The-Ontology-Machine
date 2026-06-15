"""Policy helpers for source-backed profile discovery."""
from __future__ import annotations

from .types import LocalProfileSpec


def sort_local_profiles(profiles: list[LocalProfileSpec]) -> list[LocalProfileSpec]:
    return list(profiles)
