"""Model response normalization for the Optimizer OCR port."""

from __future__ import annotations

import json
import time
from typing import Any

from .errors import LlmOcrResponseError


def parse_model_json(response_text: str) -> dict[str, Any]:
    try:
        payload = json.loads(response_text)
    except json.JSONDecodeError as exc:
        raise LlmOcrResponseError("LLM-OCR Modelloutput ist kein valides JSON.") from exc
    if not isinstance(payload, dict):
        raise LlmOcrResponseError("LLM-OCR Modelloutput ist kein JSON-Objekt.")
    return payload


def normalize_blocks(raw_blocks: Any) -> list[dict[str, Any]]:
    if not isinstance(raw_blocks, list):
        raise LlmOcrResponseError("LLM-OCR Modelloutput enthaelt keine blocks-Liste.")
    blocks: list[dict[str, Any]] = []
    for index, raw_block in enumerate(raw_blocks):
        if not isinstance(raw_block, dict):
            raise LlmOcrResponseError(f"LLM-OCR Block {index} ist kein JSON-Objekt.")
        value = str(raw_block.get("value") or "").strip()
        if not value:
            continue
        block: dict[str, Any] = {
            "id": str(raw_block.get("id") or f"ocr_{index:04d}"),
            "type": str(raw_block.get("type") or "paragraph"),
            "value": value,
        }
        layout_label = _optional_text(raw_block.get("layout_label"))
        if layout_label:
            block["layout_label"] = layout_label
        value_type = str(raw_block.get("value_type") or "text").strip()
        if value_type and value_type != "text":
            block["value_type"] = value_type
        position = _normalize_position(raw_block.get("position"), fallback_page=raw_block.get("page"))
        if position:
            block["position"] = position
        formatting = _normalize_formatting(raw_block.get("formatting"), bold=raw_block.get("bold"))
        if formatting:
            block["formatting"] = formatting
        confidence = _optional_float(raw_block.get("confidence"))
        if confidence is not None:
            block["confidence"] = confidence
        blocks.append(block)
    return blocks


def metadata(settings: Any, assets: list[dict[str, str]], model_metadata: Any, blocks: list[dict[str, Any]]) -> dict[str, Any]:
    data = dict(model_metadata) if isinstance(model_metadata, dict) else {}
    data.update(
        {
            "ocr_engine": "llm",
            "ocr_backend": "llm",
            "ocr_provider_id": settings.provider_id,
            "ocr_provider_family": settings.provider_family,
            "ocr_model": settings.model,
            "ocr_model_source": "llm",
            "ocr_page_asset_count": len(assets),
            "ocr_text_blocks": len(blocks),
        }
    )
    return data


def envelope(status: str, blocks: list[dict[str, Any]], metadata: dict[str, Any], errors: list[str], start: int) -> dict[str, Any]:
    return {
        "status": status,
        "blocks": blocks,
        "metadata": metadata,
        "errors": errors,
        "processing_time_ms": (time.perf_counter_ns() - start) // 1_000_000,
        "needs_ocr": False,
    }


def _normalize_position(position: Any, *, fallback_page: Any = None) -> dict[str, Any]:
    data = position if isinstance(position, dict) else {}
    normalized = {
        "sheet": _optional_text(data.get("sheet")),
        "row": _optional_int(data.get("row")),
        "col": _optional_int(data.get("col")),
        "col_letter": _optional_text(data.get("col_letter")),
        "page": _optional_int(data.get("page")) or _optional_int(fallback_page),
        "paragraph_index": _optional_int(data.get("paragraph_index")),
        "table_index": _optional_int(data.get("table_index")),
    }
    return {key: value for key, value in normalized.items() if value is not None}


def _normalize_formatting(formatting: Any, *, bold: Any = None) -> dict[str, Any]:
    data = formatting if isinstance(formatting, dict) else {}
    bold_value = data.get("bold", bold)
    if bold_value is True:
        return {"bold": True}
    if isinstance(bold_value, str) and bold_value.strip().lower() == "true":
        return {"bold": True}
    return {}


def _optional_text(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None


def _optional_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _optional_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return round(float(value), 4)
    except (TypeError, ValueError):
        return None
