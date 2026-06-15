"""Path-stable surface for the Optimizer subprocess contract."""
from __future__ import annotations

import argparse
from pathlib import Path

from ..extractors.pdf_text import extract as extract_pdf_text
from ..models import atomic_json_write, load_config
from ..paths import module_root
from ..plugin_manager import PluginManager
from ..processor import Processor
from ..rendering import renderer_dependency_selftests
from . import adapter, debug_processing, debug_support, validation, workflow
from .types import (
    CLASSIFY_DOCUMENT_ACTION,
    DEBUG_RUN_ACTION,
    EXTRACT_DOCUMENT_ACTION,
    HEALTHCHECK_ACTION,
    SCAN_DEBUG_INPUT_ACTION,
)

ROOT = module_root()
APP_HOME: Path | None = None


def _load_request(path: Path) -> dict:
    return adapter.load_request(path)


def _write_response(path: Path, payload: dict) -> None:
    adapter.write_response(path, payload, atomic_write=atomic_json_write)


def _error(message: str) -> dict:
    return workflow.error_response(message)


def normalize_action(payload: dict) -> str:
    return workflow.normalize_action(payload)


def _extract_document(payload: dict) -> dict:
    return workflow.extract_document(
        payload,
        root=ROOT,
        app_home=APP_HOME,
        load_config=load_config,
        plugin_manager_cls=PluginManager,
        processor_cls=Processor,
    )


def _classify_document(payload: dict) -> dict:
    return workflow.classify_document(payload, pdf_extract=extract_pdf_text)


def _healthcheck(payload: dict) -> dict:
    return workflow.healthcheck(
        payload,
        root=ROOT,
        app_home=APP_HOME,
        load_config=load_config,
        plugin_manager_cls=PluginManager,
        renderer_dependency_selftests=renderer_dependency_selftests,
    )


def _scan_debug_input(payload: dict) -> dict:
    return _run_debug_action(
        payload,
        lambda: debug_processing.scan_debug_input(payload, root=ROOT, app_home=APP_HOME),
        summary="Scan-Debug fehlgeschlagen",
    )


def _debug_run(payload: dict) -> dict:
    return _run_debug_action(
        payload,
        lambda: debug_processing.debug_run(
            payload,
            root=ROOT,
            app_home=APP_HOME,
            load_config=load_config,
            plugin_manager_cls=PluginManager,
            processor_cls=Processor,
        ),
        summary="Debuglauf fehlgeschlagen",
    )


def _dispatch(payload: dict) -> dict:
    action = validation.require_action(payload)
    if action == CLASSIFY_DOCUMENT_ACTION:
        return _classify_document(payload)
    if action == EXTRACT_DOCUMENT_ACTION:
        return _extract_document(payload)
    if action == HEALTHCHECK_ACTION:
        return _healthcheck(payload)
    if action == SCAN_DEBUG_INPUT_ACTION:
        return _scan_debug_input(payload)
    if action == DEBUG_RUN_ACTION:
        return _debug_run(payload)
    return _error(f"Unbekannte Aktion: {action}")


def _run_debug_action(payload: dict, action, *, summary: str) -> dict:
    try:
        return action()
    except Exception as exc:
        return _debug_error(payload, summary=summary, message=str(exc))


def _debug_error(payload: dict, *, summary: str, message: str) -> dict:
    try:
        session_root = validation.require_session_root(payload)
    except Exception:
        return _error(message)
    if debug_support.cancel_requested(session_root):
        debug_support.write_snapshot(session_root, status="cancelled", detail=summary)
        return debug_support.write_result(session_root, {"status": "cancelled", "summary": summary})
    debug_support.append_log(session_root, f"[ERROR] {message}")
    debug_support.write_snapshot(session_root, status="error", detail=message)
    return debug_support.write_result(session_root, {"status": "error", "summary": summary, "error": message})


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--request", required=True)
    parser.add_argument("--response", required=True)
    args = parser.parse_args(argv)
    response_path = Path(args.response)
    try:
        response = _dispatch(_load_request(Path(args.request)))
    except Exception as exc:  # pragma: no cover - defensive
        response = _error(str(exc))
    _write_response(response_path, response)
    return 0


__all__ = [
    "APP_HOME",
    "CLASSIFY_DOCUMENT_ACTION",
    "DEBUG_RUN_ACTION",
    "EXTRACT_DOCUMENT_ACTION",
    "HEALTHCHECK_ACTION",
    "PluginManager",
    "Processor",
    "ROOT",
    "_classify_document",
    "_dispatch",
    "_debug_run",
    "_error",
    "_extract_document",
    "_healthcheck",
    "_load_request",
    "_scan_debug_input",
    "_write_response",
    "atomic_json_write",
    "load_config",
    "main",
    "normalize_action",
    "renderer_dependency_selftests",
]

