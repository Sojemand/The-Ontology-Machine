from __future__ import annotations

from pathlib import Path

from phase12_merge_entry_support import create_artifact_tree, write_release_package

from semantic_control_kernel.repository.attach_state_store import ActiveArtifactTreeRefStore, AttachStateStore
from semantic_control_kernel.repository.database_binding_registry import DatabaseArtifactBindingRegistry
from semantic_control_kernel.repository.interaction_store import InteractionRequestStore
from semantic_control_kernel.repository.paths import StatePaths, path_hash, utc_iso
from semantic_control_kernel.repository.records import ActiveArtifactTreeRef
from semantic_control_kernel.types.enums import AttachPointerOwner
from semantic_control_kernel.types.events import UserInteractionResponse
from semantic_control_kernel.types.state import DatabaseArtifactBinding, SemanticReleaseAttachState


def seed_merge_source(
    paths: StatePaths,
    tmp_path: Path,
    name: str,
    *,
    release_version: str,
) -> Path:
    root = tmp_path / f"{name}_artifacts"
    create_artifact_tree(root)
    release_fingerprint = f"sha256:{name}_release"
    release_path = write_release_package(
        root,
        release_id=f"{name}.release",
        release_version=release_version,
        release_fingerprint=release_fingerprint,
    )
    database_path = root / "Corpus" / "corpus.db"
    database_path.write_text("", encoding="utf-8")
    put_active_artifact_ref(paths, root)
    DatabaseArtifactBindingRegistry(paths).put_verified_binding(
        DatabaseArtifactBinding(
            {
                "schema_version": DatabaseArtifactBinding.SCHEMA_VERSION,
                "database_path": str(database_path),
                "database_id": f"{name}_database",
                "artifact_root_path": str(root),
                "corpus_path": str(root / "Corpus"),
                "input_path": str(root / "Input"),
                "documents_path": str(root / "Documents"),
                "error_cases_path": str(root / "Error Cases"),
                "semantic_release_path": str(root / "Semantic Release"),
                "binding_provenance": {"created_by": "phase12_merge_interaction_test"},
                "created_at": utc_iso(),
                "updated_at": utc_iso(),
            }
        ),
        evidence_refs=["artifact_ref"],
    )
    AttachStateStore(paths).put_attach_state(
        SemanticReleaseAttachState(
            {
                "schema_version": SemanticReleaseAttachState.SCHEMA_VERSION,
                "release_path": str(release_path),
                "release_id": f"{name}.release",
                "release_version": release_version,
                "release_fingerprint": release_fingerprint,
                "runtime_locale": "en",
                "target_database_path": str(database_path),
                "attach_receipt_id": f"attach_{name}",
                "attached_at": utc_iso(),
                "pointer_owner": AttachPointerOwner.KERNEL_HELD.value,
            }
        )
    )
    return root


def put_active_artifact_ref(paths: StatePaths, root: Path) -> None:
    ActiveArtifactTreeRefStore(paths).put_verified_artifact_tree_ref(
        ActiveArtifactTreeRef(
            {
                "schema_version": ActiveArtifactTreeRef.SCHEMA_VERSION,
                "artifact_root_path": str(root),
                "artifact_root_path_hash": path_hash(root),
                "folder_contract_version": "artifact_tree.v1",
                "canonical_paths": {"Corpus": str(root / "Corpus")},
                "target_identity": {"schema_version": "state.target_identity.v1", "artifact_root_path_hash": path_hash(root)},
                "validation_receipt_id": f"validation_{root.name}",
                "validated_at": utc_iso(),
                "status": "active",
            }
        ),
        evidence_refs=["fixture"],
    )


def pending_request(paths: StatePaths, workflow_run_id: str) -> dict:
    requests = InteractionRequestStore(paths).list_pending_interactions_for_workflow(workflow_run_id)
    assert len(requests) == 1
    return requests[0].to_dict()


def submit_payload(request: dict, response_id: str, **value) -> dict:
    return {
        "schema_version": "semantic_control_kernel.interaction_response_submit.v1",
        "interaction_request_id": request["interaction_request_id"],
        "response": {
            "schema_version": UserInteractionResponse.SCHEMA_VERSION,
            "interaction_response_id": response_id,
            "interaction_request_id": request["interaction_request_id"],
            "response_status": "submitted",
            "target_identity": request["target_identity"],
            "state_snapshot_identity": request["state_snapshot_identity"],
            "host_surface_identity": "client_frontend_http_pipeline_session",
            "submitted_at": utc_iso(),
            **value,
        },
        "target_identity": request["target_identity"],
        "state_snapshot_identity": request["state_snapshot_identity"],
        "host_surface_identity": "client_frontend_http_pipeline_session",
        "client_request_id": f"req_{response_id}",
    }
