"""Validation stage for hard asset-contract invariants."""
from __future__ import annotations

from .types import LocalProfileSpec


def require_profile_id(profile_id: str) -> str:
    target = profile_id.strip()
    if not target:
        raise ValueError("taxonomy_profile_id darf nicht leer sein.")
    return target


def require_profile_spec(spec: LocalProfileSpec | None, profile_id: str) -> LocalProfileSpec:
    if spec is None:
        raise ValueError(f"Lokales Taxonomie-Profil nicht gefunden: {profile_id}")
    return spec
