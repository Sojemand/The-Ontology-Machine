from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Sequence

from semantic_control_kernel.repository.paths import path_hash
from semantic_control_kernel.types.database_creation import DatabaseCreationTarget
from semantic_control_kernel.workflows.database_creation.shared_steps import create_canonical_artifact_tree_folders

from _phase9_results import missing, ok_result


class FakeInteractionPort:
    def __init__(
        self,
        *,
        target: DatabaseCreationTarget | None = None,
        taxonomy_samples: Sequence[Mapping[str, Any]] = (),
        projection_samples: Sequence[Mapping[str, Any]] = (),
        taxonomy_ref: Mapping[str, Any] | None = None,
    ) -> None:
        self.target = target
        self.taxonomy_samples = tuple(dict(item) for item in taxonomy_samples)
        self.projection_samples = tuple(dict(item) for item in projection_samples)
        self.taxonomy_ref = dict(taxonomy_ref or {})

    def collect_creation_target(self, *, workflow_tool: str, workflow_run_id: str) -> DatabaseCreationTarget | None:
        return self.target

    def select_sample_files(
        self,
        *,
        workflow_tool: str,
        workflow_run_id: str,
        purpose: str,
        target: DatabaseCreationTarget | None,
    ) -> tuple[Mapping[str, Any], ...]:
        if purpose == "taxonomy":
            return self.taxonomy_samples
        return self.projection_samples

    def resolve_taxonomy_ref(
        self,
        *,
        workflow_tool: str,
        workflow_run_id: str,
        target: DatabaseCreationTarget | None,
        state: Mapping[str, Any],
    ) -> Mapping[str, Any] | None:
        return self.taxonomy_ref or None


class FakeWorkspaceAdapter:
    def __init__(self, *, missing_prepare: bool = False, missing_validate: bool = False) -> None:
        self.missing_prepare = missing_prepare
        self.missing_validate = missing_validate
        self.calls: list[str] = []

    def prepare_artifact_tree(self, request_payload: Mapping[str, Any] | None = None):
        self.calls.append("prepare_artifact_tree")
        if self.missing_prepare:
            return missing("create_standard_artifact_folder_tree")
        target = DatabaseCreationTarget.from_dict(request_payload["target"])
        create_canonical_artifact_tree_folders(target)
        return ok_result("create_standard_artifact_folder_tree", {"artifact_root_path": target.artifact_root_path})

    def validate_artifact_tree(self, request_payload: Mapping[str, Any] | None = None):
        self.calls.append("validate_artifact_tree")
        if self.missing_validate:
            return missing("store_active_artifact_folder_tree")
        return ok_result("store_active_artifact_folder_tree", {"validation_status": "valid"})


class FakeCorpusAdapter:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def create_empty_database(self, request_payload: Mapping[str, Any] | None = None):
        self.calls.append("create_empty_database")
        database_path = Path(str(request_payload["database_path"]))
        database_path.parent.mkdir(parents=True, exist_ok=True)
        database_path.write_text("", encoding="utf-8")
        return ok_result(
            "create_empty_database",
            {
                "database_id": f"db_{path_hash(database_path)}",
                "database_path": str(database_path),
                "database_path_hash": path_hash(database_path),
            },
        )
