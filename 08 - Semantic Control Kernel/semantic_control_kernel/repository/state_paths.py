from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from semantic_control_kernel.repository.errors import StatePathEscapeError, StateRootError
from semantic_control_kernel.repository.path_hashing import utc_iso
from semantic_control_kernel.repository.state_path_dirs import StatePathDirectoryProperties
from semantic_control_kernel.repository.state_path_layout import (
    STATE_LAYOUT_DIRS,
    STATE_LAYOUT_VERSION,
    STATE_README_TEXT,
    STATE_ROOT_MANIFEST_SCHEMA_VERSION,
    _ENSURED_LAYOUT_ROOTS,
    _is_relative_safe,
    _path_key,
    _write_json,
    _write_text,
)


@dataclass(frozen=True)
class StatePaths(StatePathDirectoryProperties):
    module_root: Path
    state_root: Path

    @classmethod
    def from_module_root(cls, module_root: str | os.PathLike[str]) -> "StatePaths":
        root = Path(module_root).resolve(strict=False)
        return cls(module_root=root, state_root=root / "state")

    @classmethod
    def from_state_root(cls, state_root: str | os.PathLike[str]) -> "StatePaths":
        root = Path(state_root).resolve(strict=False)
        return cls(module_root=root.parent, state_root=root)

    def ensure_layout(self, module_key: str = "semantic_control_kernel") -> None:
        root_key = _path_key(self.state_root)
        if root_key in _ENSURED_LAYOUT_ROOTS:
            return
        self.state_root.mkdir(parents=True, exist_ok=True)
        for relative_dir in STATE_LAYOUT_DIRS:
            (self.state_root / relative_dir).mkdir(parents=True, exist_ok=True)
        self._ensure_readme()
        self._ensure_state_manifest(module_key)
        self._ensure_support_index()
        _ENSURED_LAYOUT_ROOTS.add(root_key)

    def safe_path(self, *relative_parts: str | os.PathLike[str]) -> Path:
        parts = [os.fspath(part) for part in relative_parts]
        if not _is_relative_safe(parts):
            raise StatePathEscapeError(f"Unsafe state path component: {relative_parts!r}")
        candidate = self.state_root.joinpath(*parts)
        self.require_under_state_root(candidate)
        return candidate

    def require_under_state_root(self, path: str | os.PathLike[str]) -> Path:
        raw = Path(path)
        candidate = Path(os.path.abspath(os.fspath(raw)))
        root = Path(os.path.abspath(os.fspath(self.state_root)))
        try:
            common = os.path.commonpath([os.fspath(root), os.fspath(candidate)])
        except ValueError as exc:
            raise StatePathEscapeError(f"State path escapes root: {candidate}") from exc
        if os.path.normcase(common) != os.path.normcase(os.fspath(root)):
            raise StatePathEscapeError(f"State path escapes root: {candidate}")
        return candidate

    def relative_to_state_root(self, path: str | os.PathLike[str]) -> str:
        candidate = self.require_under_state_root(path)
        try:
            return candidate.relative_to(Path(os.path.abspath(os.fspath(self.state_root)))).as_posix()
        except ValueError as exc:
            raise StateRootError(f"State path is not under state root: {candidate}") from exc

    def expected_layout_entries(self) -> set[str]:
        entries = {"README.md", "state_root_manifest.json"}
        for relative_dir in STATE_LAYOUT_DIRS:
            path = Path(relative_dir)
            for index in range(1, len(path.parts) + 1):
                entries.add(Path(*path.parts[:index]).as_posix())
        entries.add("support/index.json")
        return entries

    def _ensure_readme(self) -> None:
        readme = self.state_root / "README.md"
        if not readme.exists():
            _write_text(readme, STATE_README_TEXT)

    def _ensure_state_manifest(self, module_key: str) -> None:
        manifest = self.state_root / "state_root_manifest.json"
        if manifest.exists():
            return
        _write_json(
            manifest,
            {
                "created_at": utc_iso(),
                "module_key": module_key,
                "schema_version": STATE_ROOT_MANIFEST_SCHEMA_VERSION,
                "state_layout_version": STATE_LAYOUT_VERSION,
                "state_root_path": str(self.state_root),
            },
        )

    def _ensure_support_index(self) -> None:
        if self.support_index_path.exists():
            return
        _write_json(
            self.support_index_path,
            {
                "schema_version": "repository.support_bundle_index.v1",
                "support_bundle_refs": [],
                "updated_at": utc_iso(),
            },
        )
