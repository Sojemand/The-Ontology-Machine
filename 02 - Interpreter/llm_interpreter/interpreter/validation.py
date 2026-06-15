"""Hard request and output invariants for the interpreter pipeline."""
from __future__ import annotations

from typing import Any

from ..models.types import InterpreterConfig
from ..prompts.adapter import load_page_assets
from ..prompts.projection_hint import validate_projection_catalog, validate_projection_hint
from ..prompts.types import LoadedPageAsset
from ..providers import ProviderError
from ..profile_policy import request_profile
from .persisted_validation import validate_persisted_output_shape
from .types import LoadedRequest

_MISSING = object()


def validate_request(
    request_input: dict[str, Any] | LoadedRequest,
    config: InterpreterConfig | None = None,
) -> list[LoadedPageAsset]:
    loaded_request = _coerce_loaded_request(request_input)
    request = loaded_request.request
    _reject_legacy_request_shapes(request)
    runtime_config = config or InterpreterConfig()
    source = request.get("source", {})
    if source is None:
        source = {}
    source = _require_mapping(source, "source")
    if not str(source.get("file_name", "")).strip():
        raise ProviderError("source.file_name fehlt")
    page_count = source.get("page_count")
    if page_count is not None and (isinstance(page_count, bool) or not isinstance(page_count, int) or page_count <= 0):
        raise ProviderError("source.page_count muss eine positive Ganzzahl sein")
    context = request.get("context", {})
    if context is None:
        context = {}
    _require_mapping(context, "context")
    validate_projection_catalog(request.get("projection_catalog"), error_type=ProviderError)
    reference = request.get("ocr_reference", {})
    if reference is None:
        reference = {}
    reference = _require_mapping(reference, "ocr_reference")
    _reject_legacy_ocr_reference_shapes(reference)
    _require_list(reference.get("blocks", []), "ocr_reference.blocks")
    try:
        return load_page_assets(
            request,
            asset_roots=loaded_request.asset_roots + runtime_config.page_asset_allowed_roots,
            max_page_assets=runtime_config.max_page_assets,
            max_page_asset_bytes=runtime_config.max_page_asset_bytes,
            max_request_asset_bytes=runtime_config.max_request_asset_bytes,
        )
    except ValueError as exc:
        raise ProviderError(str(exc)) from exc


def validate_llm_output_shape(llm_result: dict[str, Any], request: dict[str, Any]) -> None:
    processing = _require_llm_field(llm_result, "processing", "processing", dict)
    _require_llm_field(llm_result, "classification", "classification", dict)
    context = _require_llm_field(llm_result, "context", "context", dict)
    content = _require_llm_field(llm_result, "content", "content", dict)
    _require_llm_field(content, "structure", "content.structure", dict)
    _require_llm_field(content, "fields", "content.fields", dict)
    rows = _require_llm_field(content, "rows", "content.rows", list)
    segments = _require_llm_field(content, "segments", "content.segments", list)
    if "free_text" in content and content["free_text"] is not None and not isinstance(content["free_text"], str):
        raise ProviderError("LLM-Output ungueltig: content.free_text muss str oder null sein")
    profile = processing.get("interpreter_profile")
    expected_profile = request_profile(request)
    if profile != expected_profile:
        raise ProviderError(
            f"LLM-Output ungueltig: processing.interpreter_profile muss '{expected_profile}' sein"
        )
    _validate_optional_field(processing, "needs_review", bool)
    _validate_optional_field(processing, "review_reason", str, allow_none=True)
    _validate_optional_field(processing, "vision_used", bool)
    validate_projection_hint(context, request, error_type=ProviderError)
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise ProviderError(f"LLM-Output ungueltig: content.rows[{index}] muss ein Objekt sein")
    _validate_segments(segments)


def _require_mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ProviderError(f"{label} muss ein Objekt sein")
    return value


def _reject_legacy_request_shapes(request: dict[str, Any]) -> None:
    legacy_keys = [key for key in ("pages", "file_reference") if key in request]
    if legacy_keys:
        raise ProviderError(f"Legacy-Request-Shape nicht erlaubt: {', '.join(legacy_keys)}")


def _reject_legacy_ocr_reference_shapes(reference: dict[str, Any]) -> None:
    legacy_keys = [key for key in ("summary", "sections", "facts", "tables", "block_refs") if key in reference]
    if legacy_keys:
        raise ProviderError(f"Legacy-OCR-Reference nicht erlaubt: {', '.join(legacy_keys)}")


def _require_list(value: Any, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise ProviderError(f"{label} muss eine Liste sein")
    return value


def _require_llm_field(payload: dict[str, Any], key: str, label: str, expected_type: type) -> Any:
    value = payload.get(key, _MISSING)
    if value is _MISSING:
        raise ProviderError(f"LLM-Output ungueltig: {label} fehlt")
    if not isinstance(value, expected_type):
        raise ProviderError(f"LLM-Output ungueltig: {label} muss {expected_type.__name__} sein")
    return value


def _validate_optional_field(
    payload: dict[str, Any],
    key: str,
    expected_type: type,
    *,
    allow_none: bool = False,
) -> None:
    if key not in payload:
        return
    value = payload[key]
    if allow_none and value is None:
        return
    if not isinstance(value, expected_type):
        suffix = " oder null" if allow_none else ""
        raise ProviderError(f"LLM-Output ungueltig: {key} muss {expected_type.__name__} sein{suffix}")


def _validate_segments(segments: list[Any]) -> set[str]:
    known_ids: set[str] = set()
    for index, segment in enumerate(segments):
        if not isinstance(segment, dict):
            raise ProviderError(f"LLM-Output ungueltig: content.segments[{index}] muss ein Objekt sein")
        segment.pop("_source_refs", None)
        segment_id = segment.get("segment_id")
        if not isinstance(segment_id, str) or not segment_id.strip():
            raise ProviderError(f"LLM-Output ungueltig: content.segments[{index}].segment_id muss ein nicht-leerer String sein")
        segment_id = segment_id.strip()
        if segment_id in known_ids:
            raise ProviderError(f"LLM-Output ungueltig: content.segments[{index}].segment_id ist doppelt")
        unit_kind = segment.get("unit_kind")
        if not isinstance(unit_kind, str) or not unit_kind.strip():
            raise ProviderError(f"LLM-Output ungueltig: content.segments[{index}].unit_kind muss ein nicht-leerer String sein")
        page = segment.get("page")
        if isinstance(page, bool) or not isinstance(page, int) or page <= 0:
            raise ProviderError(f"LLM-Output ungueltig: content.segments[{index}].page muss eine positive Ganzzahl sein")
        sequence = segment.get("sequence")
        if isinstance(sequence, bool) or not isinstance(sequence, int) or sequence <= 0:
            raise ProviderError(f"LLM-Output ungueltig: content.segments[{index}].sequence muss eine positive Ganzzahl sein")
        text = segment.get("text")
        if not isinstance(text, str) or not text.strip():
            raise ProviderError(f"LLM-Output ungueltig: content.segments[{index}].text muss ein nicht-leerer String sein")
        _validate_segment_optional_text(segment, index, "section")
        _validate_segment_optional_text(segment, index, "label")
        _validate_segment_optional_text(segment, index, "function")
        _validate_segment_optional_mapping(segment, index, "attributes")
        if "confidence" in segment and not _is_number(segment.get("confidence")):
            raise ProviderError(f"LLM-Output ungueltig: content.segments[{index}].confidence muss number sein")
        known_ids.add(segment_id)
    return known_ids


def _validate_segment_optional_text(segment: dict[str, Any], index: int, key: str) -> None:
    if key not in segment or segment[key] is None:
        return
    if not isinstance(segment[key], str):
        raise ProviderError(f"LLM-Output ungueltig: content.segments[{index}].{key} muss str oder null sein")


def _validate_segment_optional_mapping(segment: dict[str, Any], index: int, key: str) -> None:
    if key not in segment or segment[key] is None:
        return
    value = segment[key]
    if not isinstance(value, dict):
        raise ProviderError(f"LLM-Output ungueltig: content.segments[{index}].{key} muss ein Objekt sein")


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _coerce_loaded_request(request_input: dict[str, Any] | LoadedRequest) -> LoadedRequest:
    if isinstance(request_input, LoadedRequest):
        return request_input
    source = request_input.get("source", {}) if isinstance(request_input, dict) else {}
    label = str((source or {}).get("file_name") or "request.json")
    return LoadedRequest(request=request_input, label=label, request_path=None, asset_roots=())
