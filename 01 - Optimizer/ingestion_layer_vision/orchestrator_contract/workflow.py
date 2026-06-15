"""Workflow helpers for optimizer vision-profile contract actions."""
from __future__ import annotations

from contextlib import contextmanager
import os
from pathlib import Path

from optimizer_ocr.request_capture import REQUEST_DIR_ENV

from ..paths import ensure_app_layout
from ..processor import policy as processor_policy
from ..runtime_policy import load_runtime_policy_state
from . import adapter, debug_errors, debug_processing, healthcheck_workflow, validation


def error_response(message: str) -> dict:
    return {"status": "error", "error": message}


def require_action(payload: dict) -> str:
    return validation.require_action(payload)


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
        runtime_policy_path = validation.require_runtime_policy_path(payload)
        runtime_policy_state = load_runtime_policy_state(runtime_policy_path)
    except FileNotFoundError as exc:
        return error_response(str(exc))
    except ValueError as exc:
        return error_response(str(exc))

    layout = ensure_app_layout(module_root_path=root, app_home_path=app_home)
    config = load_config(layout.default_config_path)
    plugin_mgr = plugin_manager_cls(layout.plugins_dir, config)
    try:
        processor = processor_cls(
            config,
            plugin_mgr,
            runtime_policy_state=runtime_policy_state,
        )
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
    page_raw_paths: list[str] = []
    if len(extracts) > 1:
        candidate_paths = processor_policy.page_raw_output_paths(raw_output_path, len(extracts) - 1)
        for page_extract, page_path in zip(extracts[1:], candidate_paths, strict=False):
            page_number = int(getattr(page_extract, "page_number", 0) or 0)
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
) -> dict:
    return healthcheck_workflow.run(
        payload,
        root=root,
        app_home=app_home,
        load_config=load_config,
        plugin_manager_cls=plugin_manager_cls,
    )


def scan_debug_input(
    payload: dict,
    *,
    root: Path,
    app_home: Path | None,
) -> dict:
    return debug_errors.run_debug_action(
        payload,
        lambda: debug_processing.scan_debug_input(payload, root=root, app_home=app_home),
        summary="Scan-Debug fehlgeschlagen",
    )


def debug_run(
    payload: dict,
    *,
    root: Path,
    app_home: Path | None,
    load_config,
    plugin_manager_cls,
    processor_cls,
) -> dict:
    return debug_errors.run_debug_action(
        payload,
        lambda: debug_processing.debug_run(
            payload,
            root=root,
            app_home=app_home,
            load_config=load_config,
            plugin_manager_cls=plugin_manager_cls,
            processor_cls=processor_cls,
        ),
        summary="Debuglauf fehlgeschlagen",
    )
