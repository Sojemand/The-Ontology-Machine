"""Validation operations for orchestrator edit surfaces."""

from . import repository


def validate_surface(surface_id: str, value: dict) -> dict:
    return repository.validate_policy(surface_id, value)
