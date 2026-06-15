"""Record, database and artifact evidence for Kernel pipeline owner refs."""

from __future__ import annotations
import sqlite3
from pathlib import Path
from typing import Any


def document_rows_for_input(db_path: Path, input_file: dict[str, Any], record: Any | None) -> list[dict[str, str]]:
    rows = _document_rows(db_path)
    if not rows:
        return []
    source_hashes = {
        str(input_file.get("content_hash") or "").strip(),
        str(getattr(record, "content_hash", "") or "").strip() if record is not None else "",
    }
    by_hash = [row for row in rows if row.get("content_hash") in source_hashes and row.get("content_hash")]
    if by_hash:
        return _ordered_rows(by_hash)
    source_names = _source_names(input_file, record)
    if not source_names:
        return []
    by_source_name = [
        row
        for row in rows
        if row.get("file_name") in source_names or Path(row.get("source_file_path") or "").name in source_names
    ]
    return _ordered_rows(by_source_name)


def record_counts(*, db_path: Path, materialized_records: list[dict[str, Any]], error_cases: int) -> dict[str, int]:
    document_ids = {str(item.get("document_id") or "") for item in materialized_records if item.get("document_id")}
    return {
        "documents": len(document_ids),
        "normalized_records": len(materialized_records),
        "projected_records": len(materialized_records),
        "embeddings": _embedding_count(db_path, document_ids),
        "error_cases": int(error_cases),
    }


def input_disposition(record: Any, db_rows: list[dict[str, str]]) -> str:
    if db_rows and record is not None and getattr(record, "final_disposition", "") in {"success", "needs_review"}:
        return "materialized"
    if record is not None and (getattr(record, "final_disposition", "") == "error" or getattr(record, "status", "") == "error"):
        return "error_case"
    if db_rows:
        return "materialized"
    return "skipped_with_receipt"


def materialization_ref(
    *,
    pipeline_batch_id: str,
    document_id: str,
    record_id: str,
    semantic_release: dict[str, Any],
    projection: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": "kernel.record_semantic_materialization_ref.v1",
        "pipeline_batch_id": pipeline_batch_id,
        "document_id": document_id,
        "record_id": record_id,
        "semantic_release_id": str(semantic_release.get("semantic_release_id") or semantic_release.get("release_id") or ""),
        "semantic_release_version": str(semantic_release.get("semantic_release_version") or semantic_release.get("release_version") or ""),
        "release_fingerprint": str(semantic_release.get("release_fingerprint") or ""),
        "taxonomy_fingerprint": str(semantic_release.get("taxonomy_fingerprint") or ""),
        "projection_id": str(projection.get("projection_id") or ""),
        "projection_fingerprint": str(projection.get("projection_fingerprint") or ""),
    }


def empty_output_artifacts() -> dict[str, list[dict[str, str]]]:
    return {
        "raw_extracts": [],
        "structured": [],
        "normalized": [],
        "validation": [],
        "page_images": [],
        "requests": [],
        "error_cases": [],
    }


def collect_record_artifacts(output_artifacts: dict[str, list[dict[str, str]]], record: Any, *, artifact_root: Path) -> None:
    artifacts = getattr(record, "artifacts", None)
    if artifacts is None:
        return
    _extend_refs(output_artifacts["raw_extracts"], getattr(artifacts, "optimizer_raw_paths", ()), artifact_root)
    _extend_refs(output_artifacts["structured"], getattr(artifacts, "structured_paths", ()), artifact_root)
    _extend_refs(output_artifacts["normalized"], getattr(artifacts, "normalized_paths", ()), artifact_root)
    _extend_refs(output_artifacts["validation"], getattr(artifacts, "validation_report_paths", ()), artifact_root)
    _extend_refs(output_artifacts["page_images"], getattr(artifacts, "optimizer_page_image_paths", ()), artifact_root)
    _extend_refs(output_artifacts["requests"], getattr(artifacts, "optimizer_ocr_request_paths", ()), artifact_root)
    _extend_refs(output_artifacts["requests"], getattr(artifacts, "interpreter_request_paths", ()), artifact_root)
    _extend_refs(output_artifacts["requests"], getattr(artifacts, "normalizer_request_paths", ()), artifact_root)
    _extend_refs(output_artifacts["error_cases"], [getattr(artifacts, "bundle_manifest_path", ""), getattr(artifacts, "bundle_dir", "")], artifact_root)


def artifact_ref(path_value: str, artifact_root: Path) -> str:
    if not path_value:
        return ""
    path = Path(path_value)
    try:
        if path.is_absolute():
            return path.resolve(strict=False).relative_to(artifact_root.resolve(strict=False)).as_posix()
    except ValueError:
        return str(path)
    return path.as_posix()


def _embedding_count(db_path: Path, document_ids: set[str]) -> int:
    if not document_ids or not db_path.exists():
        return 0
    try:
        conn = sqlite3.connect(db_path)
    except sqlite3.DatabaseError:
        return 0
    try:
        columns = _table_columns(conn, "embeddings")
        if "document_id" not in columns:
            return 0
        placeholders = ",".join("?" for _ in document_ids)
        row = conn.execute(f"SELECT COUNT(*) FROM embeddings WHERE document_id IN ({placeholders})", tuple(document_ids)).fetchone()
        return int(row[0] if row else 0)
    except sqlite3.DatabaseError:
        return 0
    finally:
        conn.close()


def _document_rows(db_path: Path) -> list[dict[str, str]]:
    if not db_path.exists():
        return []
    try:
        conn = sqlite3.connect(db_path)
    except sqlite3.DatabaseError:
        return []
    try:
        columns = _table_columns(conn, "documents")
        id_column = "id" if "id" in columns else "document_id" if "document_id" in columns else ""
        if not id_column:
            return []
        selectable = {
            "document_id": id_column,
            "content_hash": "content_hash" if "content_hash" in columns else "''",
            "file_name": "file_name" if "file_name" in columns else "''",
            "source_file_path": "source_file_path" if "source_file_path" in columns else "''",
            "source_page": "source_page" if "source_page" in columns else "0",
            "is_archived": "is_archived" if "is_archived" in columns else "0",
        }
        rows = conn.execute(
            "SELECT " + ", ".join(f"{source} AS {alias}" for alias, source in selectable.items()) + " FROM documents"
        ).fetchall()
        return [
            {
                "document_id": str(row[0]),
                "content_hash": str(row[1] or ""),
                "file_name": str(row[2] or ""),
                "source_file_path": str(row[3] or ""),
                "source_page": str(row[4] or "0"),
            }
            for row in rows
            if str(row[5] or "0") in {"0", "False", "false", ""}
        ]
    except sqlite3.DatabaseError:
        return []
    finally:
        conn.close()


def _source_names(input_file: dict[str, Any], record: Any | None) -> set[str]:
    values = [
        input_file.get("input_relative_path"),
        input_file.get("pre_run_location"),
        input_file.get("original_ref"),
        input_file.get("post_run_original_location"),
        getattr(record, "file_name", "") if record is not None else "",
        getattr(record, "relative_path", "") if record is not None else "",
        getattr(record, "original_source_path", "") if record is not None else "",
        getattr(record, "source_path", "") if record is not None else "",
    ]
    return {Path(str(value)).name for value in values if str(value or "").strip()}


def _ordered_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    deduped = {str(row.get("document_id") or ""): row for row in rows if row.get("document_id")}
    return sorted(deduped.values(), key=lambda row: (int(row.get("source_page") or "0"), row.get("document_id") or ""))


def _extend_refs(target: list[dict[str, str]], values: Any, artifact_root: Path) -> None:
    for value in values or ():
        ref = artifact_ref(str(value or ""), artifact_root)
        if ref and {"artifact_path": ref} not in target:
            target.append({"artifact_path": ref})


def _table_columns(conn: sqlite3.Connection, table_name: str) -> set[str]:
    return {str(row[1]) for row in conn.execute(f"PRAGMA table_info({table_name})").fetchall()}
