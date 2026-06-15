"""Write operations for orchestrator edit surfaces."""

from . import repository


def write_surface(surface_id: str, value: dict) -> dict:
    return repository.write_policy(surface_id, value)
