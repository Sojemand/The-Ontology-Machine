from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from semantic_control_kernel.repository.attach_state_store import AttachStateStore
from semantic_control_kernel.repository.database_binding_registry import DatabaseArtifactBindingRegistry
from semantic_control_kernel.repository.errors import BindingNotFoundError
from semantic_control_kernel.repository.paths import StatePaths, path_hash
from semantic_control_kernel.types.state import DatabaseArtifactBinding
from semantic_control_kernel.workflows.merge.source_registry_errors import MergeSourceResolutionError
from semantic_control_kernel.workflows.merge.source_registry_state import source_state


def list_merge_database_options(state_paths: StatePaths) -> list[dict[str, Any]]:
    registry = DatabaseArtifactBindingRegistry(state_paths)
    attach_store = AttachStateStore(state_paths)
    options: list[dict[str, Any]] = []
    for binding in registry.list_bindings():
        payload = binding.to_dict()
        attach = attach_store.get_attach_state_for_database({"database_path": payload["database_path"]})
        try:
            current_source_state = source_state(payload["database_path"], payload["artifact_root_path"])
        except MergeSourceResolutionError:
            current_source_state = "unknown"
        options.append(
            {
                "choice_id": payload["database_path"],
                "database_id": payload["database_id"],
                "database_path": payload["database_path"],
                "artifact_root_path": payload["artifact_root_path"],
                "label": Path(str(payload["database_path"])).name,
                "description": option_description(payload["artifact_root_path"], attach),
                "source_state": current_source_state,
                "semantic_release_id": attach.payload["release_id"] if attach is not None else "",
                "semantic_release_version": attach.payload["release_version"] if attach is not None else "",
                "merge_ready": attach is not None,
            }
        )
    return options


def optional_binding_for_source(
    registry: DatabaseArtifactBindingRegistry,
    source: Mapping[str, str],
) -> DatabaseArtifactBinding | None:
    database_path = source["database_path"]
    artifact_root = source["artifact_root_path"]
    try:
        binding = registry.get_by_database_path(database_path)
    except BindingNotFoundError:
        binding = None
    if binding is not None:
        payload = binding.to_dict()
        if path_hash(payload["artifact_root_path"]) != path_hash(artifact_root):
            raise MergeSourceResolutionError(
                "Source database binding disagrees with the selected Artifact Tree root: "
                f"{database_path}"
            )
        return binding
    try:
        binding = registry.get_by_artifact_root(artifact_root)
    except BindingNotFoundError:
        return None
    payload = binding.to_dict()
    if path_hash(payload["database_path"]) != path_hash(database_path):
        raise MergeSourceResolutionError(
            "Source Artifact Tree binding disagrees with the resolved Corpus database: "
            f"{artifact_root}"
        )
    return binding


def option_description(artifact_root: object, attach: object) -> str:
    release = ""
    payload = getattr(attach, "payload", None)
    if isinstance(payload, Mapping):
        release_id = str(payload.get("release_id") or "")
        release_version = str(payload.get("release_version") or "")
        release = f" release {release_id} {release_version}".strip()
    root = str(artifact_root or "")
    return f"{root}{' | ' + release if release else ''}"


__all__ = ["list_merge_database_options", "optional_binding_for_source"]
