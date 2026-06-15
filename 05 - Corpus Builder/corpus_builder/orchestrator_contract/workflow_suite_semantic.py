"""Semantic release contract handlers."""

from __future__ import annotations

from ..services import (
    activation_preflight,
    audit_semantics,
    backfill_semantics,
    load_semantic_release,
    merge_corpus_databases,
    merge_preflight,
    read_active_semantic_release,
    semantic_status,
)
from .result_envelope import build_result, kv_artifacts


def handle_semantic_status(command, *, context, semantic_status_fn=semantic_status):
    detail = semantic_status_fn(context, corpus_db_path=command.corpus_db_path)
    return build_result(
        headline="Semantic status loaded",
        summary_lines=[f"Active release: {detail.get('active_release_id') or 'none'}", f"Pending release change: {detail.get('pending_release_change')}"],
        artifacts=kv_artifacts(
            [
                ("Corpus DB", command.corpus_db_path),
                ("Active Release Path", detail.get("active_release_path")),
                ("Published Release Path", detail.get("published_release_path")),
            ]
        ),
        detail=detail,
    )


def handle_read_active_semantic_release(command, *, context, read_active_semantic_release_fn=read_active_semantic_release):
    detail = read_active_semantic_release_fn(context, corpus_db_path=command.corpus_db_path)
    return build_result(
        headline="Active semantic release loaded",
        summary_lines=[f"Release: {detail.get('release_id') or ''}", f"Version: {detail.get('release_version') or ''}"],
        artifacts=kv_artifacts([("Corpus DB", command.corpus_db_path), ("Active Release Path", detail.get("release_path"))]),
        detail=detail,
    )


def handle_load_semantic_release(command, *, context, load_semantic_release_fn=load_semantic_release):
    detail = load_semantic_release_fn(
        context,
        release_path=command.release_path,
        corpus_db_path=command.corpus_db_path,
        write_global_mirrors=command.write_global_mirrors,
    )
    return build_result(
        headline="Semantic release staged",
        summary_lines=[f"Release: {detail.get('release_id') or ''}", f"Version: {detail.get('release_version') or ''}"],
        artifacts=kv_artifacts([("Source Path", detail.get("source_path")), ("Published Path", detail.get("published_release_path") or detail.get("release_path")), ("Report Path", detail.get("report_path"))]),
        detail=detail,
    )


def handle_activation_preflight(command, *, context, activation_preflight_fn=activation_preflight):
    detail = activation_preflight_fn(context, release_path=command.release_path, corpus_db_path=command.corpus_db_path)
    return build_result(
        headline="Semantic activation preflight completed",
        summary_lines=[
            f"Current snapshot: {((detail.get('current_snapshot') or {}).get('snapshot_id') or 'none')}",
            f"Next snapshot: {((detail.get('next_snapshot') or {}).get('snapshot_id') or 'none')}",
        ],
        artifacts=kv_artifacts(
            [
                ("Corpus DB", command.corpus_db_path),
                ("Release Path", command.release_path),
                ("Recommended Confirmation", detail.get("recommended_confirmation_filename")),
            ]
        ),
        detail=detail,
    )


def handle_semantic_audit(command, *, context, audit_semantics_fn=audit_semantics):
    detail = audit_semantics_fn(context, corpus_db_path=command.corpus_db_path)
    status = detail.get("status") if isinstance(detail.get("status"), dict) else {}
    return build_result(
        headline="Semantic audit completed",
        summary_lines=[f"Unknown projection docs: {status.get('unknown_projection_documents', 0)}", f"Audit issues: {status.get('audit_issue_count', 0)}"],
        artifacts=kv_artifacts([("Release Path", detail.get("release_path")), ("Report Path", detail.get("report_path"))]),
        detail=detail,
    )


def handle_backfill_stale(command, *, context, backfill_semantics_fn=backfill_semantics):
    detail = backfill_semantics_fn(
        context,
        corpus_db_path=command.corpus_db_path,
        document_ids=list(command.document_ids),
        stale_only=command.stale_only,
        limit=command.limit,
    )
    return build_result(
        headline="Semantic backfill completed",
        summary_lines=[f"Processed: {detail.get('processed_count', 0)}", f"Errors: {detail.get('error_count', 0)}"],
        artifacts=kv_artifacts([("Run ID", detail.get("run_id")), ("Release Version", detail.get("release_version"))]),
        detail=detail,
    )


def handle_merge_preflight(command, *, context, merge_preflight_fn=merge_preflight):
    detail = merge_preflight_fn(context, source_db_path=command.source_db_path, target_db_path=command.target_db_path)
    state = "blocked" if detail.get("blocked") else "ready" if detail.get("merge_ready") else "pending_confirmation"
    return build_result(
        headline="Corpus merge preflight completed",
        summary_lines=[
            f"Master line: {detail.get('master_taxonomy_release_id') or 'unresolved'}",
            f"Merge state: {state}",
            f"Snapshot risk confirmation: {bool(detail.get('snapshot_risk_confirmation_required'))}",
            f"Collision resolution: {bool(detail.get('collision_resolution_required'))}",
        ],
        artifacts=kv_artifacts(
            [
                ("Source DB", detail.get("source_db_path")),
                ("Target DB", detail.get("target_db_path")),
                ("Blocked Reason", detail.get("blocked_reason")),
            ]
        ),
        detail=detail,
    )


def handle_merge_corpus_databases(command, *, context, merge_corpus_databases_fn=merge_corpus_databases):
    detail = merge_corpus_databases_fn(
        context,
        source_db_path=command.source_db_path,
        target_db_path=command.target_db_path,
        snapshot_risk_confirmation_artifact_path=command.snapshot_risk_confirmation_artifact_path,
        collision_resolution_artifact_path=command.collision_resolution_artifact_path,
    )
    return build_result(
        headline="Corpus merge completed",
        summary_lines=[
            f"Imported documents: {detail.get('imported_document_count', 0)}",
            f"Archived collisions: {detail.get('archived_collision_count', 0)}",
            f"Overwritten collisions: {detail.get('overwritten_collision_count', 0)}",
            f"Stale documents: {detail.get('stale_documents', 0)}",
        ],
        artifacts=kv_artifacts(
            [
                ("Source DB", detail.get("source_db_path")),
                ("Target DB", detail.get("target_db_path")),
                ("Active Snapshot", detail.get("active_snapshot_id")),
                ("Integrity Status", detail.get("integrity_status")),
            ]
        ),
        detail=detail,
    )
