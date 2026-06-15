"""Normalize OCR payload blocks from embedded DOCX images."""

from __future__ import annotations

from pathlib import PurePosixPath
from typing import Any

from .embedded_image_references import EmbeddedImageReference, sanitize_identifier
from .types import WordOcrBlockSnapshot


def normalize_embedded_image_ocr_block(
    reference: EmbeddedImageReference,
    block: Any,
    paragraph_index: int,
    *,
    order: int,
) -> WordOcrBlockSnapshot | None:
    if not isinstance(block, dict):
        return None

    text = str(block.get("value") or "").strip()
    if not text:
        return None

    confidence = _coerce_float(block.get("confidence"))
    block_type = "header" if reference.story_part_kind == "header" else "paragraph"
    part_stem = sanitize_identifier(PurePosixPath(reference.story_part_name).stem) or "story"
    prefix = "ocr_header" if block_type == "header" else "ocr_paragraph"

    return WordOcrBlockSnapshot(
        id=f"{prefix}_{part_stem}_{reference.image_stem}_{order:03d}",
        type=block_type,
        text=text,
        paragraph_index=paragraph_index,
        confidence=confidence,
    )


def _coerce_float(value: Any) -> float | None:
    try:
        return round(float(value), 4)
    except (TypeError, ValueError):
        return None
