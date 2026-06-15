"""Path-stable bootstrap surface for the standalone orchestrator bundle."""

from . import adapter
from .adapter import (
    MODULE_REGISTRY_PATH,
    ORCHESTRATOR_ROOT,
    STATE_ROOT,
    bundled_python_candidates,
)
from .exceptions import ModuleRegistryError, StartupPrerequisiteError
from .types import DebugSurfaceSpec, ExternalDependencySpec, ModuleRuntimeSpec, SUPPORTED_CONTRACT_VERSION
from .workflow import (
    ensure_startup_prerequisites,
    load_module_registry,
    resolve_bundled_python,
    resolve_module_runtime,
)

__all__ = [
    "ExternalDependencySpec",
    "DebugSurfaceSpec",
    "MODULE_REGISTRY_PATH",
    "ModuleRegistryError",
    "ModuleRuntimeSpec",
    "ORCHESTRATOR_ROOT",
    "STATE_ROOT",
    "SUPPORTED_CONTRACT_VERSION",
    "StartupPrerequisiteError",
    "bundled_python_candidates",
    "ensure_startup_prerequisites",
    "load_module_registry",
    "resolve_bundled_python",
    "resolve_module_runtime",
]
