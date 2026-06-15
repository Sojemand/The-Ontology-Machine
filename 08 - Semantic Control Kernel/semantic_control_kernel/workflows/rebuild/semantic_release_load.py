from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from semantic_control_kernel.types.rebuild import RebuildWorkflowBlocker, release_identity_from_payload
from semantic_control_kernel.validation.rebuild_validation import semantic_release_package_paths, validate_semantic_release_folder


def corpus_builder_load_semantic_release(
    semantic_release_adapter: object,
    *,
    artifact_root: str | Path,
    target_database_path: str | Path,
) -> tuple[dict[str, Any] | None, object | None, RebuildWorkflowBlocker | None]:
    folder_blocker = validate_semantic_release_folder(artifact_root)
    if folder_blocker is not None:
        return None, None, folder_blocker
    release_candidates = semantic_release_package_paths(artifact_root)
    release_path = release_candidates[0].parent if len(release_candidates) == 1 else Path(artifact_root) / "Semantic Release"
    result = semantic_release_adapter.load_semantic_release_from_artifact_tree(
        {
            "artifact_root": str(Path(artifact_root).resolve(strict=False)),
            "corpus_db_path": str(Path(target_database_path).resolve(strict=False)),
            "release_path": str(release_path.resolve(strict=False)),
        }
    )
    blocker = _blocker_from_result("loading_semantic_release", result, "corpus_builder_load_semantic_release")
    if blocker is not None:
        return None, result, blocker
    output = _adapter_output(result)
    release = release_identity_from_payload(output)
    release_path_text = release.get("loaded_release_path") or (str(release_path.resolve(strict=False)) if len(release_candidates) == 1 else "")
    release["loaded_release_path"] = str(release_path_text)
    if not release["loaded_release_path"] or not release["loaded_release_fingerprint"] or not release["loaded_semantic_release_id"] or not release["loaded_semantic_release_version"]:
        return None, result, RebuildWorkflowBlocker(
            blocker_code="release_incomplete",
            step_id="loading_semantic_release",
            function_or_route="corpus_builder_load_semantic_release",
            recovery_state_class="semantic_release_incomplete_staged",
            user_visible_summary="Loaded Semantic Release identity is incomplete.",
        )
    return release, result, None


def _blocker_from_result(step_id: str, result: object, function_name: str) -> RebuildWorkflowBlocker | None:
    from semantic_control_kernel.types.adapter_results import AdapterCallResult, MissingCapabilityBlocker

    if isinstance(result, MissingCapabilityBlocker):
        payload = result.to_dict()
        return RebuildWorkflowBlocker(
            blocker_code="pipeline_capability_missing",
            step_id=step_id,
            function_or_route=str(payload.get("kernel_function", function_name)),
            recovery_state_class=str(payload.get("recovery_state_class", "support_only_unrecoverable")),
            user_visible_summary=str(payload.get("blocking_reason", "Required Pipeline capability is missing.")),
            diagnostics=tuple(dict(item) for item in payload.get("diagnostics", []) if isinstance(item, Mapping)),
        )
    if isinstance(result, AdapterCallResult) and result.status != "ok":
        return RebuildWorkflowBlocker(
            blocker_code=result.status,
            step_id=step_id,
            function_or_route=function_name,
            recovery_state_class="support_only_unrecoverable",
            user_visible_summary=f"Pipeline adapter returned {result.status}.",
            diagnostics=tuple(dict(item) for item in result.to_dict().get("diagnostics", []) if isinstance(item, Mapping)),
        )
    return None


def _adapter_output(result: object) -> dict[str, Any]:
    if hasattr(result, "to_dict"):
        payload = result.to_dict()
        output = payload.get("output_refs")
        return dict(output) if isinstance(output, Mapping) else {}
    return dict(result) if isinstance(result, Mapping) else {}
