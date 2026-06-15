from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from semantic_control_kernel.repository.paths import path_hash
from semantic_control_kernel.types.merge import MergeWorkflowBlocker


def resolve_merge_target_database_path(
    target_artifact_root: str | Path,
    target_database_path: str | Path | None = None,
) -> Path:
    root = Path(target_artifact_root).resolve(strict=False)
    corpus = (root / "Corpus").resolve(strict=False)
    if target_database_path is None:
        target = corpus / "corpus.db"
    else:
        candidate = Path(target_database_path)
        if candidate.is_absolute():
            target = candidate.resolve(strict=False)
        elif len(candidate.parts) == 1:
            target = (corpus / candidate).resolve(strict=False)
        else:
            target = (root / candidate).resolve(strict=False)
    try:
        target.relative_to(corpus)
    except ValueError as exc:
        raise ValueError("Merge target database path must stay inside the selected Artifact Tree Corpus folder.") from exc
    return target


def target_confirmation_blocker(
    selection: Mapping[str, Any],
    receipt: Mapping[str, Any] | None,
    *,
    existing_selection_reused: bool = False,
) -> MergeWorkflowBlocker | None:
    if existing_selection_reused or not _target_root_non_empty(selection.get("target_artifact_root")):
        return None
    if _target_confirmation_matches(selection, receipt):
        return None
    return MergeWorkflowBlocker(
        blocker_code="confirmation_missing",
        step_id="awaiting_confirmation",
        function_or_route="database_merge_additive_only",
        recovery_state_class="target_identity_changed",
        user_visible_summary="Merge target artifact root already exists and requires an exact Kernel confirmation receipt.",
    )


def _target_root_non_empty(value: object) -> bool:
    if value is None:
        return False
    path = Path(str(value))
    try:
        if not path.exists():
            return False
        return any(not _is_ignorable_merge_log_residue(path, child) for child in path.rglob("*"))
    except OSError:
        return True


def _is_ignorable_merge_log_residue(root: Path, child: Path) -> bool:
    try:
        parts = child.relative_to(root).parts
    except ValueError:
        return False
    if parts in {
        ("Documents",),
        ("Documents", "logs"),
        ("Documents", "logs", "merge_runs"),
    }:
        return True
    if len(parts) >= 4 and parts[:3] == ("Documents", "logs", "merge_runs") and child.is_dir():
        return True
    if len(parts) == 5 and parts[:3] == ("Documents", "logs", "merge_runs"):
        return parts[4] in {
            "merge_collision_manifest.json",
            "merge_id_map_preview.json",
            "merge_selection.json",
        }
    return False


def _target_confirmation_matches(selection: Mapping[str, Any], receipt: Mapping[str, Any] | None) -> bool:
    if not isinstance(receipt, Mapping):
        return False
    decision = str(
        receipt.get("user_decision")
        or receipt.get("status")
        or receipt.get("confirmation_decision")
        or ""
    ).strip()
    if decision not in {"confirmed", "approve", "approved"}:
        return False
    identity = receipt.get("confirmed_target_identity") or receipt.get("target_identity")
    if not isinstance(identity, Mapping):
        return False
    if str(identity.get("artifact_root_path_hash", "")) != path_hash(str(selection.get("target_artifact_root", ""))):
        return False
    if str(identity.get("database_path_hash", "")) != path_hash(str(selection.get("target_database_path", ""))):
        return False
    return bool(str(receipt.get("explanation_hash") or receipt.get("outcome_explanation") or "").strip())
