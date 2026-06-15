"""Named bootstrap data carriers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

SUPPORTED_CONTRACT_VERSION = 1


@dataclass(frozen=True)
class ExternalDependencySpec:
    name: str
    kind: str = "service"
    required: bool = True
    detail: str = ""


@dataclass(frozen=True)
class DebugSurfaceSpec:
    supports_batch: bool = False
    supports_single: bool = False
    supports_scan: bool = False
    input_source: str = ""
    output_source: str = ""
    controls: tuple[str, ...] = ()
    artifacts: tuple[str, ...] = ()


@dataclass(frozen=True)
class ModuleManifestSpec:
    key: str
    display_name: str
    contract_module: str
    runtime_dir: Path
    manifest_path: Path
    contract_version: int = SUPPORTED_CONTRACT_VERSION
    actions: tuple[str, ...] = ()
    external_dependencies: tuple[ExternalDependencySpec, ...] = ()
    debug_surface: DebugSurfaceSpec | None = None


@dataclass(frozen=True)
class ModuleRuntimeSpec:
    key: str
    display_name: str
    module_root: Path
    contract_module: str
    runtime_dir: Path
    python_executable: Path
    manifest_path: Path
    contract_version: int = SUPPORTED_CONTRACT_VERSION
    actions: tuple[str, ...] = ()
    external_dependencies: tuple[ExternalDependencySpec, ...] = ()
    debug_surface: DebugSurfaceSpec | None = None

    def require_actions(self, *actions: str) -> None:
        missing = [action for action in actions if action and action not in self.actions]
        if missing:
            from .exceptions import ModuleRegistryError

            raise ModuleRegistryError(
                f"Module {self.display_name} does not support actions: {', '.join(missing)}"
            )
