from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from semantic_control_kernel.types.adapter_results import AdapterCallResult, MissingCapabilityBlocker
from semantic_control_kernel.types.batches import PipelineRunBlocker


def read_active_release(
    corpus_adapter: Any,
    *,
    workflow_tool: str,
    target_database_path: Path,
) -> tuple[dict[str, Any], PipelineRunBlocker | None]:
    result = corpus_adapter.read_active_semantic_release(
        {"corpus_db_path": str(target_database_path)}
    )
    if isinstance(result, MissingCapabilityBlocker):
        payload = result.to_dict()
        return {}, PipelineRunBlocker(
            blocker_code="pipeline_capability_missing",
            step_id="loading_active_semantic_release",
            function_or_route=str(payload.get("kernel_function", workflow_tool)),
            recovery_state_class=str(payload.get("recovery_state_class", "support_only_unrecoverable")),
            user_visible_summary=str(payload.get("blocking_reason", "Required Pipeline capability is missing.")),
            diagnostics=tuple(dict(item) for item in payload.get("diagnostics", []) if isinstance(item, Mapping)),
        )
    if isinstance(result, AdapterCallResult) and result.status != "ok":
        return {}, PipelineRunBlocker(
            blocker_code=result.status,
            step_id="loading_active_semantic_release",
            function_or_route=workflow_tool,
            recovery_state_class="support_only_unrecoverable",
            user_visible_summary=f"Pipeline adapter returned {result.status} while loading the active Semantic Release.",
            diagnostics=tuple(dict(item) for item in result.to_dict().get("diagnostics", []) if isinstance(item, Mapping)),
        )
    output = _adapter_output(result)
    if not output.get("release") and not output.get("release_id"):
        return {}, PipelineRunBlocker(
            blocker_code="semantic_release_missing",
            step_id="loading_active_semantic_release",
            function_or_route=workflow_tool,
            recovery_state_class="support_only_unrecoverable",
            user_visible_summary="Reset requires an active Semantic Release on the selected Corpus database.",
        )
    return output, None


def _adapter_output(result: object) -> dict[str, Any]:
    if isinstance(result, AdapterCallResult):
        payload = result.to_dict()
        output = payload.get("output_refs")
        return dict(output) if isinstance(output, Mapping) else {}
    return dict(result) if isinstance(result, Mapping) else {}
