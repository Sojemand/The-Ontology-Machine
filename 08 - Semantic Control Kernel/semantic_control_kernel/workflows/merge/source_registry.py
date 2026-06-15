from __future__ import annotations

from typing import Any, Sequence

from semantic_control_kernel.repository.attach_state_store import ActiveArtifactTreeRefStore
from semantic_control_kernel.repository.database_binding_registry import DatabaseArtifactBindingRegistry
from semantic_control_kernel.repository.paths import StatePaths, path_hash
from semantic_control_kernel.workflows.merge.source_registry_bindings import (
    list_merge_database_options,
    optional_binding_for_source,
)
from semantic_control_kernel.workflows.merge.source_registry_errors import MergeSourceResolutionError
from semantic_control_kernel.workflows.merge.source_registry_paths import source_paths_from_input, unique_paths
from semantic_control_kernel.workflows.merge.source_registry_release import release_identity_from_artifact_tree
from semantic_control_kernel.workflows.merge.source_registry_state import (
    artifact_tree_fingerprint,
    database_fingerprint,
    live_artifact_tree_fingerprint,
    materialization_refs,
    source_state,
)


def resolve_merge_source_descriptors(
    state_paths: StatePaths,
    source_paths: Sequence[str],
) -> tuple[dict[str, Any], ...]:
    registry = DatabaseArtifactBindingRegistry(state_paths)
    artifact_refs = ActiveArtifactTreeRefStore(state_paths)
    descriptors: list[dict[str, Any]] = []
    seen_database_hashes: set[str] = set()
    for raw_path in unique_paths(source_paths):
        source = source_paths_from_input(raw_path)
        database_key = path_hash(source["database_path"])
        if database_key in seen_database_hashes:
            continue
        seen_database_hashes.add(database_key)
        binding = optional_binding_for_source(registry, source)
        release = release_identity_from_artifact_tree(source["artifact_root_path"])
        ref = artifact_refs.get_by_artifact_root_hash(path_hash(source["artifact_root_path"]))
        descriptor = {
            "source_artifact_root": source["artifact_root_path"],
            "source_artifact_tree_fingerprint": (
                artifact_tree_fingerprint(ref.to_dict())
                if ref is not None
                else live_artifact_tree_fingerprint(source, release)
            ),
            "source_database_fingerprint": database_fingerprint(source["database_path"]),
            "source_database_path": source["database_path"],
            "source_release_fingerprint": release["release_fingerprint"],
            "source_release_ref": release["release_ref"],
            "source_semantic_release_id": release["release_id"],
            "source_semantic_release_version": release["release_version"],
            "source_state": source_state(source["database_path"], source["artifact_root_path"]),
            "materialization_refs": materialization_refs(source["artifact_root_path"]),
        }
        if binding is not None:
            descriptor["durable_source_database_id"] = binding.to_dict()["database_id"]
        descriptors.append(descriptor)
    return tuple(descriptors)


__all__ = [
    "MergeSourceResolutionError",
    "list_merge_database_options",
    "resolve_merge_source_descriptors",
]
