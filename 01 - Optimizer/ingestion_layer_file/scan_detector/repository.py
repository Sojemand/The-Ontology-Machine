"""Filesystem transitions for published scan-detector page assets."""
from __future__ import annotations

from pathlib import Path

from ..rendering.repository import (
    cleanup_stage_dir,
    clear_existing_asset_dir,
    create_stage_dir,
    publish_stage_dir,
)


def _create_stage_dir(dest_dir: Path) -> Path:
    return create_stage_dir(dest_dir)


def _publish_stage_dir(stage_dir: Path, dest_dir: Path, paths: list[str]) -> list[str]:
    return publish_stage_dir(stage_dir, dest_dir, paths)


def _cleanup_stage_dir(stage_dir: Path) -> None:
    cleanup_stage_dir(stage_dir)


def _clear_existing_asset_dir(dest_dir: Path) -> None:
    clear_existing_asset_dir(dest_dir)
