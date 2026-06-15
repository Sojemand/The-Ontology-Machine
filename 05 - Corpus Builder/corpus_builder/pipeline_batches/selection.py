from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from ..semantic_release.multi_source_merge_types import owner_ok
from .manifest_reader import latest_manifest
from .path_io import write_bytes, write_json
from .types import SAMPLE_SELECTION_MANIFEST_SCHEMA_VERSION


def inspect_latest_pipeline_batch(payload: Mapping[str, Any]) -> dict[str, Any]:
    artifact_root = str(payload.get("artifact_root") or "")
    manifest, manifest_path = latest_manifest(artifact_root)
    if manifest is None or manifest_path is None:
        raise ValueError("No finalized pipeline batch manifest exists.")
    output = {
        "pipeline_batch_manifest_ref": {"artifact_path": manifest_path.relative_to(Path(artifact_root)).as_posix()},
        "pipeline_batch_id": str(manifest.get("pipeline_batch_id", "")),
        "batch_kind": str(manifest.get("batch_kind", "")),
        "record_counts": dict(manifest.get("record_counts", {})),
        "cleanup_eligibility": {"can_cleanup_batch": True},
        "original_refs": list(manifest.get("input_files", [])),
        "manifest_fingerprint": str(manifest.get("manifest_fingerprint", "")),
    }
    return owner_ok(
        owner_action="inspect_latest_pipeline_batch",
        capability="pipeline_batch_manifest_and_reingest_domain_service",
        target_identity=_mapping(payload, "target_identity"),
        output_refs=output,
        receipt_fields={"owner_module": "05 - Corpus Builder", "owner_action": "inspect_latest_pipeline_batch", "pipeline_batch_id": output["pipeline_batch_id"], "manifest_fingerprint": output["manifest_fingerprint"]},
    )


def extract_sample_files_for_reingest(payload: Mapping[str, Any]) -> dict[str, Any]:
    artifact_root = str(payload.get("artifact_root") or "")
    manifest, manifest_path = latest_manifest(artifact_root)
    if manifest is None or manifest_path is None:
        raise ValueError("No finalized pipeline batch manifest exists.")
    sample_count = int(payload.get("sample_count") or 1)
    materialized_records = [dict(item) for item in manifest.get("materialized_records", [])[:sample_count] if isinstance(item, Mapping)]
    input_files = [dict(item) for item in manifest.get("input_files", [])[:sample_count] if isinstance(item, Mapping)]
    workflow_run_id = str(payload.get("workflow_run_id") or "wr_phase19")
    selection_seed = repr(materialized_records)
    workflow_hash = hashlib.sha256(workflow_run_id.encode("utf-8")).hexdigest()[:8]
    content_hash = hashlib.sha256(selection_seed.encode("utf-8")).hexdigest()[:8]
    selection_id = f"sample_selection_{workflow_hash}_1_{content_hash}"
    target_input_path = Path(str(payload.get("target_input_path") or Path(artifact_root) / "Input"))
    selected: list[dict[str, Any]] = []
    copied_input_refs: list[dict[str, Any]] = []
    for index, (record, item) in enumerate(zip(materialized_records, input_files, strict=False), start=1):
        source = Path(str(item.get("original_ref") or item.get("source_path") or item.get("path") or ""))
        original_ref = str(item.get("original_ref") or item.get("source_path") or item.get("path") or "")
        file_hash = str(item.get("content_hash") or _content_hash(source) or "")
        if source.exists():
            destination = target_input_path / source.name
            write_bytes(destination, source.read_bytes())
            copied_input_refs.append(
                {
                    "document_id": str(record.get("document_id") or ""),
                    "record_id": str(record.get("record_id") or ""),
                    "target_input_ref": destination.relative_to(Path(artifact_root)).as_posix(),
                    "content_hash": file_hash,
                    "size_bytes": source.stat().st_size,
                }
            )
            selected.append(
                {
                    **record,
                    "original_ref": original_ref,
                    "target_input_ref": destination.relative_to(Path(artifact_root)).as_posix(),
                    "target_input_name": source.name,
                    "content_hash": file_hash,
                }
            )
    manifest_payload = {
        "schema_version": SAMPLE_SELECTION_MANIFEST_SCHEMA_VERSION,
        "sample_selection_id": selection_id,
        "workflow_run_id": workflow_run_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "active_database": dict(manifest.get("active_database", {})),
        "source_manifest_ref": {
            "artifact_path": manifest_path.relative_to(Path(artifact_root)).as_posix(),
            "pipeline_batch_id": str(manifest.get("pipeline_batch_id", "")),
            "manifest_fingerprint": str(manifest.get("manifest_fingerprint", "")),
        },
        "selected_records": selected,
        "target_input_refs": copied_input_refs,
        "selection_fingerprint": "sha256:" + hashlib.sha256(selection_seed.encode("utf-8")).hexdigest(),
    }
    selection_path = Path(artifact_root) / "Documents" / "logs" / "pipeline_batches" / "selections" / selection_id / "sample_selection_manifest.json"
    write_json(selection_path, manifest_payload)
    output = {
        "sample_selection_manifest_ref": {"artifact_path": selection_path.relative_to(Path(artifact_root)).as_posix()},
        "sample_selection_id": selection_id,
        "source_manifest_ref": dict(manifest_payload["source_manifest_ref"]),
        "selected_records": selected,
        "copied_input_refs": copied_input_refs,
        "original_refs": [{"original_ref": item.get("original_ref") or item.get("source_path") or item.get("path") or ""} for item in input_files],
        "selection_fingerprint": manifest_payload["selection_fingerprint"],
    }
    return owner_ok(
        owner_action="extract_sample_files_for_reingest",
        capability="pipeline_batch_manifest_and_reingest_domain_service",
        target_identity=_mapping(payload, "target_identity"),
        output_refs=output,
        receipt_fields={"owner_module": "05 - Corpus Builder", "owner_action": "extract_sample_files_for_reingest", "sample_selection_id": selection_id},
    )


def _mapping(payload: Mapping[str, Any], key: str) -> dict[str, Any]:
    value = payload.get(key)
    return dict(value) if isinstance(value, Mapping) else {}


def _content_hash(path: Path) -> str:
    if not path.exists():
        return ""
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()
