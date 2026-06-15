from __future__ import annotations

from pathlib import Path
from typing import Any

from semantic_control_kernel.repository.paths import path_hash
from semantic_control_kernel.types.batches import PipelineRunTarget


def target_for(
    tmp_path: Path,
    *,
    workflow_run_id: str = "wf_phase11",
    semantic_release_state: str = "semantic_release_active",
    database_emptiness: str = "filled",
    binding: bool = True,
) -> PipelineRunTarget:
    artifact_root = tmp_path / f"Artifact Tree {workflow_run_id}"
    input_path = artifact_root / "Input"
    documents_path = artifact_root / "Documents"
    corpus_path = artifact_root / "Corpus"
    release_path = artifact_root / "Semantic Release"
    for path in (input_path, documents_path / "originals", corpus_path, release_path):
        path.mkdir(parents=True, exist_ok=True)
    for index in range(1, 4):
        (documents_path / "originals" / f"source_{index}.pdf").write_text(f"original {index}", encoding="utf-8")
    database_path = corpus_path / "corpus.db"
    database_path.write_text("filled" if database_emptiness == "filled" else "", encoding="utf-8")
    database_path_hash = path_hash(database_path)
    artifact_root_hash = path_hash(artifact_root)
    binding_ref = (
        {
            "binding_status": "verified",
            "database_path_hash": database_path_hash,
            "artifact_root_path_hash": artifact_root_hash,
        }
        if binding
        else {}
    )
    return PipelineRunTarget(
        workflow_run_id=workflow_run_id,
        database_path=str(database_path),
        database_path_hash=database_path_hash,
        database_id="active_database",
        database_fingerprint="sha256:database001",
        artifact_root_path=str(artifact_root),
        artifact_root_path_hash=artifact_root_hash,
        artifact_root_fingerprint="sha256:artifactroot001",
        input_path=str(input_path),
        documents_path=str(documents_path),
        corpus_path=str(corpus_path),
        semantic_release_path=str(release_path),
        database_emptiness=database_emptiness,
        semantic_release_state=semantic_release_state,
        active_release_ref={
            "semantic_release_id": "semantic_release.default",
            "semantic_release_version": "2026-05-01.v1",
            "release_fingerprint": "sha256:release001",
            "taxonomy_fingerprint": "sha256:tax001",
        },
        taxonomy_ref={
            "taxonomy_id": "normalizer_taxonomy.master",
            "taxonomy_version": "2026-05-01.v1",
            "taxonomy_fingerprint": "sha256:tax001",
        },
        projection_refs=(
            {
                "projection_id": "finance.default.v1",
                "projection_fingerprint": "sha256:projection001",
            },
        ),
        state_snapshot_id=f"snapshot_{workflow_run_id}",
        binding_ref=binding_ref,
    )


def input_files(count: int = 2) -> list[dict[str, Any]]:
    return [
        {
            "input_file_id": f"input_{index}",
            "input_relative_path": f"Input/source_{index}.pdf",
            "original_ref": f"Documents/originals/source_{index}.pdf",
            "content_hash": f"sha256:source{index}",
            "size_bytes": 100 + index,
            "source_kind": "document",
            "ingest_route": "auto",
            "pre_run_location": f"Input/source_{index}.pdf",
            "post_run_original_location": f"Documents/originals/source_{index}.pdf",
        }
        for index in range(1, count + 1)
    ]


def confirmation_for(target: PipelineRunTarget, scope: str = "manual_pipeline_run") -> dict[str, Any]:
    return {
        "status": "confirmed",
        "confirmation_scope": scope,
        "target_identity": target.target_identity,
        "state_snapshot_id": target.state_snapshot_id,
    }
