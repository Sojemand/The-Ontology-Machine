"""Workflow helpers for optimizer file-profile contract actions."""
from __future__ import annotations

from contextlib import contextmanager
import os
from pathlib import Path

from optimizer_ocr.request_capture import REQUEST_DIR_ENV

from ..paths import ensure_app_layout
from ..processor import policy as processor_policy
from .pdf_classification import classify_pdf_metadata
from . import validation
from .types import (
    DEFAULT_HEALTHCHECK_TIMEOUT_SECONDS,
    HEALTHCHECK_PIPELINE_RUN_SCOPE,
    PIPELINE_RUN_HEALTHCHECK_TIMEOUT_SECONDS,
)
_SKIPPED_PIPELINE_RUN_DETAIL = "Nicht fuer aktuellen pipeline_run benoetigt."
_PLUGIN_HEALTHCHECKS = (
    ("pdf-pymupdf", "runtime", True),
    ("docx-python", "runtime", True),
    ("odt-odfpy", "runtime", True),
    ("rtf-reader", "runtime", True),
    ("mail-rfc822", "runtime", True),
    ("mail-outlook-msg", "runtime", True),
    ("mail-outlook-store", "runtime", False),
)


def error_response(message: str) -> dict:
    return {"status": "error", "error": message}


def normalize_action(payload: dict) -> str:
    return validation.normalize_action(payload)


def classify_document(payload: dict, *, pdf_extract) -> dict:
    try:
        source_path = validation.require_pdf_source_path(payload)
    except (FileNotFoundError, ValueError) as exc:
        return error_response(str(exc))
    try:
        pdf_result = pdf_extract(source_path)
    except Exception as exc:
        return error_response(str(exc))
    if str(pdf_result.get("status", "")).strip().lower() != "success":
        errors = pdf_result.get("errors", [])
        message = str(errors[0]).strip() if isinstance(errors, list) and errors else "PDF-Klassifikation fehlgeschlagen."
        return error_response(message)
    metadata = pdf_result.get("metadata", {}) or {}
    classification, reason = classify_pdf_metadata(metadata, needs_ocr=bool(pdf_result.get("needs_ocr", False)))
    return {
        "status": "ok",
        "classification": classification,
        "reason": reason,
    }


def extract_document(
    payload: dict,
    *,
    root: Path,
    app_home: Path | None,
    load_config,
    plugin_manager_cls,
    processor_cls,
) -> dict:
    try:
        source_path = validation.require_source_path(payload)
        raw_output_path = validation.require_raw_output_path(payload)
        page_assets_dir = validation.require_page_assets_dir(payload)
        ocr_request_dir = validation.optional_ocr_request_dir(payload)
        logical_source_path = validation.require_logical_source_path(payload)
    except FileNotFoundError as exc:
        return error_response(str(exc))
    except ValueError as exc:
        return error_response(str(exc))

    layout = ensure_app_layout(module_root_path=root, app_home_path=app_home)
    config = load_config(layout.default_config_path)
    plugin_mgr = plugin_manager_cls(layout.plugins_dir, config)
    try:
        processor = processor_cls(config, plugin_mgr)
        try:
            with _ocr_request_capture(ocr_request_dir):
                extracts = processor.process_single(
                    source_path,
                    write_output=True,
                    raw_output_path=raw_output_path,
                    page_assets_dir=page_assets_dir,
                    logical_source_path=logical_source_path,
                )
        except Exception as exc:
            return error_response(str(exc))
    finally:
        plugin_mgr.kill_all()

    if not extracts:
        return error_response("Optimizer lieferte keine Raw-Extracts")

    extract = extracts[0]
    page_raw_paths = [str(raw_output_path)]
    if len(extracts) > 1:
        page_raw_paths = []
        candidate_paths = processor_policy.page_raw_output_paths(raw_output_path, len(extracts) - 1)
        for page_extract, page_path in zip(extracts[1:], candidate_paths, strict=False):
            page_number = int(page_extract.page_number or 0)
            if page_number <= 0:
                continue
            if page_path.exists() and page_path.is_file():
                page_raw_paths.append(str(page_path))
    ingest_id = extract.source.ingest_id or ""
    if not raw_output_path.exists() or not raw_output_path.is_file():
        return error_response(f"Raw-Extract fehlt nach Verarbeitung: {raw_output_path}")
    return {
        "status": "ok",
        "content_hash": extract.source.content_hash,
        "ingest_id": ingest_id,
        "document_raw_path": str(raw_output_path),
        "page_raw_paths": page_raw_paths,
        "page_asset_paths": list(extract.image_paths),
        "ocr_request_paths": _ocr_request_paths(ocr_request_dir),
    }


@contextmanager
def _ocr_request_capture(ocr_request_dir: Path | None):
    previous = os.environ.get(REQUEST_DIR_ENV)
    if ocr_request_dir is None:
        yield
        return
    ocr_request_dir.mkdir(parents=True, exist_ok=True)
    os.environ[REQUEST_DIR_ENV] = str(ocr_request_dir)
    try:
        yield
    finally:
        if previous is None:
            os.environ.pop(REQUEST_DIR_ENV, None)
        else:
            os.environ[REQUEST_DIR_ENV] = previous


def _ocr_request_paths(ocr_request_dir: Path | None) -> list[str]:
    if ocr_request_dir is None or not ocr_request_dir.exists():
        return []
    return [str(path) for path in sorted(ocr_request_dir.glob("*.request.json")) if path.is_file()]


def healthcheck(
    payload: dict,
    *,
    root: Path,
    app_home: Path | None,
    load_config,
    plugin_manager_cls,
    renderer_dependency_selftests,
) -> dict:
    scope, required_dependencies = validation.parse_healthcheck_request(payload)
    layout = ensure_app_layout(module_root_path=root, app_home_path=app_home)
    config = load_config(layout.default_config_path)
    plugin_mgr = plugin_manager_cls(layout.plugins_dir, config)
    try:
        dependencies = []
        overall_healthy = True
        explicit_dependencies = scope == HEALTHCHECK_PIPELINE_RUN_SCOPE and required_dependencies is not None
        timeout_seconds = _healthcheck_timeout_seconds(scope)
        required_names = set(required_dependencies or ())
        for name, kind, required_by_default in _PLUGIN_HEALTHCHECKS:
            if explicit_dependencies and name not in required_names:
                dependencies.append(_dependency_payload(name=name, kind=kind, required=False, healthy=True, detail=_SKIPPED_PIPELINE_RUN_DETAIL))
                continue
            healthy, detail = plugin_mgr.selftest(name, timeout_seconds=timeout_seconds)
            required = True if explicit_dependencies else required_by_default
            dependencies.append(
                _dependency_payload(name=name, kind=kind, required=required, healthy=healthy, detail=detail)
            )
            if required and not healthy:
                overall_healthy = False
        renderer_checks = renderer_dependency_selftests(
            scope=scope,
            required_dependencies=required_dependencies if explicit_dependencies else None,
            timeout_seconds=timeout_seconds,
        )
        dependencies.extend(renderer_checks)
        if any(not bool(item["healthy"]) for item in renderer_checks if item.get("required")):
            overall_healthy = False
    finally:
        plugin_mgr.kill_all()
    return {
        "status": "ok" if overall_healthy else "error",
        "healthy": overall_healthy,
        "message": "" if overall_healthy else "Core-Extraktoren oder Renderer des Optimizers sind nicht verfuegbar.",
        "dependencies": dependencies,
    }


def _healthcheck_timeout_seconds(scope: str) -> int:
    if scope == HEALTHCHECK_PIPELINE_RUN_SCOPE:
        return PIPELINE_RUN_HEALTHCHECK_TIMEOUT_SECONDS
    return DEFAULT_HEALTHCHECK_TIMEOUT_SECONDS


def _dependency_payload(*, name: str, kind: str, required: bool, healthy: bool, detail: str) -> dict[str, object]:
    return {
        "name": name,
        "kind": kind,
        "required": required,
        "healthy": healthy,
        "detail": detail,
    }
