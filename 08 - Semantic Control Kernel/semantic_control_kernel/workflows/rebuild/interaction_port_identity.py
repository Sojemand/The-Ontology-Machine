from __future__ import annotations

from pathlib import Path
from typing import Any

from semantic_control_kernel.repository.paths import path_hash, stable_hash
from semantic_control_kernel.types.rebuild import RebuildWorkflowBlocker


def rebuild_placeholder_identity(workflow_run_id: str) -> dict[str, Any]:
    return {
        "schema_version": "state.target_identity.v1",
        "artifact_root_path_hash": f"pending:{stable_hash(f'{workflow_run_id}:rebuild_artifact_root')}",
        "database_path_hash": f"pending:{stable_hash(f'{workflow_run_id}:rebuild_database')}",
        "target_hash": stable_hash(f"{workflow_run_id}:rebuild_target"),
        "lock_scope": "database_rebuild",
        "workflow_run_id": workflow_run_id,
        "created_from": "kernel.database_rebuild_target_collection.v1",
    }


def rebuild_target_identity(
    workflow_run_id: str,
    artifact_root: str | Path,
    target_database_path: str | Path,
    *,
    release_fingerprint: str = "",
) -> dict[str, Any]:
    artifact_hash = path_hash(artifact_root)
    database_hash = path_hash(target_database_path)
    identity: dict[str, Any] = {
        "schema_version": "state.target_identity.v1",
        "artifact_root_path_hash": artifact_hash,
        "database_path_hash": database_hash,
        "workflow_run_id": workflow_run_id,
        "lock_scope": "database_rebuild",
        "target_hash": stable_hash(f"{artifact_hash}:{database_hash}:{release_fingerprint}:{workflow_run_id}"),
        "created_from": "kernel.database_rebuild_target_collection.v1",
    }
    if release_fingerprint:
        identity["release_fingerprint"] = release_fingerprint
    return identity


def interaction_snapshot_id(workflow_run_id: str, interaction_function: str) -> str:
    return stable_hash(f"{workflow_run_id}:{interaction_function}")


def existing_corpus_databases(corpus_dir: Path, *, excluding: Path) -> tuple[Path, ...]:
    if not corpus_dir.is_dir():
        return ()
    excluded = excluding.resolve(strict=False)
    databases: list[Path] = []
    for path in sorted(corpus_dir.iterdir(), key=lambda item: item.name.casefold()):
        if not path.is_file() or path.suffix.casefold() != ".db":
            continue
        if path.resolve(strict=False) == excluded:
            continue
        databases.append(path.resolve(strict=False))
    return tuple(databases)


def input_blocker(summary: str) -> RebuildWorkflowBlocker:
    return RebuildWorkflowBlocker(
        blocker_code="input_missing",
        step_id="rebuild_collect_interaction",
        function_or_route="database_rebuild_from_artifacts",
        recovery_state_class="expired_pending_interaction",
        user_visible_summary=summary,
    )


def clean_text(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    return text or None


def clean_path(value: object) -> str | None:
    text = clean_text(value)
    if text is None:
        return None
    if len(text) >= 2 and text[0] == text[-1] and text[0] in {'"', "'"}:
        text = text[1:-1].strip()
        if not text:
            return None
    return str(Path(text).resolve(strict=False))


__all__ = [
    "clean_path",
    "clean_text",
    "existing_corpus_databases",
    "input_blocker",
    "interaction_snapshot_id",
    "rebuild_placeholder_identity",
    "rebuild_target_identity",
]
