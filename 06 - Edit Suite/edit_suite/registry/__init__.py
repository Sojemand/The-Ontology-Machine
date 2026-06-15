"""Path-stable surface for Edit Suite discovery."""

from .types import ModuleReadinessEntry, RegistrySnapshot
from .workflow import discover_registry

__all__ = ["ModuleReadinessEntry", "RegistrySnapshot", "discover_registry"]
