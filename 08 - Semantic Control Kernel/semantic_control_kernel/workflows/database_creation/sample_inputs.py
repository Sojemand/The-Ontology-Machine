from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from semantic_control_kernel.types.database_creation import DatabaseCreationBlocker, DatabaseCreationTarget, JsonObject
from semantic_control_kernel.workflows.database_creation.blockers import create_blocker


def sample_refs_under_input(target: DatabaseCreationTarget, sample_refs: Sequence[Mapping[str, Any]]) -> bool:
    return sample_ref_validation_error(target=target, sample_refs=sample_refs) is None


def sample_ref_validation_error(
    *,
    target: DatabaseCreationTarget | None,
    sample_refs: Sequence[Mapping[str, Any]],
) -> str | None:
    if sample_ref_inspection_error(sample_refs) is not None:
        return "sample_inspection_failed"
    seen_sample_ids: set[str] = set()
    seen_paths: set[str] = set()
    input_path = Path(target.input_path).resolve(strict=False) if target is not None else None
    for ref in sample_refs:
        sample_id = str(ref.get("sample_id", "")).strip()
        if not sample_id:
            return "sample_id_missing"
        if sample_id in seen_sample_ids:
            return "duplicate_sample_id"
        seen_sample_ids.add(sample_id)
        path_value = ref.get("path") or ref.get("artifact_path")
        if not path_value:
            return "sample_path_missing"
        candidate = Path(str(path_value)).resolve(strict=False)
        if input_path is not None:
            try:
                candidate.relative_to(input_path)
            except ValueError:
                return "sample_outside_input"
        candidate_key = str(candidate)
        if candidate_key in seen_paths:
            return "duplicate_sample_path"
        seen_paths.add(candidate_key)
        inline_input = ref.get("analyze_sample_input")
        if isinstance(inline_input, Mapping):
            if inline_input.get("schema_version") != "kernel.analyze_sample.input.v1":
                return "invalid_analyze_sample_input"
            if str(inline_input.get("sample_id", "")) != sample_id:
                return "sample_id_mismatch"
            continue
        if not candidate.is_file():
            return "sample_file_missing"
    return None


def sample_ref_inspection_error(sample_refs: Sequence[Mapping[str, Any]]) -> str | None:
    for ref in sample_refs:
        error = ref.get("sample_inspection_error")
        if not isinstance(error, Mapping):
            continue
        for key in ("summary", "message", "code"):
            value = error.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        return "Sample inspection failed before analyze_samples could run."
    return None


def validate_selected_sample_refs(
    *,
    target: DatabaseCreationTarget | None,
    sample_refs: Sequence[Mapping[str, Any]],
    step_id: str,
    sample_subject: str,
) -> DatabaseCreationBlocker | None:
    subject = sample_subject.strip().lower()
    subject_title = subject.capitalize()
    if not sample_refs:
        return create_blocker(
            step_id=step_id,
            function_or_route="analyze_samples",
            blocker_code="input_missing",
            recovery_state_class="expired_pending_interaction",
            summary=f"Custom {subject} creation requires sample files selected through Kernel state.",
        )
    inspection_error = sample_ref_inspection_error(sample_refs)
    if inspection_error is not None:
        return create_blocker(
            step_id=step_id,
            function_or_route="inspect_source_document_sample",
            blocker_code="input_missing",
            recovery_state_class="support_only_unrecoverable",
            summary=f"{subject_title} sample inspection failed before analyze_samples could run: {inspection_error}",
        )
    reason = sample_ref_validation_error(target=target, sample_refs=sample_refs)
    if reason is not None:
        return create_blocker(
            step_id=step_id,
            function_or_route="analyze_samples",
            blocker_code="input_missing",
            recovery_state_class="target_identity_changed",
            summary=f"Selected {subject} sample evidence must be readable analyze-sample input under the active Artifact Tree Input folder.",
        )
    return None


def build_analyze_sample_inputs(
    *,
    target: DatabaseCreationTarget | None,
    sample_refs: Sequence[Mapping[str, Any]],
    step_id: str,
    function_or_route: str,
) -> tuple[list[JsonObject], DatabaseCreationBlocker | None]:
    inspection_error = sample_ref_inspection_error(sample_refs)
    if inspection_error is not None:
        return [], create_blocker(
            step_id=step_id,
            function_or_route=function_or_route,
            blocker_code="input_missing",
            recovery_state_class="support_only_unrecoverable",
            summary=f"Sample inspection failed before analyze_samples could run: {inspection_error}",
        )
    reason = sample_ref_validation_error(target=target, sample_refs=sample_refs)
    if reason is not None:
        return [], create_blocker(
            step_id=step_id,
            function_or_route=function_or_route,
            blocker_code="input_missing",
            recovery_state_class="target_identity_changed"
            if reason in {"sample_outside_input", "sample_file_missing"}
            else "expired_pending_interaction",
            summary=_sample_ref_validation_summary(reason),
        )
    sample_inputs: list[JsonObject] = []
    for ref in sample_refs:
        inline_input = ref.get("analyze_sample_input")
        if isinstance(inline_input, Mapping):
            sample_inputs.append(dict(inline_input))
            continue
        path_value = ref.get("path") or ref.get("artifact_path")
        try:
            payload = json.loads(Path(str(path_value)).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, UnicodeDecodeError) as exc:
            return [], create_blocker(
                step_id=step_id,
                function_or_route=function_or_route,
                blocker_code="input_missing",
                recovery_state_class="target_identity_changed",
                summary=f"Sample evidence could not be read as kernel.analyze_sample.input.v1 JSON: {exc}.",
            )
        if not isinstance(payload, Mapping) or payload.get("schema_version") != "kernel.analyze_sample.input.v1":
            return [], create_blocker(
                step_id=step_id,
                function_or_route=function_or_route,
                blocker_code="input_missing",
                recovery_state_class="target_identity_changed",
                summary="Sample evidence must contain kernel.analyze_sample.input.v1 JSON before analyze_samples runs.",
            )
        if str(payload.get("sample_id", "")) != str(ref.get("sample_id", "")):
            return [], create_blocker(
                step_id=step_id,
                function_or_route=function_or_route,
                blocker_code="input_missing",
                recovery_state_class="target_identity_changed",
                summary="Sample evidence sample_id must match the selected sample ref.",
            )
        sample_inputs.append(dict(payload))
    return sample_inputs, None


def _sample_ref_validation_summary(reason: str) -> str:
    summaries = {
        "sample_id_missing": "Selected sample evidence must include a sample_id.",
        "duplicate_sample_id": "Selected sample evidence must not repeat sample_id values.",
        "sample_path_missing": "Selected sample evidence must include an Artifact Tree Input path.",
        "sample_outside_input": "Selected sample files must live under the active Artifact Tree Input folder.",
        "duplicate_sample_path": "Selected sample evidence must not repeat file paths.",
        "invalid_analyze_sample_input": "Inline sample evidence must use kernel.analyze_sample.input.v1.",
        "sample_id_mismatch": "Inline sample evidence sample_id must match the selected sample ref.",
        "sample_file_missing": "Selected sample evidence must point to an existing file or include inline analyze-sample input.",
        "sample_inspection_failed": "Sample inspection failed before analyze_samples could run.",
    }
    return summaries.get(reason, "Selected sample evidence is invalid.")
