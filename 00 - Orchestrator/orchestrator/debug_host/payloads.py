"""Payload builders and result aggregation for debug-host sessions."""

from __future__ import annotations

import json
from collections.abc import Iterable
from typing import Any

from .. import policy_store
from ..integrations.workflow_helpers import required_runtime_settings_for
from . import polling
from .types import DebugResult, DebugSession

_INTERPRETER_DEBUG_MODULES = frozenset({"interpreter"})
_NORMALIZER_DEBUG_MODULES = frozenset({"normalizer"})
_INTERPRETER_BATCH_OUTPUT_DIR = "structured_output"


def build_module_payload(session: DebugSession, *, modules: Any = None) -> dict[str, Any]:
    step = session.active_step
    if step is None:
        return {}
    if step.module_key in _INTERPRETER_DEBUG_MODULES and step.action == "debug_run":
        return _interpreter_payload(session, modules, module_key=step.module_key)
    return _default_payload(session, modules=modules)


def aggregate_result(results: Iterable[DebugResult]) -> DebugResult | None:
    items = list(results)
    if not items:
        return None
    final = items[-1]
    return DebugResult(
        status=final.status,
        summary=final.summary,
        artifacts=_merge_mapping(items, key="artifacts"),
        error=final.error,
        metrics=dict(final.metrics),
        outputs=_merge_mapping(items, key="outputs"),
    )


def _default_payload(session: DebugSession, *, modules: Any = None) -> dict[str, Any]:
    controls = set(session.descriptor.controls)
    payload: dict[str, Any] = {
        "action": session.active_step.action if session.active_step is not None else "",
        "session_root": str(session.session_root),
        "input_root": str(session.request.input_root),
        "mode": session.request.mode,
    }
    if "filters" in controls:
        payload["filters"] = dict(session.request.options.get("filters", {}))
    if payload["action"] == "scan_debug_input":
        if "hash_tools" in controls:
            payload["hash_tools"] = dict(session.request.options.get("hash_tools", {}))
        return payload
    payload["output_root"] = str(session.output_root)
    if session.active_step is not None and session.active_step.module_key == "optimizer":
        payload["optimizer_profile"] = _source_profile(session)
    if "worker_count" in controls:
        payload["worker_count"] = int(session.request.options.get("worker_count", 1) or 1)
    if (
        session.active_step is not None
        and session.active_step.module_key in _NORMALIZER_DEBUG_MODULES
        and session.active_step.action == "debug_run"
    ):
        payload["runtime_settings"] = required_runtime_settings_for(modules, session.active_step.module_key)
    options = _payload_options(session, controls)
    if options:
        payload["options"] = options
    if session.request.mode == "single":
        if session.request.resolved_source_path is None:
            raise ValueError("single debug requires source_path.")
        payload["source_path"] = str(session.request.resolved_source_path)
        if session.request.logical_source_path:
            payload["logical_source_path"] = session.request.logical_source_path
    return payload


def _interpreter_payload(session: DebugSession, modules: Any, *, module_key: str) -> dict[str, Any]:
    prior = session.completed_results[-1] if session.completed_results else None
    if prior is None:
        raise ValueError(f"Missing prerequisites for {module_key}:debug_run.")
    request_items = prior.outputs.get("interpreter_request", [])
    if not request_items:
        raise ValueError("interpreter.request.json is missing after Request Enrichment.")
    runtime_settings = required_runtime_settings_for(modules, module_key)
    interpreter_profile = _request_profile(session, request_items)
    if session.request.mode == "batch":
        return {
            "action": "debug_run",
            "mode": "batch",
            "session_root": str(session.session_root),
            "input_root": str(session.output_root / policy_store.publication_name("requests")),
            "output_root": str(session.output_root / _INTERPRETER_BATCH_OUTPUT_DIR),
            "num_workers": 1,
            "interpreter_profile": interpreter_profile,
            "runtime_settings": runtime_settings,
        }
    if len(request_items) != 1:
        raise ValueError("single debug expects exactly one interpreter request.")
    request_path = polling.resolve_output_path(session.session_root, request_items[0])
    return {
        "action": "debug_run",
        "mode": "single",
        "session_root": str(session.session_root),
        "request_path": str(request_path),
        "output_root": str(session.output_root),
        "interpreter_profile": interpreter_profile,
        "runtime_settings": runtime_settings,
    }


def _source_profile(session: DebugSession) -> str:
    candidate = session.request.resolved_source_path
    if candidate is None and session.request.logical_source_path:
        candidate = polling.resolve_output_path(session.session_root, session.request.logical_source_path)
    suffix = str(getattr(candidate, "suffix", "") or "").strip().lower()
    if suffix in policy_store.file_suffixes():
        return "file"
    return "vision"


def _request_profile(session: DebugSession, request_items: list[str]) -> str:
    if not request_items:
        return "vision"
    request_path = polling.resolve_output_path(session.session_root, request_items[0])
    try:
        payload = json.loads(request_path.read_text(encoding="utf-8"))
    except Exception:
        return "vision"
    context = payload.get("context", {}) if isinstance(payload, dict) else {}
    profile = str(context.get("interpreter_profile", "")).strip().lower() if isinstance(context, dict) else ""
    return profile if profile in {"vision", "file"} else "vision"


def _merge_mapping(results: list[DebugResult], *, key: str) -> dict[str, list[str]]:
    merged: dict[str, list[str]] = {}
    for result in results:
        mapping = getattr(result, key)
        for name, values in mapping.items():
            bucket = merged.setdefault(str(name), [])
            for value in values:
                text = str(value).strip()
                if text and text not in bucket:
                    bucket.append(text)
    return merged


def _payload_options(session: DebugSession, controls: set[str]) -> dict[str, Any]:
    options: dict[str, Any] = {}
    if "raw_evidence" in controls:
        options["raw_evidence"] = dict(session.request.options.get("raw_evidence", {}))
    if "check_toggles" in controls:
        options["check_toggles"] = dict(session.request.options.get("check_toggles", {}))
    if "persist_page_images" in controls:
        options["persist_page_images_in_db"] = bool(session.request.options.get("persist_page_images_in_db"))
    return options
