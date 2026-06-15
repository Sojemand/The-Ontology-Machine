"""Embedded image OCR helpers for the docx-python adapter."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from pathlib import Path, PurePosixPath
import tempfile
from typing import Any
from zipfile import ZipFile

from .embedded_image_ocr_blocks import normalize_embedded_image_ocr_block
from .embedded_image_ocr_metadata import aggregate_embedded_image_ocr_metadata
from .embedded_image_ocr_runtime import config_enabled, run_embedded_image_ocr
from .embedded_image_references import embedded_image_part_names, embedded_image_references
from .types import WordOcrBlockSnapshot, WordStageError


def extract_embedded_image_ocr_blocks(
    archive: ZipFile,
    story_parts: Sequence[Any],
    start_paragraph_index: int,
    config: dict[str, Any],
    *,
    extract_page_assets: Callable[..., dict[str, Any]],
) -> tuple[tuple[WordOcrBlockSnapshot, ...], dict[str, Any]]:
    references = embedded_image_references(archive, tuple(story_parts))
    metadata: dict[str, Any] = {
        "embedded_image_count": len(references),
        "embedded_image_ocr_images_processed": 0,
        "embedded_image_ocr_block_count": 0,
    }
    if not references:
        metadata["embedded_image_ocr_status"] = "no_embedded_images"
        return (), metadata

    if not config_enabled(config.get("embedded_image_ocr_enabled"), default=False):
        metadata["embedded_image_ocr_status"] = "disabled"
        return (), metadata

    ocr_blocks: list[WordOcrBlockSnapshot] = []
    next_paragraph_index = start_paragraph_index
    errors: list[str] = []
    successful_runs = 0
    metadata_samples: list[dict[str, Any]] = []

    for reference in references:
        if reference.image_name not in archive.namelist():
            errors.append(f"adapter.ocr: Eingebettetes Bild fehlt im Archiv: {reference.image_name}")
            continue

        suffix = PurePosixPath(reference.image_name).suffix.lower() or ".bin"
        with tempfile.TemporaryDirectory(prefix="docx_embedded_image_ocr_") as tmp_dir_name:
            tmp_dir = Path(tmp_dir_name)
            image_path = tmp_dir / f"{reference.image_stem}{suffix}"
            image_path.write_bytes(archive.read(reference.image_name))

            try:
                payload = run_embedded_image_ocr(image_path, config, extract_page_assets=extract_page_assets)
            except WordStageError as exc:
                errors.append(str(exc))
                continue

        successful_runs += 1
        metadata_samples.append(dict(payload.get("metadata") or {}))
        errors.extend(str(item).strip() for item in payload.get("errors", []) if str(item).strip())

        for block in payload.get("blocks", []):
            normalized = normalize_embedded_image_ocr_block(
                reference,
                block,
                next_paragraph_index,
                order=len(ocr_blocks),
            )
            if normalized is None:
                continue
            ocr_blocks.append(normalized)
            next_paragraph_index += 1

    metadata.update(
        aggregate_embedded_image_ocr_metadata(
            metadata_samples,
            ocr_blocks,
            processed_images=successful_runs,
            errors=errors,
        )
    )
    return tuple(ocr_blocks), metadata


__all__ = ["embedded_image_part_names", "extract_embedded_image_ocr_blocks"]
