"""Read operations for orchestrator edit surfaces."""

from . import repository


def read_surface(surface_id: str) -> dict:
    return repository.read_policy(surface_id)
