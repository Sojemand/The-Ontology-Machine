"""Workflow stages for semantic release CLI commands."""
from __future__ import annotations

from types import SimpleNamespace


def run_semantic_status(args, *, context, seams: SimpleNamespace) -> None:
    status = seams.semantic_status(
        context,
        corpus_db_path=seams.resolve_corpus_db_path(context, getattr(args, "corpus_db", None)),
    )
    print(f"Release: {status.get('active_release_id') or '-'}")
    print(f"Version: {status.get('active_release_version') or '-'}")
    print(f"Pfad: {status.get('active_release_path') or '-'}")
    if status.get("pending_release_change"):
        print(
            f"Bereit: {status.get('published_release_id') or '-'} "
            f"{status.get('published_release_version') or '-'} (noch nicht aktiv)"
        )
    print(f"Dokumente: {status.get('total_documents', 0)}")
    print(f"Stale: {status.get('stale_documents', 0)}")


def run_semantic_audit(args, *, context, seams: SimpleNamespace) -> None:
    result = seams.audit_semantics(
        context,
        corpus_db_path=seams.resolve_corpus_db_path(context, getattr(args, "corpus_db", None)),
    )
    analysis = result["analysis"]
    print(f"Report: {result['report_path']}")
    print(f"Release: {result['release_path']}")
    print(f"Projectionen: {analysis.get('projection_count', 0)}")
    print(f"Issues: {len(analysis.get('issues') or [])}")
    for issue in analysis.get("issues") or []:
        print(f"  ISSUE: {issue}")
    for warning in analysis.get("warnings") or []:
        print(f"  WARN: {warning}")


def run_semantic_load(args, *, context, seams: SimpleNamespace) -> None:
    result = seams.load_semantic_release(
        context,
        release_path=args.release,
        corpus_db_path=seams.resolve_corpus_db_path(context, getattr(args, "corpus_db", None)),
    )
    print(f"Geladen: {result['release_id']} {result['release_version']}")
    print(f"Quelle: {result['source_path']}")
    print(f"Bereitgestellt: {result['release_path']}")
    print(f"Report: {result['report_path']}")
    print("Status: noch nicht aktiv, verwende 'apply-release' fuer die Datenbank.")


def run_semantic_apply(args, *, context, seams: SimpleNamespace) -> None:
    result = seams.apply_semantic_release(
        context,
        corpus_db_path=seams.resolve_corpus_db_path(context, getattr(args, "corpus_db", None)),
    )
    print(f"Aktiviert: {result['release_id']} {result['release_version']}")
    print(f"Fingerprint: {result['fingerprint']}")
    print(f"Release: {result['release_path']}")
    print(f"Report: {result['report_path']}")


def run_semantic_backfill(args, *, context, seams: SimpleNamespace) -> None:
    result = seams.backfill_semantics(
        context,
        corpus_db_path=seams.resolve_corpus_db_path(context, getattr(args, "corpus_db", None)),
        document_ids=args.document_ids,
        stale_only=not bool(args.all),
        limit=args.limit,
    )
    print(
        f"Run {result['run_id']}: verarbeitet={result['processed_count']} "
        f"zielmenge={result['stale_count']} fehler={result['error_count']} "
        f"release={result['release_version']}"
    )


def run_merge_preflight(args, *, context, seams: SimpleNamespace) -> None:
    result = seams.merge_preflight(
        context,
        source_db_path=args.source_db,
        target_db_path=args.target_db,
    )
    print(f"Source DB: {result['source_db_path']}")
    print(f"Target DB: {result['target_db_path']}")
    print(f"Master line: {result.get('master_taxonomy_release_id') or '-'}")
    print(f"Blocked: {bool(result.get('blocked'))}")
    if result.get("blocked_reason"):
        print(f"Reason: {result['blocked_reason']}")
    print(f"Snapshot confirmation required: {bool(result.get('snapshot_risk_confirmation_required'))}")
    print(f"Collision confirmation required: {bool(result.get('collision_resolution_required'))}")
    print(f"Pending interactions: {len(result.get('pending_interactions') or [])}")


def run_merge_corpus(args, *, context, seams: SimpleNamespace) -> None:
    result = seams.merge_corpus_databases(
        context,
        source_db_path=args.source_db,
        target_db_path=args.target_db,
        snapshot_risk_confirmation_artifact_path=args.snapshot_risk_confirmation,
        collision_resolution_artifact_path=args.collision_resolution,
    )
    print(f"Merged: {result['source_db_path']} -> {result['target_db_path']}")
    print(f"Imported documents: {result['imported_document_count']}")
    print(f"Archived collisions: {result['archived_collision_count']}")
    print(f"Overwritten collisions: {result['overwritten_collision_count']}")
    print(f"Stale documents: {result['stale_documents']}")
    print(f"Integrity status: {result.get('integrity_status') or '-'}")


__all__ = [
    "run_merge_corpus",
    "run_merge_preflight",
    "run_semantic_apply",
    "run_semantic_audit",
    "run_semantic_backfill",
    "run_semantic_load",
    "run_semantic_status",
]
