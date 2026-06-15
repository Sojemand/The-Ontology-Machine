from __future__ import annotations

from typing import Any, Mapping, Sequence

from semantic_control_kernel.policy.artifact_merge_policy import missing_artifact_blocks, target_artifact_path
from semantic_control_kernel.types.merge import MergeWorkflowBlocker
from semantic_control_kernel.workflows.merge.receipts import adapter_output, blocker_from_adapter_result


def plan_artifact_fill(records: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    existing: set[str] = set()
    planned: list[dict[str, Any]] = []
    for record in records:
        source_path = str(record.get("source_artifact_path", ""))
        if not source_path and missing_artifact_blocks(record):
            raise ValueError("Missing source artifact blocks filled merge.")
        target_path = target_artifact_path(
            source_database_id=str(record.get("source_database_id", "")),
            source_relative_path=source_path,
            source_content_hash=str(record.get("source_content_hash", "")),
            existing_target_paths=existing,
        )
        existing.add(target_path)
        planned.append({**dict(record), "target_artifact_path": target_path})
    return planned


def fill_artifact_folder_tree(merge_adapter: object, payload: Mapping[str, Any]) -> tuple[object, MergeWorkflowBlocker | None]:
    result = merge_adapter.fill_artifact_tree(payload)
    return result, blocker_from_adapter_result("filling_artifact_tree", result, function_name="fill_artifact_folder_tree")


def artifact_path_mappings_from_owner(result: object) -> list[dict[str, Any]]:
    output = adapter_output(result)
    mappings = output.get("artifact_path_mappings", [])
    return [dict(item) for item in mappings if isinstance(item, Mapping)]
