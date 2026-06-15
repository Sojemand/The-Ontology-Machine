"""Path-stable surface for the orchestrator subprocess contract."""

from __future__ import annotations

import argparse
from pathlib import Path

from ..bootstrap import ORCHESTRATOR_ROOT, ensure_startup_prerequisites
from ..main.workflow import reset_logging_files as _reset_logging_files
from ..models import UiState
from ..pipeline_batches import create_pipeline_batch_manifest, finalize_pipeline_batch_manifest
from ..pipeline import OrchestratorEngine
from ..state import load_ui_state, save_ui_state
from ..workspace_domain import create_artifact_tree, validate_artifact_tree
from . import adapter, kernel_llm, validation, workflow
from .types import (
    ACTIVATE_CORPUS_CONTEXT_ACTION,
    CREATE_ARTIFACT_TREE_ACTION,
    CREATE_PIPELINE_BATCH_MANIFEST_ACTION,
    EMBEDDINGS_ACTION,
    FINALIZE_PIPELINE_BATCH_MANIFEST_ACTION,
    HEALTHCHECK_ACTION,
    INSPECT_SOURCE_DOCUMENT_SAMPLE_ACTION,
    KERNEL_LLM_GENERATE_ACTION,
    KERNEL_LLM_RUNTIME_PROFILE_ACTION,
    RESET_ACTION,
    RESET_PIPELINE_LOGS_ACTION,
    RUN_ACTION,
    VALIDATE_ARTIFACT_TREE_ACTION,
)


def _load_request(path: Path) -> dict:
    return adapter.load_request(path)


def _write_response(path: Path, payload: dict) -> None:
    adapter.write_response(path, payload)


def _error(message: str) -> dict:
    return workflow.error_response(message)


def _run(payload: dict, *, owner_result: bool = False) -> dict:
    return workflow.run_action(
        validation.ui_state_payload(payload),
        engine_cls=OrchestratorEngine,
        ui_state_cls=UiState,
        snapshot_path=validation.optional_snapshot_path(payload),
        request_payload=payload,
        owner_result=owner_result,
    )


def _reset(payload: dict, *, owner_result: bool = False) -> dict:
    return workflow.reset_action(
        validation.ui_state_payload(payload),
        engine_cls=OrchestratorEngine,
        ui_state_cls=UiState,
        request_payload=payload,
        owner_result=owner_result,
    )


def _reset_pipeline_logs(payload: dict) -> dict:
    return workflow.reset_pipeline_logs_action(
        validation.ui_state_payload(payload),
        engine_cls=OrchestratorEngine,
        ui_state_cls=UiState,
        reset_logging_files=_reset_logging_files,
    )


def _healthcheck(_payload: dict) -> dict:
    return workflow.healthcheck(
        ensure_startup_prerequisites=ensure_startup_prerequisites,
    )


def _embeddings(payload: dict, *, owner_result: bool = False) -> dict:
    return workflow.embeddings_action(
        validation.ui_state_payload(payload),
        engine_cls=OrchestratorEngine,
        ui_state_cls=UiState,
        owner_result=owner_result,
    )


def _activate_corpus_context(payload: dict) -> dict:
    return workflow.activate_corpus_context_action(
        validation.activate_corpus_context_payload(payload),
        root=ORCHESTRATOR_ROOT,
        ui_state_cls=UiState,
        load_ui_state=load_ui_state,
        save_ui_state=save_ui_state,
    )


def _inspect_source_document_sample(payload: dict) -> dict:
    return workflow.inspect_source_document_sample_action(
        validation.inspect_source_document_sample_payload(payload),
        root=ORCHESTRATOR_ROOT,
    )


def _kernel_llm_runtime_profile(_payload: dict) -> dict:
    return kernel_llm.runtime_profile_action(root=ORCHESTRATOR_ROOT)


def _kernel_llm_generate(payload: dict) -> dict:
    return kernel_llm.generate_action(
        validation.kernel_llm_generate_payload(payload),
        root=ORCHESTRATOR_ROOT,
    )


def _dispatch(payload: dict) -> dict:
    owner_call = payload.get("schema_version") == "adapter.call_request.v1"
    body = validation.request_body(payload)
    try:
        action = validation.require_action(payload)
    except ValueError as exc:
        return _error(str(exc))
    if action == RUN_ACTION:
        return _run(body, owner_result=owner_call)
    if action == RESET_ACTION:
        return _reset(body, owner_result=owner_call)
    if action == RESET_PIPELINE_LOGS_ACTION:
        return _reset_pipeline_logs(body)
    if action == EMBEDDINGS_ACTION:
        return _embeddings(body, owner_result=owner_call)
    if action == ACTIVATE_CORPUS_CONTEXT_ACTION:
        return _activate_corpus_context(body)
    if action == INSPECT_SOURCE_DOCUMENT_SAMPLE_ACTION:
        return _inspect_source_document_sample(body)
    if action == KERNEL_LLM_RUNTIME_PROFILE_ACTION:
        return _kernel_llm_runtime_profile(body)
    if action == KERNEL_LLM_GENERATE_ACTION:
        return _kernel_llm_generate(body)
    if action == HEALTHCHECK_ACTION:
        return _healthcheck(body)
    if action == CREATE_ARTIFACT_TREE_ACTION:
        return create_artifact_tree(body)
    if action == VALIDATE_ARTIFACT_TREE_ACTION:
        return validate_artifact_tree(body)
    if action == CREATE_PIPELINE_BATCH_MANIFEST_ACTION:
        return create_pipeline_batch_manifest(body)
    if action == FINALIZE_PIPELINE_BATCH_MANIFEST_ACTION:
        return finalize_pipeline_batch_manifest(body)
    return _error(f"Unknown action: {action}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--request", required=True)
    parser.add_argument("--response", required=True)
    args = parser.parse_args(argv)
    try:
        response = _dispatch(_load_request(Path(args.request)))
    except Exception as exc:  # pragma: no cover - defensive
        response = _error(str(exc))
    _write_response(Path(args.response), response)
    return 0


__all__ = [
    "OrchestratorEngine",
    "ACTIVATE_CORPUS_CONTEXT_ACTION",
    "EMBEDDINGS_ACTION",
    "INSPECT_SOURCE_DOCUMENT_SAMPLE_ACTION",
    "KERNEL_LLM_GENERATE_ACTION",
    "KERNEL_LLM_RUNTIME_PROFILE_ACTION",
    "RUN_ACTION",
    "RESET_ACTION",
    "RESET_PIPELINE_LOGS_ACTION",
    "HEALTHCHECK_ACTION",
    "UiState",
    "_embeddings",
    "_activate_corpus_context",
    "_inspect_source_document_sample",
    "_kernel_llm_generate",
    "_kernel_llm_runtime_profile",
    "_dispatch",
    "_error",
    "_healthcheck",
    "_load_request",
    "_reset",
    "_reset_pipeline_logs",
    "_run",
    "_write_response",
    "ensure_startup_prerequisites",
    "main",
]
