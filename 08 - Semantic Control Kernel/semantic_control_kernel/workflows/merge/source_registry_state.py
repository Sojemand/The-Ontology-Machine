from __future__ import annotations

import json
from pathlib import Path
import sqlite3
from typing import Any, Mapping

from semantic_control_kernel.repository.paths import path_hash, stable_hash
from semantic_control_kernel.workflows.merge.source_registry_errors import MergeSourceResolutionError


def source_state(database_path: str, artifact_root: str) -> str:
    if manifest_record_count(artifact_root) > 0:
        return "filled"
    path = Path(database_path)
    if not path.exists():
        raise MergeSourceResolutionError(f"Source database does not exist: {database_path}")
    sqlite_content_count = sqlite_content_count_for(path)
    if sqlite_content_count is not None:
        return "filled" if sqlite_content_count > 0 else "empty"
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return "filled" if path.stat().st_size > 0 else "empty"
    return "filled" if text.strip() else "empty"


def database_fingerprint(database_path: str) -> str:
    path = Path(database_path)
    if not path.exists():
        raise MergeSourceResolutionError(f"Source database does not exist: {database_path}")
    stat = path.stat()
    return "sha256:" + stable_hash(f"{path_hash(path)}:{stat.st_size}:{stat.st_mtime_ns}")


def artifact_tree_fingerprint(ref_payload: Mapping[str, Any]) -> str:
    basis = json.dumps(dict(ref_payload), sort_keys=True, separators=(",", ":"))
    return "sha256:" + stable_hash(basis)


def live_artifact_tree_fingerprint(source: Mapping[str, str], release: Mapping[str, str]) -> str:
    basis = {
        "artifact_root_path_hash": path_hash(source["artifact_root_path"]),
        "database_fingerprint": database_fingerprint(source["database_path"]),
        "release_fingerprint": release["release_fingerprint"],
        "release_id": release["release_id"],
        "release_version": release["release_version"],
    }
    return "sha256:" + stable_hash(json.dumps(basis, sort_keys=True, separators=(",", ":")))


def materialization_refs(artifact_root: str) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    required = (
        "pipeline_batch_id",
        "document_id",
        "record_id",
        "semantic_release_id",
        "semantic_release_version",
        "release_fingerprint",
        "taxonomy_fingerprint",
        "projection_id",
        "projection_fingerprint",
    )
    for manifest in pipeline_manifests(artifact_root):
        records = manifest.get("materialized_records")
        if not isinstance(records, list):
            continue
        for record in records:
            if isinstance(record, Mapping) and all(record.get(field) for field in required):
                refs.append({field: record[field] for field in required})
    return refs


def manifest_record_count(artifact_root: str) -> int:
    total = 0
    for manifest in pipeline_manifests(artifact_root):
        counts = manifest.get("record_counts")
        if isinstance(counts, Mapping):
            total += sum(int(value) for value in counts.values() if isinstance(value, int))
        records = manifest.get("materialized_records")
        if isinstance(records, list):
            total += len(records)
    return total


def pipeline_manifests(artifact_root: str) -> list[dict[str, Any]]:
    root = Path(artifact_root) / "Documents" / "logs" / "pipeline_batches"
    manifests: list[dict[str, Any]] = []
    for path in sorted(root.glob("*/pipeline_batch_manifest.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(payload, dict) and payload.get("batch_status") == "finalized":
            manifests.append(payload)
    return manifests


def sqlite_content_count_for(database_path: Path) -> int | None:
    if database_path.stat().st_size == 0:
        return 0
    content_tables = (
        "documents",
        "document_payloads",
        "evidence_atoms",
        "extracted_rows",
        "embedding_chunks",
        "semantic_evidence_links",
        "materialization_audit",
    )
    try:
        with sqlite3.connect(str(database_path)) as connection:
            table_names = {
                str(row[0])
                for row in connection.execute("select name from sqlite_master where type='table'").fetchall()
            }
            total = 0
            for table in content_tables:
                if table in table_names:
                    total += int(connection.execute(f'select count(*) from "{table}"').fetchone()[0])
            return total
    except sqlite3.DatabaseError:
        return None


__all__ = [
    "artifact_tree_fingerprint",
    "database_fingerprint",
    "live_artifact_tree_fingerprint",
    "materialization_refs",
    "source_state",
]
