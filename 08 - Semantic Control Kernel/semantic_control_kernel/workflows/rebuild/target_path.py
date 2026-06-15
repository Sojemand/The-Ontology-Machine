from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from semantic_control_kernel.policy.rebuild_policy import resolve_rebuild_target_path, target_identity
from semantic_control_kernel.validation.rebuild_validation import validate_overwrite_receipt


def resolve_target_database(
    *,
    artifact_root: str | Path,
    target_database_name: str,
) -> tuple[Path, dict[str, str]]:
    target = resolve_rebuild_target_path(artifact_root, target_database_name)
    return target, target_identity(artifact_root, target)


def overwrite_blocker(
    receipt: Mapping[str, Any] | None,
    *,
    artifact_root: str | Path,
    target_database_path: str | Path,
    loaded_release_fingerprint: str,
    workflow_run_id: str,
):
    return validate_overwrite_receipt(
        receipt,
        artifact_root=artifact_root,
        target_database_path=target_database_path,
        loaded_release_fingerprint=loaded_release_fingerprint,
        workflow_run_id=workflow_run_id,
    )
