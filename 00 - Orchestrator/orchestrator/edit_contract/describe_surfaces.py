"""Descriptor builder for orchestrator edit surfaces."""

from . import repository


def describe_surfaces() -> list[dict]:
    return repository.describe_surfaces()
