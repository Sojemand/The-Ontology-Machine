"""Cleanup helpers for generated processor output."""
from __future__ import annotations

import logging
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)


def cleanup_generated_output(
    processor,
    *,
    output_dir: Path | None,
    raw_paths: list[Path],
    image_paths: list[str],
    asset_dirs: list[Path] | None = None,
    page_assets_root: Path | None = None,
    ingest_id: str,
) -> None:
    del ingest_id
    for raw_path in raw_paths:
        try:
            raw_path.unlink(missing_ok=True)
        except OSError as exc:
            logger.warning("Cleanup fehlgeschlagen fuer Raw-Output %s: %s", raw_path, exc)
    if not image_paths and not asset_dirs:
        return

    if page_assets_root is None:
        if output_dir is None:
            return
        page_assets_root = output_dir / "page_assets"
    try:
        page_assets_root_resolved = page_assets_root.resolve()
    except OSError:
        page_assets_root_resolved = page_assets_root
    candidates = list(asset_dirs or []) + [Path(path).parent for path in image_paths]
    resolved_asset_dirs: set[Path] = set()
    for candidate in candidates:
        try:
            candidate_resolved = candidate.resolve()
            candidate_resolved.relative_to(page_assets_root_resolved)
            resolved_asset_dirs.add(candidate_resolved)
        except (OSError, ValueError):
            continue
    for asset_dir in sorted(resolved_asset_dirs, key=lambda path: len(path.parts), reverse=True):
        try:
            shutil.rmtree(asset_dir)
        except OSError as exc:
            logger.warning("Cleanup fehlgeschlagen fuer Vision-Assets %s: %s", asset_dir, exc)
