"""Boundary adapters for plugin/runtime-facing processor calls."""
from __future__ import annotations

import inspect
import logging
import sys
from pathlib import Path
from typing import Callable

from optimizer_ocr import extract_page_assets

from ..input_catalog.adapter import build_catalog_entry
from ..models import ExtractResult, FileFormat, PluginError
from ..runtime_policy.ocr_policy import INTERPRETER_PAGE_ASSET_DPI

logger = logging.getLogger(__name__)
_LLM_OCR_PLUGIN = "optimizer-llm-ocr"


def _surface_module():
    return sys.modules[__package__]


def _manager_invoke(processor, plugin_name: str, file_path: Path, config_override: dict | None, worker_startup_config: dict | None):
    invoke = processor._plugin_mgr.invoke
    try:
        signature = inspect.signature(invoke)
    except (TypeError, ValueError):
        signature = None
    if signature and "worker_startup_config" in signature.parameters:
        return invoke(plugin_name, file_path, config_override, worker_startup_config=worker_startup_config)
    return invoke(plugin_name, file_path, config_override)


def build_single_entry(file_path: Path, content_hash: str):
    stat_result = file_path.stat()
    return build_catalog_entry(
        file_path,
        stat_result,
        input_root=file_path.parent,
        content_hash=content_hash,
        created="",
        modified="",
    )


def invoke_plugin(
    processor,
    plugin_name: str,
    file_path: Path,
    config_override: dict | None = None,
    worker_startup_config: dict | None = None,
) -> ExtractResult:
    try:
        result = _manager_invoke(processor, plugin_name, file_path, config_override, worker_startup_config)
    except Exception as exc:
        raise PluginError(plugin_name, f"Unerwarteter Plugin-Fehler: {exc}") from exc
    if not isinstance(result, ExtractResult):
        raise PluginError(plugin_name, f"Ungueltiges Plugin-Ergebnis: {type(result).__name__}")
    return result


def detect_scan_state(processor, *, fmt: str, ext: str, result: ExtractResult, plugin_name: str, policy_config: dict | None = None) -> bool:
    if fmt == FileFormat.IMAGE:
        return True
    if fmt != FileFormat.PDF:
        return False
    try:
        payload = {"blocks": result.blocks, "metadata": result.metadata}
        return bool(_surface_module().is_scan(payload, ext, **dict(policy_config or {})))
    except Exception as exc:
        raise PluginError(plugin_name, f"Scan-Erkennung fehlgeschlagen: {exc}") from exc


def should_use_vision_route(ext: str, scan_detected: bool, policy_config: dict | None = None) -> bool:
    return bool(_surface_module().should_use_vision(ext, scan_detected, **dict(policy_config or {})))


def is_ocr_plugin(processor, plugin_name: str) -> bool:
    if plugin_name == _LLM_OCR_PLUGIN:
        return True
    manifest = processor._plugin_mgr.get_manifest(plugin_name)
    return bool(manifest and "ocr" in manifest.capabilities)


def resolve_ocr_plugin_name(processor, ext: str, preferred_plugin: str | None = None) -> str | None:
    del processor, ext, preferred_plugin
    return _LLM_OCR_PLUGIN


def apply_ocr_route(
    processor,
    *,
    file_path: Path,
    filename: str,
    ext: str,
    plugin_name: str,
    result: ExtractResult,
    scan_detected: bool,
    vision: bool,
    on_plugin_selected: Callable[[str], None] | None = None,
    preferred_plugin: str | None = None,
    backup_ocr_on_scan: bool = True,
    config_override: dict | None = None,
    worker_startup_config: dict | None = None,
    image_paths: list[str] | None = None,
    requires_ocr: bool | None = None,
    wants_backup_ocr: bool | None = None,
) -> tuple[ExtractResult, str, bool]:
    del ext, preferred_plugin, config_override, worker_startup_config
    initial_is_ocr = processor._is_ocr_plugin(plugin_name)
    ocr_was_used = initial_is_ocr
    required = bool(result.needs_ocr) if requires_ocr is None else bool(requires_ocr)
    backup_requested = (
        vision and scan_detected and backup_ocr_on_scan and not initial_is_ocr
        if wants_backup_ocr is None
        else bool(wants_backup_ocr)
    )
    if not (required or backup_requested):
        return result, plugin_name, ocr_was_used
    if on_plugin_selected:
        on_plugin_selected(_LLM_OCR_PLUGIN)
    if not image_paths:
        if required:
            raise PluginError(_LLM_OCR_PLUGIN, "LLM-OCR erforderlich, aber keine Page-Assets gerendert.")
        if on_plugin_selected:
            on_plugin_selected(plugin_name)
        logger.warning("OCR-Backup uebersprungen fuer %s: keine Page-Assets", filename)
        return result, plugin_name, ocr_was_used
    ocr_payload = extract_page_assets(list(image_paths), source_path=file_path)
    ocr_result = ExtractResult(
        status=str(ocr_payload.get("status") or "error"),
        blocks=list(ocr_payload.get("blocks") or []),
        metadata=dict(ocr_payload.get("metadata") or {}),
        errors=[str(item) for item in ocr_payload.get("errors", [])],
        processing_time_ms=int(ocr_payload.get("processing_time_ms") or 0),
        needs_ocr=bool(ocr_payload.get("needs_ocr", False)),
    )
    if ocr_result.status == "success":
        return ocr_result, _LLM_OCR_PLUGIN, True
    detail = processor._result_error_detail(ocr_result, "LLM-OCR lieferte Fehlerstatus ohne Details")
    if on_plugin_selected:
        on_plugin_selected(plugin_name)
    if required:
        raise PluginError(_LLM_OCR_PLUGIN, detail)
    logger.warning("OCR-Backup fehlgeschlagen fuer %s: %s", filename, detail)
    return result, plugin_name, ocr_was_used


def render_vision_assets(
    processor,
    file_path: Path,
    output_dir: Path | None = None,
    asset_key: str | None = None,
    *,
    page_assets_dir: Path | None = None,
    render_config: dict | None = None,
) -> list[str]:
    render_config = dict(render_config or {})
    render_kwargs = {
        "dpi": INTERPRETER_PAGE_ASSET_DPI,
        "quality": int(render_config.get("quality", 95) or 95),
    }
    if page_assets_dir is not None:
        image_paths = _surface_module().render_page_assets(str(file_path), page_assets_dir=str(page_assets_dir), **render_kwargs)
    else:
        if output_dir is None:
            raise OSError(f"Vision-Output-Verzeichnis fehlt fuer {file_path}")
        image_paths = _surface_module().render_page_assets(str(file_path), str(output_dir), asset_key=asset_key, **render_kwargs)
    if not image_paths:
        raise OSError(f"Vision-Assets fehlen fuer {file_path}")
    missing = [path for path in image_paths if not path or not Path(path).is_file()]
    if missing:
        raise OSError(f"Vision-Assets unvollstaendig fuer {file_path}: {missing[0]}")
    return image_paths
