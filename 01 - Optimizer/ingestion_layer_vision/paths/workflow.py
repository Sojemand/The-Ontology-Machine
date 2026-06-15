"""Workflow stage for fallback-aware Optimizer path setup."""
from __future__ import annotations

from pathlib import Path

from .policy import _build_layout, _fallback_home
from .types import PathLayout


def resolve_layout(module_root_path: Path | None = None, app_home_path: Path | None = None) -> PathLayout:
    return _build_layout(module_root_path, app_home_path)


def ensure_app_layout(module_root_path: Path | None = None, app_home_path: Path | None = None) -> PathLayout:
    layout = resolve_layout(module_root_path, app_home_path)
    try:
        return _ensure_layout(layout)
    except OSError:
        if app_home_path is not None or layout.app_home == _fallback_home(module_root_path):
            raise
        return _ensure_layout(resolve_layout(module_root_path, _fallback_home(module_root_path)))


def _ensure_layout(layout: PathLayout) -> PathLayout:
    for directory in (layout.config_dir, layout.state_dir, layout.output_dir, layout.log_dir):
        directory.mkdir(parents=True, exist_ok=True)
    _seed_config_tree(layout)
    return layout


def _seed_config_tree(layout: PathLayout) -> None:
    if not layout.bundled_config_dir.exists():
        return
    for source in layout.bundled_config_dir.rglob("*"):
        relative = source.relative_to(layout.bundled_config_dir)
        target = layout.config_dir / relative
        if source.is_dir():
            target.mkdir(parents=True, exist_ok=True)
            continue
        _seed_file(target, source)


def _seed_file(target: Path, source: Path) -> None:
    if target.exists():
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    data = source.read_bytes()
    try:
        with open(target, "xb") as handle:
            handle.write(data)
    except FileExistsError:
        return
    except Exception:
        target.unlink(missing_ok=True)
        raise

