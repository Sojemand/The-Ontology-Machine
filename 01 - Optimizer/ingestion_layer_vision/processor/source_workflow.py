"""Source preparation and extract-route setup for processor workflows."""
from __future__ import annotations

import uuid

from ..input_catalog import CatalogEntry
from ..models import ExtractResult, FileFormat
from ..runtime_policy import ocr_policy
from . import adapter, validation
from .types import PreparedSource

_LLM_OCR_PLUGIN = "optimizer-llm-ocr"


def _prepare_source(processor, entry: CatalogEntry) -> PreparedSource:
    validation.ensure_existing_file(entry.path)
    validation.ensure_file_size(entry.size_bytes, processor._config.max_file_size_mb)
    ext = entry.extension.lower()
    fmt = FileFormat.from_ext(ext)
    plugin_name = processor._plugin_mgr.get_plugin_for_format(ext)
    if not plugin_name and fmt == FileFormat.IMAGE:
        plugin_name = _LLM_OCR_PLUGIN
    else:
        plugin_name = validation.ensure_plugin_name(plugin_name, ext)
    return PreparedSource(
        entry=entry,
        file_path=entry.path,
        filename=entry.filename,
        ext=ext,
        fmt=fmt,
        relative_path=entry.relative_path or entry.filename,
        size=entry.size_bytes,
        content_hash=processor._resolve_content_hash(entry.path, entry.content_hash),
        ingest_id=str(uuid.uuid4()),
        plugin_name=plugin_name,
    )


def _extract_source(processor, source: PreparedSource, on_plugin_selected=None) -> None:
    policy = getattr(getattr(processor, "_runtime_policy_state", None), "ocr_policy", None)
    if source.fmt == FileFormat.IMAGE:
        if on_plugin_selected:
            on_plugin_selected(_LLM_OCR_PLUGIN)
        result = ExtractResult(
            status="success",
            blocks=[],
            metadata={"needs_ocr": True},
            errors=[],
            processing_time_ms=0,
            needs_ocr=True,
        )
    else:
        result = processor._invoke_plugin(source.plugin_name, source.file_path)
    validation.ensure_success_result(source.plugin_name, result)
    source.scan_detected = processor._detect_scan_state(
        fmt=source.fmt,
        ext=source.ext,
        result=result,
        plugin_name=source.plugin_name,
        policy_config=ocr_policy.scan_policy(policy),
    )
    source.vision = adapter.should_use_vision_route(
        source.ext,
        source.scan_detected,
        policy_config=ocr_policy.vision_route_policy(policy),
    )
    source.ocr_required = bool(result.needs_ocr)
    if source.ocr_required:
        source.vision = True
    source.backup_ocr_requested = source.vision and source.scan_detected and ocr_policy.force_backup_on_scan(policy)
    source.render_config = ocr_policy.page_image_render_policy(policy)
    source.result = result
