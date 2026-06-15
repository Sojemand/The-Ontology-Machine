"""Path-stable surface for the merged Optimizer subprocess contract."""
from __future__ import annotations

import argparse
from pathlib import Path

import ingestion_layer_file.orchestrator_contract as file_contract

from ..models import atomic_json_write, load_config
from ..paths import module_root
from ..plugin_manager import PluginManager
from ..processor import Processor
from . import adapter, classification_routing, healthcheck_routing, workflow
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


def _optimizer_profile(payload: dict) -> str:
    profile = str(payload.get("optimizer_profile", "")).strip().lower()
    if profile in {"vision", "file"}:
        return profile
    return "vision"


def _extract_document(payload: dict) -> dict:
    if _optimizer_profile(payload) == "file":
        return file_contract._extract_document(payload)
    return workflow.extract_document(
        payload,
        root=ROOT,
        app_home=APP_HOME,
        load_config=load_config,
        plugin_manager_cls=PluginManager,
        processor_cls=Processor,
    )


def _classify_document(payload: dict) -> dict:
    return classification_routing.classify_document(payload, pdf_classify=file_contract._classify_document)


def _healthcheck(_payload: dict) -> dict:
    explicit_profile = str(_payload.get("optimizer_profile", "")).strip().lower()
    if explicit_profile == "file":
        return file_contract._healthcheck(_payload)
    if explicit_profile == "vision":
        return _vision_healthcheck(_payload)
    split = healthcheck_routing.split_payloads(_payload)
    if split is None:
        return _vision_healthcheck(_payload)
    file_payload, vision_payload = split
    if file_payload is None and vision_payload is None:
        return _vision_healthcheck(_payload)
    if file_payload is not None and vision_payload is None:
        return file_contract._healthcheck(file_payload)
    if vision_payload is not None and file_payload is None:
        return _vision_healthcheck(vision_payload)
    return healthcheck_routing.merge_responses(
        file_contract._healthcheck(file_payload),
        _vision_healthcheck(vision_payload),
    )


def _vision_healthcheck(payload: dict) -> dict:
    return workflow.healthcheck(
        payload,
        root=ROOT,
        app_home=APP_HOME,
        load_config=load_config,
        plugin_manager_cls=PluginManager,
    )


def _scan_debug_input(payload: dict) -> dict:
    if _optimizer_profile(payload) == "file":
        return file_contract._scan_debug_input(payload)
    return workflow.scan_debug_input(payload, root=ROOT, app_home=APP_HOME)


def _debug_run(payload: dict) -> dict:
    if _optimizer_profile(payload) == "file":
        return file_contract._debug_run(payload)
    return workflow.debug_run(
        payload,
        root=ROOT,
        app_home=APP_HOME,
        load_config=load_config,
        plugin_manager_cls=PluginManager,
        processor_cls=Processor,
    )


def _dispatch(payload: dict) -> dict:
    action = workflow.require_action(payload)
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
    "_dispatch",
    "_debug_run",
    "_error",
    "_classify_document",
    "_extract_document",
    "_healthcheck",
    "_load_request",
    "_scan_debug_input",
    "_write_response",
    "atomic_json_write",
    "load_config",
    "main",
]
