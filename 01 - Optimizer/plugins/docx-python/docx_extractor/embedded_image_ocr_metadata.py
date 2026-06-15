"""Metadata aggregation for embedded image OCR results."""

from __future__ import annotations

from typing import Any

from .types import WordOcrBlockSnapshot


def aggregate_embedded_image_ocr_metadata(
    metadata_samples: list[dict[str, Any]],
    ocr_blocks: list[WordOcrBlockSnapshot],
    *,
    processed_images: int,
    errors: list[str],
) -> dict[str, Any]:
    confidences = [block.confidence for block in ocr_blocks if block.confidence is not None]
    first_sample = metadata_samples[0] if metadata_samples else {}

    metadata: dict[str, Any] = {
        "embedded_image_ocr_images_processed": processed_images,
        "embedded_image_ocr_block_count": len(ocr_blocks),
        "embedded_image_ocr_status": embedded_image_ocr_status(processed_images, len(ocr_blocks), bool(errors)),
        "ocr_engine": "llm",
        "ocr_text_blocks": len(ocr_blocks),
        "ocr_backend": first_sample.get("ocr_backend") or "llm",
        "ocr_model_source": first_sample.get("ocr_model_source") or "llm",
    }
    for key in ("ocr_provider_id", "ocr_provider_family", "ocr_model"):
        if first_sample.get(key):
            metadata[key] = first_sample[key]
    if confidences:
        metadata["ocr_avg_confidence"] = round(sum(confidences) / len(confidences), 4)
        metadata["ocr_min_confidence"] = round(min(confidences), 4)
    if errors:
        metadata["embedded_image_ocr_errors"] = errors
    return metadata


def embedded_image_ocr_status(processed_images: int, block_count: int, has_errors: bool) -> str:
    if has_errors and block_count > 0:
        return "partial"
    if has_errors:
        return "error"
    if processed_images == 0:
        return "skipped"
    if block_count == 0:
        return "no_text"
    return "success"
