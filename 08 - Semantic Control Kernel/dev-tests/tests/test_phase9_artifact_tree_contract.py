from __future__ import annotations

from pathlib import Path

from _phase9_fakes import FakeWorkspaceAdapter, target_for
from semantic_control_kernel.repository.paths import StatePaths
from semantic_control_kernel.workflows.database_creation.shared_steps import (
    CreationStateRepository,
    DatabaseCreationExecution,
    create_canonical_artifact_tree_folders,
    validate_artifact_tree_contract,
)


def test_artifact_tree_contract_and_path_derivation(tmp_path: Path) -> None:
    target = target_for(tmp_path, name="Client A", database_name="Invoices.db")
    FakeWorkspaceAdapter().prepare_artifact_tree({"target": target.to_dict()})

    ok, reason = validate_artifact_tree_contract(target.artifact_root_path)

    assert ok is True
    assert reason == "ok"
    assert target.database_name == "Invoices"
    assert target.database_path == str(Path(target.artifact_root_path) / "Corpus" / "Invoices.db")
    assert target.input_path == str(Path(target.artifact_root_path) / "Input")


def test_artifact_tree_contract_rejects_missing_extra_and_wrong_case(tmp_path: Path) -> None:
    missing = target_for(tmp_path, name="Missing")
    create_canonical_artifact_tree_folders(missing)
    (Path(missing.semantic_release_path)).rmdir()
    assert validate_artifact_tree_contract(missing.artifact_root_path)[1] == "missing_canonical_folder:Semantic Release"

    extra = target_for(tmp_path, name="Extra")
    create_canonical_artifact_tree_folders(extra)
    (Path(extra.artifact_root_path) / "Runtime").mkdir()
    assert validate_artifact_tree_contract(extra.artifact_root_path)[1] == "extra_authoritative_folder:Runtime"

    wrong = target_for(tmp_path, name="Wrong")
    create_canonical_artifact_tree_folders(wrong)
    (Path(wrong.artifact_root_path) / "Input").rename(Path(wrong.artifact_root_path) / "input")
    assert validate_artifact_tree_contract(wrong.artifact_root_path)[1] == "missing_canonical_folder:Input"


def test_store_active_artifact_tree_does_not_write_database_binding(tmp_path: Path) -> None:
    target = target_for(tmp_path, name="Stored")
    create_canonical_artifact_tree_folders(target)
    state_root = tmp_path / "state"
    repository = CreationStateRepository(state_root)
    execution = DatabaseCreationExecution(
        workflow_run_id="wf_store_tree",
        workflow_tool="empty_database_no_semantic_release",
        state_root=state_root,
        target=target,
    )

    repository.store_active_artifact_tree(execution, "validation_receipt_1")

    paths = StatePaths.from_state_root(state_root)
    assert list(paths.artifact_trees_active_dir.glob("*.json"))
    assert list(paths.bindings_records_dir.glob("*.json")) == []
