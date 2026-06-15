from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

SCHEMA_VERSION = "kernel.workflow_explanation_context.v1"


def build_workflow_explanation_context(
    execution: Any,
    *,
    step_facts: Mapping[str, Mapping[str, Any]],
    current_state_summary: str | None = None,
    unchanged_artifacts: Sequence[Mapping[str, Any]] = (),
    changed_artifacts: Sequence[Mapping[str, Any]] = (),
    evidence_refs: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    """Build a reusable explanation provenance payload for resumable workflows."""

    completed_total = _unique_strings(getattr(execution, "completed_step_ids", ()))
    completed_at_start = _unique_strings(getattr(execution, "completed_step_ids_at_run_start", ()))
    satisfied_preconditions = _unique_strings(getattr(execution, "satisfied_precondition_step_ids", ()))
    completed_at_start_set = set(completed_at_start)
    performed_this_run = [step_id for step_id in completed_total if step_id not in completed_at_start_set]
    already_available_step_ids = [step_id for step_id in completed_at_start if step_id in set(completed_total)]

    return {
        "schema_version": SCHEMA_VERSION,
        "workflow_run_id": str(getattr(execution, "workflow_run_id", "") or ""),
        "workflow_tool": str(getattr(execution, "workflow_tool", "") or ""),
        "current_state_summary": current_state_summary if current_state_summary is not None else str(getattr(execution, "final_state", "") or ""),
        "completed_step_ids_total": completed_total,
        "completed_step_ids_at_run_start": completed_at_start,
        "completed_step_ids_this_run": performed_this_run,
        "satisfied_precondition_step_ids": satisfied_preconditions,
        "already_available": _fact_items(already_available_step_ids, step_facts, provenance="already_available"),
        "performed_this_run": _fact_items(performed_this_run, step_facts, provenance="performed_this_run"),
        "unchanged_artifacts": [dict(item) for item in unchanged_artifacts],
        "changed_artifacts": [dict(item) for item in changed_artifacts],
        "evidence_refs": [dict(item) for item in evidence_refs],
        "provenance_policy": {
            "completed_step_ids_at_run_start_are_not_new_work": True,
            "completed_step_ids_this_run_are_the_only_steps_the_agent_may_describe_as_newly_performed": True,
        },
    }


def explanation_preferred_structure(
    explanation_context: Mapping[str, Any],
    *,
    default_structure: Sequence[str],
    resumed_structure: Sequence[str],
) -> list[str]:
    if explanation_context.get("already_available"):
        return list(resumed_structure)
    return list(default_structure)


def performed_step_ids(execution: Any) -> tuple[str, ...]:
    completed_at_start = set(_unique_strings(getattr(execution, "completed_step_ids_at_run_start", ())))
    return tuple(step_id for step_id in _unique_strings(getattr(execution, "completed_step_ids", ())) if step_id not in completed_at_start)


def already_available_step_ids(execution: Any) -> tuple[str, ...]:
    completed_total = set(_unique_strings(getattr(execution, "completed_step_ids", ())))
    return tuple(step_id for step_id in _unique_strings(getattr(execution, "completed_step_ids_at_run_start", ())) if step_id in completed_total)


def _fact_items(
    step_ids: Sequence[str],
    step_facts: Mapping[str, Mapping[str, Any]],
    *,
    provenance: str,
) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for step_id in step_ids:
        fact = step_facts.get(step_id)
        if fact is None:
            continue
        item = {
            "step_id": step_id,
            "provenance": provenance,
            "fact_id": str(fact.get("fact_id") or step_id),
            "label": str(fact.get("label") or step_id),
        }
        artifact_keys = fact.get("artifact_keys")
        if isinstance(artifact_keys, Sequence) and not isinstance(artifact_keys, (str, bytes)):
            item["artifact_keys"] = [str(key) for key in artifact_keys]
        items.append(item)
    return items


def _unique_strings(values: Sequence[Any]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        text = str(value or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
    return result
