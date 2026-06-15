"""Path-stable workflow surface for the Corpus Builder subprocess contract."""

from __future__ import annotations

from ..context import ModuleContext
from ..models.types import EmbeddingRequest
from ..services import (
    apply_semantic_release,
    build_load_bundle,
    generate_embeddings as run_embedding_generation,
    load_batch,
    resolve_existing_corpus_db_path,
)
from .types import (
    ACTIVATE_SEMANTIC_RELEASE_ACTION,
    GENERATE_EMBEDDINGS_ACTION,
    HEALTHCHECK_ACTION,
    LOAD_DOCUMENT_ACTION,
    READ_ACTIVE_SEMANTIC_RELEASE_ACTION,
    ActivateSemanticReleaseCommand,
    GenerateEmbeddingsCommand,
    LoadDocumentCommand,
)
from .workflow_dispatch import dispatch as _dispatch
from .workflow_healthcheck import healthcheck
from .workflow_suite import handle_read_active_semantic_release


def error_response(message: str) -> dict:
    return {"status": "error", "reason": message}


def load_document(command: LoadDocumentCommand, *, context: ModuleContext) -> dict:
    request = build_load_bundle(
        context,
        normalized_path=command.normalized_path,
        structured_path=command.structured_path,
        validation_path=command.validation_path,
        raw_path=command.raw_path,
        corpus_db_path=command.corpus_db_path,
    )
    result = load_batch(
        context,
        [request],
        persist_page_images_in_db=command.persist_page_images_in_db,
        page_images_dir=command.page_images_dir,
    )
    item = result.results[0] if result.results else None
    if item is None:
        return error_response("Kein Load-Request verarbeitet.")
    return {"status": item.status, "reason": str(item.reason or "")}


def activate_semantic_release(command: ActivateSemanticReleaseCommand, *, context: ModuleContext) -> dict:
    corpus_db_path = (
        resolve_existing_corpus_db_path(context, command.corpus_db_path)
        if command.corpus_db_path
        else None
    )
    applied = apply_semantic_release(
        context,
        release_path=command.release_path,
        corpus_db_path=corpus_db_path,
        confirmation_artifact_path=command.confirmation_artifact_path,
        write_global_mirrors=command.write_global_mirrors,
    )
    return {
        "status": str(applied.get("status") or "applied"),
        "reason": "",
        "release_id": str(applied.get("release_id") or ""),
        "release_version": str(applied.get("release_version") or ""),
        "active_snapshot_id": str(applied.get("active_snapshot_id") or ""),
        "stale_documents": int(applied.get("stale_documents") or 0),
        "backfill_started": bool(applied.get("backfill_started")),
        "backfill_processed_count": int(applied.get("backfill_processed_count") or 0),
        "global_mirrors_written": bool(applied.get("global_mirrors_written", True)),
        "target_identity_proof": {
            "database_path": str(corpus_db_path or ""),
            "release_fingerprint": str(applied.get("fingerprint") or ""),
        },
    }


def generate_embeddings(command: GenerateEmbeddingsCommand, *, context: ModuleContext) -> dict:
    result = run_embedding_generation(
        context,
        EmbeddingRequest(corpus_db_path=command.corpus_db_path, runtime_settings=command.runtime_settings),
    )
    return {"status": result.status, "count": result.count, "reason": str(result.reason or "")}


def dispatch(payload: dict, *, context: ModuleContext, **parsers) -> dict:
    body = parsers["request_body_fn"](payload) if "request_body_fn" in parsers else payload
    action = parsers["require_action_fn"](payload)
    if action == LOAD_DOCUMENT_ACTION:
        return load_document(parsers["parse_load_document_command_fn"](body), context=context)
    if action == ACTIVATE_SEMANTIC_RELEASE_ACTION:
        return activate_semantic_release(parsers["parse_activate_semantic_release_command_fn"](body), context=context)
    if action == GENERATE_EMBEDDINGS_ACTION:
        return generate_embeddings(parsers["parse_generate_embeddings_command_fn"](body), context=context)
    if action == HEALTHCHECK_ACTION:
        return healthcheck(parsers["parse_healthcheck_command_fn"](body), context=context)
    if action == READ_ACTIVE_SEMANTIC_RELEASE_ACTION:
        return handle_read_active_semantic_release(
            parsers["parse_read_active_semantic_release_command_fn"](body),
            context=context,
        )
    return _dispatch(body, context=context, **parsers)


__all__ = [
    "activate_semantic_release",
    "apply_semantic_release",
    "build_load_bundle",
    "dispatch",
    "error_response",
    "generate_embeddings",
    "healthcheck",
    "handle_read_active_semantic_release",
    "load_batch",
    "load_document",
    "resolve_existing_corpus_db_path",
]
