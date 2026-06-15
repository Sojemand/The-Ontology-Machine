from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from semantic_control_kernel.repository.paths import path_hash, stable_hash

def create_artifact_tree(root: Path) -> None:
    for relative in (
        "Input",
        "Corpus",
        "Semantic Release",
        "Documents/originals",
        "Documents/raw_extracts",
        "Documents/page_images",
        "Documents/requests",
        "Documents/structured",
        "Documents/validation",
        "Documents/normalized",
        "Documents/logs",
        "Error Cases",
    ):
        (root / relative).mkdir(parents=True, exist_ok=True)


def write_release_package(
    root: Path,
    *,
    release_id: str,
    release_version: str,
    release_fingerprint: str,
    runtime_locale: str = "en",
    include_component_refs: bool = True,
) -> Path:
    release_path = root / "Semantic Release" / "releases" / release_id
    release_path.mkdir(parents=True, exist_ok=True)
    taxonomy_ref = {
        "runtime_locale": runtime_locale,
        "taxonomy_fingerprint": f"sha256:{release_id}_taxonomy",
        "taxonomy_id": f"{release_id}.taxonomy",
        "taxonomy_version": release_version,
    }
    projection_refs = [
        {
            "projection_fingerprint": f"sha256:{release_id}_projection",
            "projection_id": f"{release_id}.projection",
        }
    ]
    payload = {
        "release_fingerprint": release_fingerprint,
        "release_id": release_id,
        "release_version": release_version,
        "runtime_locale": runtime_locale,
    }
    if include_component_refs:
        payload["projection_refs"] = projection_refs
        payload["taxonomy_ref"] = taxonomy_ref
    (release_path / "release.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return release_path


def seed_rebuild_release(root: Path) -> Path:
    return write_release_package(
        root,
        release_id="tree.release",
        release_version="2.0.0",
        release_fingerprint="sha256:tree_release",
    )


def merge_resolution(collision_id: str, selected_resolution: str) -> dict[str, str]:
    return {"collision_id": collision_id, "selected_resolution": selected_resolution}


def reconciliation_receipt(*, manifest: Mapping[str, Any], selected_resolutions: Sequence[Mapping[str, Any]], workflow_run_id: str = "wf_reconcile") -> dict[str, Any]:
    fingerprint = str(manifest["manifest_fingerprint"])
    return {
        "collision_manifest_ref": {"manifest_fingerprint": fingerprint, "path": "merge_collision_manifest.json"},
        "created_at": "2026-05-06T02:00:00Z",
        "manifest_revision_after": int(manifest["manifest_revision"]) + 1,
        "manifest_revision_before": int(manifest["manifest_revision"]),
        "merge_run_id": manifest["merge_run_id"],
        "receipt_fingerprint": stable_hash(fingerprint + repr(list(selected_resolutions))),
        "reconciliation_receipt_id": "reconcile_receipt_001",
        "result_status": "resolved",
        "schema_version": "kernel.database_merge_reconciliation_receipt.v1",
        "selected_resolutions": [dict(item) for item in selected_resolutions],
        "state_snapshot_identity": {"schema_version": "state.snapshot_identity.v1", "state_snapshot_id": "snapshot_001"},
        "target_identity": {
            "schema_version": "state.target_identity.v1",
            "artifact_root_path_hash": path_hash(str(manifest["target_artifact_root"])),
            "database_path_hash": path_hash(str(manifest["target_database_path"])),
            "lock_scope": "merge",
            "target_hash": stable_hash(f"{manifest['merge_run_id']}:{manifest['target_database_path']}"),
            "workflow_run_id": workflow_run_id,
            "created_from": "fixture",
        },
        "updated_collision_manifest_ref": {"manifest_fingerprint": fingerprint, "path": "merge_collision_manifest.json"},
        "workflow_run_id": workflow_run_id,
    }


def source(tmp_path: Path, name: str, *, state: str = "empty", durable: bool = True, batch_id: str = "batch_001", materialization: bool = True) -> dict[str, Any]:
    root = tmp_path / f"{name}_artifacts"
    create_artifact_tree(root)
    write_release_package(
        root,
        release_id=f"release.{name}",
        release_version="1.0.0",
        release_fingerprint=f"sha256:{name}_release",
    )
    db = root / "Corpus" / "corpus.db"
    db.write_text("" if state == "empty" else "filled", encoding="utf-8")
    payload = {
        "source_artifact_root": str(root),
        "source_artifact_tree_fingerprint": f"sha256:{name}_artifact",
        "source_database_fingerprint": f"sha256:{name}_database",
        "source_database_path": str(db),
        "source_release_fingerprint": f"sha256:{name}_release",
        "source_release_ref": {
            "projection_refs": [
                {
                    "projection_fingerprint": f"sha256:release.{name}_projection",
                    "projection_id": f"release.{name}.projection",
                }
            ],
            "release_fingerprint": f"sha256:{name}_release",
            "release_id": f"release.{name}",
            "release_version": "1.0.0",
            "runtime_locale": "en",
            "taxonomy_ref": {
                "runtime_locale": "en",
                "taxonomy_fingerprint": f"sha256:release.{name}_taxonomy",
                "taxonomy_id": f"release.{name}.taxonomy",
                "taxonomy_version": "1.0.0",
            },
        },
        "source_semantic_release_id": f"release.{name}",
        "source_semantic_release_version": "1.0.0",
        "source_state": state,
    }
    if durable:
        payload["durable_source_database_id"] = f"source_db_{name}"
    if materialization:
        payload["materialization_refs"] = [
            {
                "pipeline_batch_id": batch_id,
                "record_id": f"record_{name}",
                "projection_fingerprint": f"sha256:{name}_projection",
                "projection_id": "projection.default",
                "release_fingerprint": f"sha256:{name}_release",
                "semantic_release_id": f"release.{name}",
                "semantic_release_version": "1.0.0",
                "taxonomy_fingerprint": f"sha256:{name}_taxonomy",
            }
        ]
    return payload


def target_root(tmp_path: Path, name: str = "target_artifacts") -> Path:
    return tmp_path / name


def merge_target_confirmation(selection: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "confirmation_receipt_id": "receipt_merge_target",
        "confirmed_at": "2026-05-06T02:00:00Z",
        "confirmed_state_snapshot_identity": {"schema_version": "state.snapshot_identity.v1", "state_snapshot_id": "snapshot_merge_target"},
        "confirmed_target_identity": {
            "schema_version": "state.target_identity.v1",
            "artifact_root_path_hash": path_hash(selection["target_artifact_root"]),
            "database_path_hash": path_hash(selection["target_database_path"]),
            "lock_scope": "merge",
            "target_hash": stable_hash(f"{selection['target_artifact_root']}:{selection['target_database_path']}"),
            "created_from": "fixture",
        },
        "explanation_hash": stable_hash("merge into existing target root"),
        "schema_version": "kernel.confirmation_receipt.v1",
        "user_decision": "confirmed",
    }
