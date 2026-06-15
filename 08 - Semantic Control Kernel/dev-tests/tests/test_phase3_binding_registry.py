from __future__ import annotations

import json
from pathlib import Path

import pytest

from semantic_control_kernel.repository.attach_state_store import ActiveArtifactTreeRefStore
from semantic_control_kernel.repository.database_binding_registry import DatabaseArtifactBindingRegistry
from semantic_control_kernel.repository.errors import BindingConflictError
from semantic_control_kernel.repository.paths import StatePaths, path_hash
from semantic_control_kernel.repository.records import ActiveArtifactTreeRef
from semantic_control_kernel.types.state import DatabaseArtifactBinding


MODULE_ROOT = Path(__file__).resolve().parents[2]
FIXTURES = MODULE_ROOT / "dev-tests" / "fixtures" / "contracts"


def _binding(tmp_path: Path, **updates) -> DatabaseArtifactBinding:
    payload = json.loads((FIXTURES / "kernel__database_artifact_binding__v1.valid.json").read_text(encoding="utf-8"))
    artifact_root = tmp_path / "artifact_root"
    artifact_root.mkdir(exist_ok=True)
    database_path = tmp_path / "database.sqlite"
    if not updates.pop("skip_database_create", False):
        database_path.write_text("sqlite placeholder", encoding="utf-8")
    payload.update(
        {
            "artifact_root_path": str(artifact_root),
            "corpus_path": str(artifact_root / "Corpus"),
            "database_path": str(database_path),
            "documents_path": str(artifact_root / "Documents"),
            "error_cases_path": str(artifact_root / "ErrorCases"),
            "input_path": str(artifact_root / "Input"),
            "semantic_release_path": str(artifact_root / "SemanticRelease"),
        }
    )
    payload.update(updates)
    return DatabaseArtifactBinding.from_dict(payload)


def _active_artifact_ref(artifact_root_path: str) -> ActiveArtifactTreeRef:
    return ActiveArtifactTreeRef(
        {
            "artifact_root_path": artifact_root_path,
            "artifact_root_path_hash": path_hash(artifact_root_path),
            "canonical_paths": {"Documents": f"{artifact_root_path}/Documents"},
            "folder_contract_version": "artifact_tree.v1",
            "schema_version": ActiveArtifactTreeRef.SCHEMA_VERSION,
            "status": "active",
            "target_identity": {"artifact_root_path_hash": path_hash(artifact_root_path)},
            "validated_at": "2026-05-05T00:00:00Z",
            "validation_receipt_id": "opr_validation",
        }
    )


def test_binding_registry_writes_and_resolves_verified_binding(tmp_path: Path) -> None:
    paths = StatePaths.from_state_root(tmp_path / "state")
    binding = _binding(tmp_path)
    ActiveArtifactTreeRefStore(paths).put_verified_artifact_tree_ref(_active_artifact_ref(binding.payload["artifact_root_path"]), [])
    registry = DatabaseArtifactBindingRegistry(paths)

    registry.put_verified_binding(binding, [{"receipt_id": "opr_validation"}])

    assert registry.get_by_database_id("database_id_example").payload["artifact_root_path"] == binding.payload["artifact_root_path"]
    assert registry.get_by_database_path(binding.payload["database_path"]).payload["database_id"] == "database_id_example"
    assert registry.get_by_artifact_root(binding.payload["artifact_root_path"]).payload["database_path"] == binding.payload["database_path"]


def test_binding_registry_rejects_conflicting_evidence(tmp_path: Path) -> None:
    paths = StatePaths.from_state_root(tmp_path / "state")
    artifacts = ActiveArtifactTreeRefStore(paths)
    first = _binding(tmp_path)
    other_artifact_root = tmp_path / "other_artifact_root"
    other_artifact_root.mkdir()
    artifacts.put_verified_artifact_tree_ref(_active_artifact_ref(first.payload["artifact_root_path"]), [])
    artifacts.put_verified_artifact_tree_ref(_active_artifact_ref(str(other_artifact_root)), [])
    registry = DatabaseArtifactBindingRegistry(paths)
    registry.put_verified_binding(first, [])

    with pytest.raises(BindingConflictError):
        registry.put_verified_binding(_binding(tmp_path, artifact_root_path=str(other_artifact_root)), [])


def test_binding_registry_marks_stale_without_deleting_evidence(tmp_path: Path) -> None:
    paths = StatePaths.from_state_root(tmp_path / "state")
    binding = _binding(tmp_path)
    ActiveArtifactTreeRefStore(paths).put_verified_artifact_tree_ref(_active_artifact_ref(binding.payload["artifact_root_path"]), [])
    registry = DatabaseArtifactBindingRegistry(paths)
    registry.put_verified_binding(binding, [])

    registry.mark_binding_stale({"database_id": "database_id_example"}, "artifact tree moved", "rcr_1")

    assert registry.list_bindings() == []
    assert list(paths.bindings_history_dir.rglob("*.json"))


def test_binding_registry_rejects_missing_target_database(tmp_path: Path) -> None:
    paths = StatePaths.from_state_root(tmp_path / "state")
    binding = _binding(tmp_path, skip_database_create=True, database_path=str(tmp_path / "missing.sqlite"))
    ActiveArtifactTreeRefStore(paths).put_verified_artifact_tree_ref(_active_artifact_ref(binding.payload["artifact_root_path"]), [])
    registry = DatabaseArtifactBindingRegistry(paths)

    with pytest.raises(BindingConflictError):
        registry.put_verified_binding(binding, [])
