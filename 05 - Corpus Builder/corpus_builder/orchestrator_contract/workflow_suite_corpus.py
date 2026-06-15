"""Corpus admin, search, stats and export contract handlers."""

from __future__ import annotations

from ..models.types import EmbeddingRuntimeSettings
from ..semantic_release.multi_source_merge_types import path_hash
from ..services import (
    activate_corpus_context,
    apply_semantic_release,
    create_and_activate_new_corpus_db,
    create_empty_corpus_db,
    export_corpus,
    get_stats,
    reset_active_corpus_db,
    search_corpus,
)
from .result_envelope import build_result, kv_artifacts


def handle_activate_corpus_context(command, *, context, activate_corpus_context_fn=activate_corpus_context):
    detail = activate_corpus_context_fn(context, corpus_db_path=command.corpus_db_path)
    semantic = detail.get("semantic_status") if isinstance(detail.get("semantic_status"), dict) else {}
    return build_result(
        headline="Corpus context activated",
        summary_lines=[f"Corpus DB: {detail.get('corpus_db_path') or ''}", f"Active release: {semantic.get('active_release_id') or 'none'}"],
        artifacts=kv_artifacts([("Corpus DB", detail.get("corpus_db_path")), ("Previous Default", detail.get("previous_default_corpus_db_path"))]),
        detail=detail,
    )


def handle_create_empty_corpus_db(command, *, context, create_empty_corpus_db_fn=create_empty_corpus_db):
    detail = create_empty_corpus_db_fn(
        context,
        corpus_db_path=command.corpus_db_path,
        activate_context=command.activate_context,
    )
    response = build_result(
        headline="Empty corpus DB created",
        summary_lines=[f"Corpus DB: {detail.get('corpus_db_path') or ''}", f"Activated context: {bool(detail.get('activated_context'))}"],
        artifacts=kv_artifacts([("Corpus DB", detail.get("corpus_db_path")), ("Previous Default", detail.get("previous_default_corpus_db_path"))]),
        detail=detail,
    )
    corpus_db_path = str(detail.get("corpus_db_path") or "")
    output_refs = {
        "database_path": corpus_db_path,
        "corpus_db_path": corpus_db_path,
        "database_id": f"db:{path_hash(corpus_db_path)}" if corpus_db_path else "",
        "activated_context": bool(detail.get("activated_context")),
    }
    response["output_refs"] = output_refs
    # Prove the concrete created target path without leaking the owner's hash
    # format into the Kernel's current target-identity comparison path.
    response["target_identity_proof"] = {
        "database_path": corpus_db_path,
    }
    response["receipt_fields"] = {
        "owner_module": "05 - Corpus Builder",
        "owner_action": "create_empty_corpus_db",
    }
    response["diagnostics"] = []
    return response


def handle_reset_active_corpus_db(command, *, context, reset_active_corpus_db_fn=reset_active_corpus_db):
    detail = reset_active_corpus_db_fn(
        context,
        corpus_db_path=command.corpus_db_path,
        confirmation_artifact_path=command.confirmation_artifact_path,
    )
    response = build_result(
        headline="Active corpus DB reset",
        summary_lines=[
            f"Corpus DB: {detail.get('corpus_db_path') or ''}",
            f"Semantic Release preserved: {bool(detail.get('semantic_release_preserved'))}",
        ],
        artifacts=kv_artifacts([("Corpus DB", detail.get("corpus_db_path")), ("Confirmation", (detail.get("confirmation") or {}).get("artifact_path"))]),
        detail=detail,
    )
    corpus_db_path = str(detail.get("corpus_db_path") or detail.get("database_path") or "")
    response["output_refs"] = {
        "database_path": corpus_db_path,
        "corpus_db_path": corpus_db_path,
        "semantic_release_preserved": bool(detail.get("semantic_release_preserved")),
        "empty_state_proven": bool(detail.get("empty_state_proven")),
        "active_release_ref": dict(detail.get("active_release_ref") or {}),
        "preserved_release_ref": dict(detail.get("preserved_release_ref") or {}),
        "post_reset_counts": dict(detail.get("post_reset_counts") or {}),
        "cleared_table_counts": dict(detail.get("cleared_table_counts") or {}),
        "physical_compaction": dict(detail.get("physical_compaction") or {}),
        "physical_compaction_performed": bool(detail.get("physical_compaction_performed")),
        "wal_sidecar_cleanup": dict(detail.get("wal_sidecar_cleanup") or {}),
    }
    response["target_identity_proof"] = {
        "database_path": corpus_db_path,
    }
    response["receipt_fields"] = {
        "owner_module": "05 - Corpus Builder",
        "owner_action": "reset_active_corpus_db",
        "confirmation_artifact_path": command.confirmation_artifact_path,
    }
    response["diagnostics"] = []
    return response


def handle_create_and_activate_new_corpus_db(
    command,
    *,
    context,
    create_and_activate_new_corpus_db_fn=create_and_activate_new_corpus_db,
    apply_semantic_release_fn=apply_semantic_release,
):
    detail = create_and_activate_new_corpus_db_fn(
        context,
        release_path=command.release_path,
        confirmation_artifact_path=command.confirmation_artifact_path,
        activate_release_fn=apply_semantic_release_fn,
    )
    return build_result(
        headline="New corpus DB created and release activated",
        summary_lines=[
            f"Release: {detail.get('release_id') or ''}",
            f"Version: {detail.get('release_version') or ''}",
            f"Taxonomy locale: {detail.get('taxonomy_locale') or ''}",
        ],
        artifacts=kv_artifacts(
            [
                ("Corpus Root", detail.get("corpus_root")),
                ("Corpus DB", detail.get("corpus_db_path")),
                ("Detached Previous DB", detail.get("previous_default_corpus_db_path")),
            ]
        ),
        detail=detail,
    )


def handle_search(command, *, context, search_corpus_fn=search_corpus):
    runtime_settings = EmbeddingRuntimeSettings(model=command.runtime_model) if command.runtime_model else None
    results = search_corpus_fn(
        context,
        corpus_db_path=command.corpus_db_path,
        query=command.query,
        mode=command.mode,
        limit=command.limit,
        runtime_settings=runtime_settings,
    )
    rows = [
        {
            "document_id": item.document_id,
            "title": item.title or "",
            "score": item.score,
            "source": item.source,
            "snippet": item.snippet or "",
        }
        for item in results
    ]
    return build_result(
        headline="Search completed",
        summary_lines=[f"Mode: {command.mode}", f"Hits: {len(rows)}"],
        artifacts=kv_artifacts([("Corpus DB", command.corpus_db_path), ("Query", command.query)]),
        table={"columns": ["document_id", "title", "score", "source", "snippet"], "rows": rows},
        detail={"query": command.query, "mode": command.mode, "results": rows},
    )


def handle_stats(command, *, context, get_stats_fn=get_stats):
    detail = get_stats_fn(context, corpus_db_path=command.corpus_db_path)
    return build_result(
        headline="Corpus stats loaded",
        summary_lines=[f"Documents: {detail.get('document_count', 0)}"],
        artifacts=kv_artifacts([("Corpus DB", command.corpus_db_path)]),
        detail=detail,
    )


def handle_export(command, *, context, export_corpus_fn=export_corpus):
    detail = export_corpus_fn(
        context,
        corpus_db_path=command.corpus_db_path,
        output_path=command.output_path,
        fmt=command.fmt,
        include_archived=command.include_archived,
    )
    return build_result(
        headline="Corpus export completed",
        summary_lines=[f"Format: {detail.format}", f"Documents: {detail.document_count}"],
        artifacts=kv_artifacts([("Corpus DB", command.corpus_db_path), ("Output Path", detail.path)]),
        detail={"path": detail.path, "format": detail.format, "document_count": detail.document_count},
    )
