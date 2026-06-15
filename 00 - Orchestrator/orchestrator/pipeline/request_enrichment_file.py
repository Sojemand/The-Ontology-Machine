"""File-profile request shaping for minimal optimizer_raw_v2 payloads."""

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


def normalized_interpreter_profile(interpreter_profile: str, payload: dict[str, Any]) -> str:
    profile = str(interpreter_profile or "").strip().lower()
    if profile in {"vision", "file"}:
        return profile
    optimizer_profile = str(payload.get("optimizer_profile", "")).strip().lower()
    if optimizer_profile in {"vision", "file"}:
        return optimizer_profile
    return "vision"


def build_file_request(payload: dict[str, Any], *, working_page_paths: tuple[Path, ...]) -> dict[str, Any]:
    _reject_legacy_payload_shapes(payload)
    if str(payload.get("schema_version") or "").strip() != "optimizer_raw_v2":
        raise ValueError("File request enrichment expects optimizer_raw_v2.")
    raw_source = required_mapping(payload.get("source"), "source")
    raw_context = _mapping_or_empty(payload.get("context"))
    ocr_reference = required_mapping(payload.get("ocr_reference"), "ocr_reference")
    blocks = required_list(ocr_reference.get("blocks", []), "ocr_reference.blocks")
    source = copy.deepcopy(raw_source)
    context = copy.deepcopy(raw_context)
    return {
        "source": source,
        "context": context,
        "page_assets": _page_assets_for_request(
            context=context,
            source=source,
            working_page_paths=working_page_paths,
        ),
        "ocr_reference": {
            "blocks": [copy.deepcopy(required_mapping(block, "ocr_reference.blocks[]")) for block in blocks],
        },
    }


def select_page_targets(
    payload: dict[str, Any],
    request: dict[str, Any],
    page_targets: tuple[Any, ...],
) -> tuple[Any, ...]:
    del payload
    request_pages = required_list(request.get("page_assets", []), "page_assets")
    if not page_targets or len(request_pages) == len(page_targets):
        return page_targets
    if len(request_pages) != 1:
        return page_targets
    page_number = _request_page_number(request)
    if page_number <= 0 or page_number > len(page_targets):
        raise ValueError("Page-scoped raw payload references an invalid page number.")
    return (page_targets[page_number - 1],)


def _page_assets_for_request(
    *,
    context: dict[str, Any],
    source: dict[str, Any],
    working_page_paths: tuple[Path, ...],
) -> list[dict[str, Any]]:
    if not working_page_paths:
        raise ValueError("working_page_paths is missing for file request enrichment.")
    selected_paths = working_page_paths
    document_page_count = _positive_int(context.get("document_page_count")) or _positive_int(source.get("page_count"))
    page_number = _positive_int(context.get("page_number"))
    if page_number is not None and document_page_count and document_page_count > 1:
        if page_number > len(working_page_paths):
            raise ValueError("File request references an invalid page_number.")
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


def _request_page_number(request: dict[str, Any]) -> int:
    context = request.get("context", {}) if isinstance(request.get("context"), dict) else {}
    page_number = _positive_int(context.get("page_number"))
    if page_number is not None:
        return page_number
    page_assets = required_list(request.get("page_assets", []), "page_assets")
    if page_assets:
        page_value = _positive_int(required_mapping(page_assets[0], "page_assets[0]").get("page"))
        if page_value is not None:
            return page_value
    return 1


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


__all__ = ["build_file_request", "normalized_interpreter_profile", "select_page_targets"]
