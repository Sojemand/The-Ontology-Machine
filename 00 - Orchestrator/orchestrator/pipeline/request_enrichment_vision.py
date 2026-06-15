"""Vision-specific request shaping for minimal raw-v2 payloads."""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

from .request_enrichment_helpers import required_list, required_mapping

_LEGACY_RAW_KEYS = (
    "doc",
    "ctx",
    "pages",
    "file_reference",
    "vision_assets",
    "guardrail",
    "summary",
    "sections",
    "facts",
    "tables",
    "block_refs",
    "runtime_trace",
    "compression_audit",
)
_INTERPRETER_PAGE_ASSET_DPI = 150


def build_vision_request(
    payload: dict[str, Any],
    *,
    working_page_paths: tuple[Path, ...],
) -> dict[str, Any]:
    _reject_legacy_payload_shapes(payload)
    if str(payload.get("schema_version") or "").strip() != "optimizer_raw_v2":
        raise ValueError("Vision request enrichment expects optimizer_raw_v2.")
    raw_source = required_mapping(payload.get("source"), "source")
    raw_context = _mapping_or_empty(payload.get("context"))
    ocr_reference = required_mapping(payload.get("ocr_reference"), "ocr_reference")
    blocks = required_list(ocr_reference.get("blocks", []), "ocr_reference.blocks")
    source = copy.deepcopy(raw_source)
    context = copy.deepcopy(raw_context)
    page_assets = _page_assets_for_request(
        context=context,
        source=source,
        working_page_paths=working_page_paths,
    )
    return {
        "source": source,
        "context": context,
        "page_assets": page_assets,
        "ocr_reference": {
            "blocks": [copy.deepcopy(required_mapping(block, "ocr_reference.blocks[]")) for block in blocks],
        },
    }


def _page_assets_for_request(
    *,
    context: dict[str, Any],
    source: dict[str, Any],
    working_page_paths: tuple[Path, ...],
) -> list[dict[str, Any]]:
    if not working_page_paths:
        raise ValueError("working_page_paths is missing for vision request enrichment.")
    selected_paths = working_page_paths
    document_page_count = _positive_int(context.get("document_page_count")) or _positive_int(source.get("page_count"))
    page_number = _positive_int(context.get("page_number"))
    if page_number is not None and document_page_count and document_page_count > 1:
        if page_number > len(working_page_paths):
            raise ValueError("Vision request references an invalid page_number.")
        selected_paths = (working_page_paths[page_number - 1],)
    assets: list[dict[str, Any]] = []
    for index, path in enumerate(selected_paths, start=1):
        asset_page = page_number if len(selected_paths) == 1 and page_number is not None else index
        assets.append(
            {
                "page": asset_page,
                "path": str(path),
                "media_type": "image/png",
                "format": "png",
                "color_mode": "grayscale",
                "bit_depth": 8,
                "dpi_x": _INTERPRETER_PAGE_ASSET_DPI,
                "dpi_y": _INTERPRETER_PAGE_ASSET_DPI,
                "dpi_unit": "inch",
            }
        )
    return assets


def _mapping_or_empty(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    return required_mapping(value, "context")


def _positive_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


def _reject_legacy_payload_shapes(payload: dict[str, Any]) -> None:
    present = [key for key in _LEGACY_RAW_KEYS if key in payload]
    if present:
        raise ValueError(f"Legacy optimizer raw fields are not allowed: {', '.join(present)}")


__all__ = ["build_vision_request"]
