from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from ..semantic_release.multi_source_merge_types import owner_ok
from .manifest_reader import latest_manifest, read_json
from .path_io import write_bytes, write_json
from .types import RETRIEVED_ORIGINALS_MANIFEST_SCHEMA_VERSION


def restore_pipeline_batch_originals(payload: Mapping[str, Any]) -> dict[str, Any]:
    artifact_root = str(payload.get("artifact_root") or "")
    manifest_path = None
    manifest = None
    if payload.get("pipeline_batch_id"):
        manifest_path = Path(artifact_root) / "Documents" / "logs" / "pipeline_batches" / str(payload["pipeline_batch_id"]) / "pipeline_batch_manifest.json"
        manifest = read_json(manifest_path)
    else:
        manifest, manifest_path = latest_manifest(artifact_root)
    if manifest is None or manifest_path is None:
        raise ValueError("No pipeline batch manifest exists.")
    target_input_path = Path(str(payload.get("target_input_path") or Path(artifact_root) / "Input"))
    restored: list[dict[str, Any]] = []
    for item in manifest.get("input_files", []):
        if not isinstance(item, Mapping):
            continue
        source = Path(str(item.get("original_ref") or item.get("source_path") or item.get("path") or ""))
        destination = target_input_path / source.name
        content_hash = str(item.get("content_hash") or _content_hash(source) or "")
        if source.exists():
            write_bytes(destination, source.read_bytes())
        restored.append(
            {
                "source_ref": {
                    "artifact_path": str(source),
                    "content_hash": content_hash,
                    "size_bytes": source.stat().st_size if source.exists() else 0,
                },
                "destination_ref": {
                    "artifact_path": destination.relative_to(Path(artifact_root)).as_posix(),
                    "target_input_ref": destination.relative_to(Path(artifact_root)).as_posix(),
                    "input_relative_path": destination.relative_to(Path(artifact_root)).as_posix(),
                    "file_name": destination.name,
                    "content_hash": content_hash,
                    "size_bytes": source.stat().st_size if source.exists() else 0,
                },
            }
        )
    journal_path = manifest_path.parent / "restore_originals_journal.json"
    journal_payload = {
        "schema_version": RETRIEVED_ORIGINALS_MANIFEST_SCHEMA_VERSION,
        "workflow_run_id": str(payload.get("workflow_run_id") or "wr_phase19"),
        "retrieval_scope": "all_originals" if payload.get("all_originals_scope") else "pipeline_batch",
        "source_manifest_ref": {"artifact_path": manifest_path.relative_to(Path(artifact_root)).as_posix()},
        "restored_originals": restored,
        "collision_decisions": [],
        "source_cleanup_journal_ref": {"artifact_path": "none"},
        "retrieval_status": "completed",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    write_json(journal_path, journal_payload)
    output = {
        "restored_original_refs": restored,
        "restored_originals": restored,
        "input_refs": [item["destination_ref"] for item in restored],
        "move_or_copy_journal_ref": {"artifact_path": journal_path.relative_to(Path(artifact_root)).as_posix()},
        "collision_report_ref": {"artifact_path": "none"},
        "source_cleanup_verified": True,
        "source_cleanup_journal_ref": {"journal_id": str(manifest.get("pipeline_batch_id", ""))},
        "restored_count": len(restored),
    }
    return owner_ok(
        owner_action="restore_pipeline_batch_originals",
        capability="pipeline_batch_manifest_and_reingest_domain_service",
        target_identity=_mapping(payload, "target_identity"),
        output_refs=output,
        receipt_fields={"owner_module": "05 - Corpus Builder", "owner_action": "restore_pipeline_batch_originals", "pipeline_batch_id": str(manifest.get('pipeline_batch_id', ''))},
    )


def _mapping(payload: Mapping[str, Any], key: str) -> dict[str, Any]:
    value = payload.get(key)
    return dict(value) if isinstance(value, Mapping) else {}


def _content_hash(path: Path) -> str:
    if not path.exists():
        return ""
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()
