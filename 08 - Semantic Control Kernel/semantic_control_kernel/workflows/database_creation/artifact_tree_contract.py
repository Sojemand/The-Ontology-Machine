from __future__ import annotations

from pathlib import Path

from semantic_control_kernel.types.database_creation import CANONICAL_ARTIFACT_FOLDERS, DatabaseCreationBlocker, DatabaseCreationTarget
from semantic_control_kernel.workflows.database_creation.blockers import create_blocker


def reject_target_conflict(target: DatabaseCreationTarget) -> DatabaseCreationBlocker | None:
    if Path(target.artifact_root_path).exists() or Path(target.database_path).exists():
        return create_blocker(
            step_id="dc_create_artifact_tree",
            function_or_route="create_standard_artifact_folder_tree",
            blocker_code="target_conflict",
            recovery_state_class="target_identity_changed",
            summary="The selected Artifact Tree folder or database path already exists.",
        )
    return None


def validate_artifact_tree_contract(artifact_root_path: str | Path) -> tuple[bool, str]:
    root = Path(artifact_root_path)
    if not _has_exact_child(root.parent, root.name):
        return False, "artifact_root_missing_or_wrong_case"
    expected_top = {"Input", "Corpus", "Semantic Release", "Documents", "Error Cases"}
    actual_top = {child.name for child in root.iterdir() if child.is_dir()}
    if actual_top != expected_top:
        missing = sorted(expected_top - actual_top)
        extra = sorted(actual_top - expected_top)
        if missing:
            return False, f"missing_canonical_folder:{missing[0]}"
        return False, f"extra_authoritative_folder:{extra[0]}"
    documents = root / "Documents"
    expected_documents = {
        "logs",
        "normalized",
        "originals",
        "page_images",
        "raw_extracts",
        "requests",
        "structured",
        "validation",
    }
    actual_documents = {child.name for child in documents.iterdir() if child.is_dir()}
    if actual_documents != expected_documents:
        missing = sorted(expected_documents - actual_documents)
        extra = sorted(actual_documents - expected_documents)
        if missing:
            return False, f"missing_canonical_folder:Documents/{missing[0]}"
        return False, f"extra_authoritative_folder:Documents/{extra[0]}"
    for relative in CANONICAL_ARTIFACT_FOLDERS:
        path = root / relative
        if not path.is_dir() or not _path_components_exact(root, relative):
            return False, f"wrongly_cased_or_missing:{relative}"
    return True, "ok"


def create_canonical_artifact_tree_folders(target: DatabaseCreationTarget) -> None:
    root = Path(target.artifact_root_path)
    for relative in CANONICAL_ARTIFACT_FOLDERS:
        (root / relative).mkdir(parents=True, exist_ok=False)


def _has_exact_child(parent: Path, child_name: str) -> bool:
    if not parent.exists():
        return False
    return any(child.name == child_name for child in parent.iterdir())


def _path_components_exact(root: Path, relative: str) -> bool:
    current = root
    for part in Path(relative).parts:
        if not _has_exact_child(current, part):
            return False
        current = current / part
    return True
