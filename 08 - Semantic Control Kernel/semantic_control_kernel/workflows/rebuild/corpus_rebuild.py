from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from semantic_control_kernel.repository.paths import canonical_path_text
from semantic_control_kernel.types.rebuild import RebuildWorkflowBlocker
from semantic_control_kernel.workflows.rebuild.semantic_release_load import _adapter_output, _blocker_from_result


def run_corpus_builder(
    corpus_adapter: object,
    *,
    artifact_root: str | Path,
    target_database_path: str | Path,
    loaded_release: Mapping[str, Any],
    workflow_run_id: str,
) -> tuple[dict[str, Any] | None, object | None, RebuildWorkflowBlocker | None]:
    payload = {
        "artifact_root": str(Path(artifact_root).resolve(strict=False)),
        "corpus_db_path": str(Path(target_database_path).resolve(strict=False)),
        "create_new": False,
        "loaded_semantic_release": dict(loaded_release),
        "release_path": str(loaded_release.get("loaded_release_path") or ""),
        "replace_existing": True,
        "target_identity": {
            "artifact_root": str(Path(artifact_root).resolve(strict=False)),
            "target_database_path": str(Path(target_database_path).resolve(strict=False)),
        },
        "workflow_run_id": workflow_run_id,
    }
    result = corpus_adapter.rebuild_from_artifacts(payload)
    blocker = _blocker_from_result("running_rebuild", result, "run_corpus_builder")
    if blocker is not None:
        return None, result, blocker
    output = _adapter_output(result)
    if canonical_path_text(output.get("database_path") or output.get("corpus_db_path") or "") != canonical_path_text(target_database_path):
        return None, result, RebuildWorkflowBlocker(
            blocker_code="rebuild_primitive_insufficient",
            step_id="running_rebuild",
            function_or_route="run_corpus_builder",
            recovery_state_class="support_only_unrecoverable",
            user_visible_summary="Corpus Builder rebuild did not prove the exact Kernel target database path.",
        )
    release_fingerprint = str(output.get("loaded_release_fingerprint") or output.get("release_fingerprint") or "")
    if release_fingerprint != loaded_release.get("loaded_release_fingerprint"):
        return None, result, RebuildWorkflowBlocker(
            blocker_code="rebuild_primitive_insufficient",
            step_id="running_rebuild",
            function_or_route="run_corpus_builder",
            recovery_state_class="support_only_unrecoverable",
            user_visible_summary="Corpus Builder rebuild did not prove the loaded Semantic Release identity.",
        )
    return output, result, None
