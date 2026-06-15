"""Repository helpers for publishing rendered mail pages."""
from __future__ import annotations

import shutil
from pathlib import Path

from ..rendering.repository import publish_stage_dir
from .mail_compound_types import MAX_MAIL_PAGE_BYTES


def publish_compound_pages(stage_dir: Path, dest_dir: Path, pages: list[object]) -> list[str]:
    if not pages:
        raise RuntimeError("Mail-Compound erzeugte keine Seiten.")
    staged_paths: list[str] = []
    for index, page in enumerate(pages, start=1):
        target_path = stage_dir / f"page_{index:03d}.png"
        target_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(page.image_path, target_path)
        if target_path.stat().st_size > MAX_MAIL_PAGE_BYTES:
            raise RuntimeError(f"Mail-Seite ueberschreitet das sichere Bildbudget: {target_path.name}")
        staged_paths.append(str(target_path))
    return publish_stage_dir(stage_dir, dest_dir, staged_paths)
