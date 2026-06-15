"""Path-stable context surface for Corpus Builder runtime locations."""

from __future__ import annotations

from pathlib import Path

from . import repository
from .policy import build_context_paths, package_module_root, resolve_optional_path, resolve_path
from .types import ContextPaths


class ModuleContext:
    """Thin compatibility surface over the module runtime path contract."""

    __slots__ = ("_paths",)

    def __init__(self, module_root: str | Path):
        self._paths = build_context_paths(module_root)

    @classmethod
    def from_package_root(cls) -> "ModuleContext":
        return cls(package_module_root())

    @property
    def paths(self) -> ContextPaths:
        return self._paths

    @property
    def module_root(self) -> Path:
        return self._paths.module_root

    @property
    def config_dir(self) -> Path:
        return self._paths.config_dir

    @property
    def runtime_dir(self) -> Path:
        return self._paths.mutable_runtime_dir

    @property
    def bundled_runtime_dir(self) -> Path:
        return self._paths.bundled_runtime_dir

    @property
    def state_dir(self) -> Path:
        return self._paths.state_dir

    @property
    def output_dir(self) -> Path:
        return self._paths.output_dir

    @property
    def config_path(self) -> Path:
        return self._paths.config_path

    @property
    def semantic_release_state_path(self) -> Path:
        return self._paths.semantic_release_state_path

    @property
    def semantic_release_report_path(self) -> Path:
        return self._paths.semantic_release_report_path

    def ensure_runtime_dirs(self) -> None:
        repository.ensure_runtime_dirs(self._paths)

    def resolve_path(self, value: str | Path, *, base_dir: Path | None = None) -> Path:
        return resolve_path(self.module_root, value, base_dir=base_dir)

    def resolve_optional_path(
        self,
        value: str | Path | None,
        *,
        base_dir: Path | None = None,
    ) -> Path | None:
        return resolve_optional_path(self.module_root, value, base_dir=base_dir)
