from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Sequence

from semantic_control_kernel.repository.paths import stable_hash
from semantic_control_kernel.types.merge import (
    MERGE_SELECTION_REQUIRED_FIELDS,
    MERGE_SOURCE_REQUIRED_FIELDS,
    PROJECTION_MERGE_MODE_VALUES,
    MergeWorkflowBlocker,
)
from semantic_control_kernel.validation.merge_validation_common import norm_path, require_fields, stable_payload, target_conflict


def validate_source_count(sources: Sequence[Mapping[str, Any]]) -> MergeWorkflowBlocker | None:
    if len(sources) < 2:
        return MergeWorkflowBlocker(
            blocker_code="input_missing",
            step_id="source_selection",
            function_or_route="database_merge_additive_only",
            recovery_state_class="support_only_unrecoverable",
            user_visible_summary="At least two source databases are required for additive merge.",
        )
    return None


def validate_selection_contract(selection: Mapping[str, Any]) -> None:
    require_fields(selection, MERGE_SELECTION_REQUIRED_FIELDS, "kernel.database_merge_selection.v1")
    sources = selection.get("source_databases")
    if not isinstance(sources, list) or len(sources) < 2:
        raise ValueError("kernel.database_merge_selection.v1 requires at least two source_databases.")
    for source in sources:
        _validate_source_entry(source)
    validate_target_database_under_root(selection)
    if selection.get("projection_merge_mode") not in PROJECTION_MERGE_MODE_VALUES:
        raise ValueError("projection_merge_mode is invalid.")
    if selection.get("selection_fingerprint") != selection_fingerprint(selection):
        raise ValueError("selection_fingerprint does not match selection payload.")


def selection_fingerprint(selection: Mapping[str, Any]) -> str:
    payload = {key: value for key, value in selection.items() if key != "selection_fingerprint"}
    return stable_hash(repr(stable_payload(payload)))


def validate_no_mixed_sources(selection: Mapping[str, Any]) -> MergeWorkflowBlocker | None:
    states = {source.get("source_state") for source in selection.get("source_databases", []) if isinstance(source, Mapping)}
    if states <= {"empty", "filled"}:
        return None
    return MergeWorkflowBlocker(
        blocker_code="source_state_unknown",
        step_id="classifying_merge_route",
        function_or_route="database_merge_additive_only",
        recovery_state_class="none",
        user_visible_summary="Merge source states must be empty or filled before additive merge can run.",
        diagnostics=({"source_states": sorted(str(item) for item in states)},),
    )


def validate_target_not_source(selection: Mapping[str, Any]) -> MergeWorkflowBlocker | None:
    target_root = norm_path(selection.get("target_artifact_root"))
    target_db = norm_path(selection.get("target_database_path"))
    for source in selection.get("source_databases", []):
        if not isinstance(source, Mapping):
            continue
        if target_root and target_root == norm_path(source.get("source_artifact_root")):
            return target_conflict("target_artifact_root")
        if target_db and target_db == norm_path(source.get("source_database_path")):
            return target_conflict("target_database_path")
    return None


def validate_target_database_under_root(selection: Mapping[str, Any]) -> None:
    target_root = selection.get("target_artifact_root")
    target_db = selection.get("target_database_path")
    if not target_root or not target_db:
        raise ValueError("target_artifact_root and target_database_path are required.")
    corpus = (Path(str(target_root)).resolve(strict=False) / "Corpus").resolve(strict=False)
    target = Path(str(target_db)).resolve(strict=False)
    try:
        target.relative_to(corpus)
    except ValueError as exc:
        raise ValueError("target_database_path must stay inside target_artifact_root/Corpus.") from exc


def _validate_source_entry(source: object) -> None:
    if not isinstance(source, Mapping):
        raise ValueError("source_databases entries must be objects.")
    require_fields(source, MERGE_SOURCE_REQUIRED_FIELDS, "kernel.database_merge_selection.v1.source_databases[]")
    if source["source_state"] not in {"empty", "filled"}:
        raise ValueError("source_state must be empty or filled.")
