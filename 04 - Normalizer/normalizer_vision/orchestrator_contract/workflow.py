"""Workflow helpers for the normalizer subprocess contract."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from ..models import FIXED_API_REASONING_EFFORT, NormalizerRuntimeSettings
from ..models.config import load_config
from ..normalizer import DocumentNormalizer
from ..providers import create_provider, sanitize_secret_text
from . import debug_workflow
from .types import (
    BUILD_PROJECTION_CATALOG_ACTION,
    BUILD_RUNTIME_SEMANTIC_ASSETS_ACTION,
    CREATE_ZERO_SHOT_WORKING_RELEASE_ACTION,
    DEBUG_RUN_ACTION,
    EXPORT_DEFAULT_BLUEPRINT_RELEASE_ACTION,
    HEALTHCHECK_ACTION,
    LIST_DEFAULT_BLUEPRINTS_ACTION,
    PUBLISH_SEMANTIC_RELEASE_ACTION,
    HealthcheckCommand,
    NormalizeDocumentCommand,
    RuntimeSettings,
)
from .workflow_blueprints import (
    create_zero_shot_working_release_response,
    export_default_blueprint_release_response,
    list_default_blueprints_response,
)
from .workflow_errors import error_response
from .workflow_release_actions import (
    build_projection_catalog_response,
    build_runtime_semantic_assets_response,
    publish_semantic_release_response,
)


def normalize_document(command: NormalizeDocumentCommand, *, root: Path) -> dict:
    try:
        normalizer = DocumentNormalizer.from_project(
            root,
            runtime_settings=_runtime_settings(command.runtime_settings),
            semantic_release=command.release,
        )
        result = normalizer.normalize(
            command.structured_path,
            command.normalized_output_path,
            request_output_path=command.request_output_path,
        )
    except Exception as exc:
        return error_response(str(exc))
    return {
        "status": result.status,
        "output_path": result.output_path,
        "request_path": str(command.request_output_path) if command.request_output_path and command.request_output_path.exists() else "",
        "needs_review": bool(result.needs_review),
        "message": result.message,
        "review_reason": result.review_reason,
        "duration_ms": result.duration_ms,
    }


def healthcheck(command: HealthcheckCommand, *, root: Path) -> dict:
    try:
        runtime_settings = _runtime_settings(command.runtime_settings)
        project_config = load_config(root)
        provider = create_provider(project_config.build_execution_config(runtime_settings))
        provider.generate(
            _healthcheck_messages(),
            schema=None,
            max_output_tokens=runtime_settings.max_output_tokens,
            thinking_effort=FIXED_API_REASONING_EFFORT,
        )
        detail = (
            f"{provider.provider_name} "
            f"({runtime_settings.model}, max_output_tokens={runtime_settings.max_output_tokens}, reasoning={FIXED_API_REASONING_EFFORT})"
        )
    except Exception as exc:
        return _dependency_error(detail=sanitize_secret_text(str(exc)))
    return {"status": "OK", "healthy": True, "message": "", "dependencies": [_dependency_payload(healthy=True, detail=detail)]}


def dispatch(
    payload: dict,
    *,
    root: Path,
    require_action_fn,
    parse_normalize_document_command_fn,
    parse_healthcheck_command_fn,
    parse_build_runtime_semantic_assets_command_fn,
    parse_publish_semantic_release_command_fn,
    parse_list_default_blueprints_command_fn,
    parse_export_default_blueprint_release_command_fn,
    parse_create_zero_shot_working_release_command_fn,
    parse_debug_run_command_fn,
) -> dict:
    body = payload.get("request_payload") if payload.get("schema_version") == "adapter.call_request.v1" else payload
    if not isinstance(body, dict):
        body = payload
    action = require_action_fn(body)
    if action == BUILD_PROJECTION_CATALOG_ACTION:
        return build_projection_catalog_response(root=root)
    if action == BUILD_RUNTIME_SEMANTIC_ASSETS_ACTION:
        return build_runtime_semantic_assets_response(parse_build_runtime_semantic_assets_command_fn(body))
    if action == PUBLISH_SEMANTIC_RELEASE_ACTION:
        return publish_semantic_release_response(parse_publish_semantic_release_command_fn(body), root=root)
    if action == LIST_DEFAULT_BLUEPRINTS_ACTION:
        parse_list_default_blueprints_command_fn(body)
        return list_default_blueprints_response(root=root)
    if action == EXPORT_DEFAULT_BLUEPRINT_RELEASE_ACTION:
        return export_default_blueprint_release_response(parse_export_default_blueprint_release_command_fn(body), root=root)
    if action == CREATE_ZERO_SHOT_WORKING_RELEASE_ACTION:
        return create_zero_shot_working_release_response(parse_create_zero_shot_working_release_command_fn(body), root=root)
    if action == HEALTHCHECK_ACTION:
        return healthcheck(parse_healthcheck_command_fn(body), root=root)
    if action == DEBUG_RUN_ACTION:
        return debug_workflow.run_debug(body, root=root, parse_debug_run_command_fn=parse_debug_run_command_fn)
    return normalize_document(parse_normalize_document_command_fn(body), root=root)


def _dependency_error(*, detail: str) -> dict:
    return {
        "status": "ERROR",
        "healthy": False,
        "message": "Normalizer-Provider nicht bereit.",
        "dependencies": [_dependency_payload(healthy=False, detail=detail)],
    }


def _dependency_payload(*, healthy: bool, detail: str) -> dict[str, Any]:
    return {
        "name": "llm_provider",
        "kind": "service",
        "required": True,
        "healthy": healthy,
        "detail": sanitize_secret_text(detail),
    }


def _runtime_settings(settings: RuntimeSettings) -> NormalizerRuntimeSettings:
    return NormalizerRuntimeSettings(model=settings.model, max_output_tokens=settings.max_output_tokens)


def _healthcheck_messages() -> list[dict[str, str]]:
    return [
        {"role": "system", "content": "Return valid json only. Return the requested payload exactly. No prose."},
        {"role": "user", "content": 'Return exactly this json object: {"accepted":true}'},
    ]
