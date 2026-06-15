"""Repository stage for mutable Corpus Builder runtime directories."""

from __future__ import annotations

from .types import ContextPaths


def ensure_runtime_dirs(paths: ContextPaths) -> None:
    for directory in (paths.mutable_runtime_dir, paths.state_dir, paths.output_dir):
        directory.mkdir(parents=True, exist_ok=True)
