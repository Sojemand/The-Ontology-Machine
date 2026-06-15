from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Mapping

from ..database import connect
from .multi_source_merge_manifests import artifact_ref, artifact_root_for_merge_manifest_root, load_manifest, merge_manifest_root, utc_iso, write_manifest
from .multi_source_merge_types import owner_ok, path_hash
from .multi_source_merge_validation import validate_artifact_path_within_root


def backfill_sql_from_merge_artifacts(payload: Mapping[str, Any]) -> dict[str, Any]:
    merge_run_id = str(payload.get("merge_run_id") or payload.get("selection", {}).get("merge_run_id", "")).strip()
    artifact_root_text = str(payload.get("artifact_root") or payload.get("selection", {}).get("target_artifact_root", "")).strip()
    target_database_path = str(payload.get("target_database_path") or payload.get("selection", {}).get("target_database_path", "")).strip()
    if not merge_run_id or not artifact_root_text or not target_database_path:
        raise ValueError("merge_run_id, artifact_root and target_database_path are required.")
    manifest_root = merge_manifest_root(artifact_root_text, merge_run_id)
    id_map = _load_id_map(payload, manifest_root)
    mappings = [dict(item) for item in id_map.get("mappings", []) if isinstance(item, Mapping)]
    if not mappings:
        raise ValueError("merge_id_map_invalid: merge backfill requires a non-empty merge ID map.")
    backfill_report = _backfill_target_database(Path(target_database_path), mappings, merge_run_id)
    report_path = manifest_root / "backfill_report.json"
    report = {
        "merge_run_id": merge_run_id,
        "backfilled_record_refs": backfill_report["backfilled_record_refs"],
        "skipped_ambiguous_refs": backfill_report["skipped_ambiguous_refs"],
        "post_backfill_counts": backfill_report["post_backfill_counts"],
    }
    write_manifest(report_path, report)
    output = {
        "backfill_report_ref": artifact_ref(report_path, Path(artifact_root_text)),
        "backfilled_record_count": len(report["backfilled_record_refs"]),
        "skipped_ambiguous_count": len(report["skipped_ambiguous_refs"]),
        "post_backfill_counts": report["post_backfill_counts"],
    }
    return owner_ok(
        owner_action="backfill_sql_from_merge_artifacts",
        capability="multi_source_merge_domain_service",
        target_identity={
            "database_path_hash": path_hash(target_database_path),
            "merge_run_id": merge_run_id,
            "target_database_path_hash": path_hash(target_database_path),
        },
        output_refs=output,
        receipt_fields={
            "owner_module": "05 - Corpus Builder",
            "owner_action": "backfill_sql_from_merge_artifacts",
            "merge_run_id": merge_run_id,
        },
    )


def _load_id_map(payload: Mapping[str, Any], manifest_root: Path) -> dict[str, Any]:
    inline = payload.get("id_map")
    if isinstance(inline, Mapping) and inline.get("mappings"):
        return dict(inline)
    merge_id_map_ref = payload.get("merge_id_map_ref")
    if isinstance(merge_id_map_ref, Mapping) and merge_id_map_ref.get("artifact_path"):
        path = validate_artifact_path_within_root(artifact_root_for_merge_manifest_root(manifest_root), str(merge_id_map_ref["artifact_path"]))
        return load_manifest(path)
    return load_manifest(manifest_root / "merge_id_map.json")


def _backfill_target_database(
    target_database_path: Path,
    mappings: list[Mapping[str, Any]],
    merge_run_id: str,
) -> dict[str, Any]:
    if not target_database_path.exists():
        raise ValueError(f"database_missing: merge backfill target database does not exist: {target_database_path}")
    conn = connect(str(target_database_path))
    try:
        if not _table_exists(conn, "documents"):
            raise ValueError("database_missing: merge backfill target is not a Corpus Builder database.")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("BEGIN IMMEDIATE")
        backfilled: list[dict[str, Any]] = []
        skipped: list[dict[str, Any]] = []
        for mapping in mappings:
            target_document_id = str(mapping.get("target_document_id") or mapping.get("target_record_id") or "")
            if not target_document_id:
                skipped.append({**dict(mapping), "skip_reason": "target_document_id_missing"})
                continue
            if not _document_exists(conn, target_document_id):
                raise ValueError(f"merge_id_map_invalid: target document is missing: {target_document_id}")
            _update_document_semantics(conn, target_document_id, mapping)
            _upsert_processing_state(conn, target_document_id, mapping)
            backfilled.append(dict(mapping))
        if _table_exists(conn, "materialization_runs"):
            conn.execute(
                "INSERT INTO materialization_runs (action, release_version, scope, processed_count, stale_count, error_count, notes, started_at, finished_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    "backfill_sql_from_merge_artifacts",
                    "",
                    merge_run_id,
                    len(backfilled),
                    0,
                    len(skipped),
                    "merge_id_map_backfill",
                    utc_iso(),
                    utc_iso(),
                ),
            )
        counts = {
            "records": _count_documents(conn),
            "documents": _count_documents(conn),
            "processing_state": _count_rows(conn, "document_processing_state"),
        }
        conn.commit()
        return {
            "backfilled_record_refs": backfilled,
            "skipped_ambiguous_refs": skipped,
            "post_backfill_counts": counts,
        }
    except Exception:
        if conn.in_transaction:
            conn.rollback()
        raise
    finally:
        conn.close()


def _update_document_semantics(conn: sqlite3.Connection, document_id: str, mapping: Mapping[str, Any]) -> None:
    assignments: list[str] = []
    values: list[Any] = []
    for column, key in (
        ("projection_id", "projection_id"),
        ("projection_fingerprint", "projection_fingerprint"),
        ("materialization_version", "semantic_release_version"),
    ):
        if _column_exists(conn, "documents", column):
            assignments.append(f"{column} = ?")
            values.append(str(mapping.get(key) or ""))
    if assignments:
        values.append(document_id)
        conn.execute(f"UPDATE documents SET {', '.join(assignments)} WHERE id = ?", values)


def _upsert_processing_state(conn: sqlite3.Connection, document_id: str, mapping: Mapping[str, Any]) -> None:
    if not _table_exists(conn, "document_processing_state"):
        return
    conn.execute(
        "INSERT OR REPLACE INTO document_processing_state "
        "(document_id, schema_version, materialization_version, materialized_snapshot_id, projection_id, projection_fingerprint, "
        "materialization_state, stale_reason, source_mode, last_materialized_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            document_id,
            "kernel.merge_backfill.v1",
            str(mapping.get("semantic_release_version") or ""),
            str(mapping.get("release_fingerprint") or ""),
            str(mapping.get("projection_id") or ""),
            str(mapping.get("projection_fingerprint") or ""),
            "current",
            None,
            "merged",
            utc_iso(),
        ),
    )


def _document_exists(conn: sqlite3.Connection, document_id: str) -> bool:
    return conn.execute("SELECT 1 FROM documents WHERE id = ?", (document_id,)).fetchone() is not None


def _count_documents(conn: sqlite3.Connection) -> int:
    return int(conn.execute("SELECT COUNT(*) FROM documents WHERE COALESCE(is_archived, 0) = 0").fetchone()[0])


def _count_rows(conn: sqlite3.Connection, table_name: str) -> int:
    if not _table_exists(conn, table_name):
        return 0
    return int(conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0])


def _table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type IN ('table', 'view') AND name = ?",
        (table_name,),
    ).fetchone()
    return row is not None


def _column_exists(conn: sqlite3.Connection, table_name: str, column_name: str) -> bool:
    rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    return any(str(row["name"] or "") == column_name for row in rows)
