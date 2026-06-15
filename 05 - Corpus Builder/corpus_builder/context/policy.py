"""Policy stage for Corpus Builder runtime layout and path resolution."""

from __future__ import annotations

from pathlib import Path

from .types import ContextPaths


def package_module_root() -> Path:
    return Path(__file__).resolve().parents[2]


def build_context_paths(module_root: str | Path) -> ContextPaths:
    root = Path(module_root).resolve()
    config_dir = root / "config"
    mutable_runtime_dir = root / "runtime"
    state_dir = root / "state"
    return ContextPaths(
        module_root=root,
        config_dir=config_dir,
        mutable_runtime_dir=mutable_runtime_dir,
        bundled_runtime_dir=mutable_runtime_dir / "python",
        state_dir=state_dir,
        output_dir=root / "output",
        config_path=config_dir / "corpus_config.json",
        semantic_release_state_path=state_dir / "semantic_release.active.json",
        semantic_release_report_path=state_dir / "semantic_release_report.json",
    )


def resolve_path(module_root: Path, value: str | Path, *, base_dir: Path | None = None) -> Path:
    path = Path(str(value)).expanduser()
    if path.is_absolute():
        return path.resolve()
    anchor = Path(base_dir) if base_dir is not None else module_root
    return (anchor / path).resolve()


def resolve_optional_path(
    module_root: Path,
    value: str | Path | None,
    *,
    base_dir: Path | None = None,
) -> Path | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    return resolve_path(module_root, text, base_dir=base_dir)
