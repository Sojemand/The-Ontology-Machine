from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from semantic_control_kernel.policy.rebuild_policy import overwrite_receipt_matches
from semantic_control_kernel.repository.paths import stable_hash
from semantic_control_kernel.types.rebuild import REBUILD_MANIFEST_REQUIRED_FIELDS, RebuildWorkflowBlocker


def semantic_release_package_paths(artifact_root: str | Path) -> list[Path]:
    release_root = Path(artifact_root) / "Semantic Release" / "releases"
    if not release_root.is_dir():
        return []
    return sorted(path for path in release_root.glob("*/release.json") if path.is_file())


def validate_semantic_release_folder(artifact_root: str | Path) -> RebuildWorkflowBlocker | None:
    release_root = Path(artifact_root) / "Semantic Release"
    if not release_root.is_dir():
        return RebuildWorkflowBlocker(
            blocker_code="release_missing",
            step_id="loading_semantic_release",
            function_or_route="corpus_builder_load_semantic_release",
            recovery_state_class="semantic_release_incomplete_staged",
            user_visible_summary="The selected Artifact Tree has no complete Semantic Release folder.",
        )
    if not semantic_release_package_paths(artifact_root):
        return RebuildWorkflowBlocker(
            blocker_code="release_incomplete",
            step_id="loading_semantic_release",
            function_or_route="corpus_builder_load_semantic_release",
            recovery_state_class="semantic_release_incomplete_staged",
            user_visible_summary="The selected Artifact Tree Semantic Release folder has no complete release package.",
        )
    return None


def validate_overwrite_receipt(
    receipt: Mapping[str, Any] | None,
    *,
    artifact_root: str | Path,
    target_database_path: str | Path,
    loaded_release_fingerprint: str,
    workflow_run_id: str,
) -> RebuildWorkflowBlocker | None:
    if overwrite_receipt_matches(
        receipt,
        artifact_root=artifact_root,
        target_database_path=target_database_path,
        loaded_release_fingerprint=loaded_release_fingerprint,
        workflow_run_id=workflow_run_id,
    ):
        return None
    return RebuildWorkflowBlocker(
        blocker_code="confirmation_missing",
        step_id="awaiting_confirmation",
        function_or_route="database_rebuild_from_artifacts",
        recovery_state_class="target_identity_changed",
        user_visible_summary="Rebuild overwrite requires an exact Kernel confirmation receipt.",
    )


def validate_rebuild_manifest(manifest: Mapping[str, Any]) -> None:
    missing = [field for field in REBUILD_MANIFEST_REQUIRED_FIELDS if field not in manifest]
    if missing:
        raise ValueError(f"kernel.database_rebuild_manifest.v1 missing required field(s): {', '.join(missing)}")
    if manifest.get("manifest_fingerprint") != rebuild_manifest_fingerprint(manifest):
        raise ValueError("manifest_fingerprint does not match rebuild manifest.")


def rebuild_manifest_fingerprint(manifest: Mapping[str, Any]) -> str:
    payload = {key: value for key, value in manifest.items() if key != "manifest_fingerprint"}
    return stable_hash(repr(_stable(payload)))


def _stable(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _stable(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        return [_stable(item) for item in value]
    return value
