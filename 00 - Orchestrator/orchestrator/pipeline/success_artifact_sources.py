"""Shared source discovery for success artifact publication."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from . import page_image_assets, success_publication


def artifact_sources(record: Any, list_attr: str, single_attr: str) -> list[Path]:
    values = list(getattr(record.artifacts, list_attr, []) or [])
    if not values:
        single_value = str(getattr(record.artifacts, single_attr, "") or "").strip()
        values = [single_value] if single_value else []
    return [success_publication.existing_path(value) for value in values if str(value).strip()]


def extra_request_page_images(record: Any) -> list[Path]:
    return page_image_assets.extra_render_paths_from_raws(
        (str(path) for path in artifact_sources(record, "optimizer_raw_paths", "raw_path")),
        known_path_values=record.artifacts.optimizer_page_image_paths,
    )
