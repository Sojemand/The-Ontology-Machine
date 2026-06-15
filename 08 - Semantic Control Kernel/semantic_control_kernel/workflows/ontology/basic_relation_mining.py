from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from semantic_control_kernel.repository.paths import canonical_path_text
from semantic_control_kernel.types.adapter_results import AdapterCallResult, MissingCapabilityBlocker
from semantic_control_kernel.types.ontology import OntologyWorkflowBlocker


def basic_relation_mining(
    corpus_adapter: object,
    *,
    target_database_path: str | Path,
    dry_run: bool = False,
) -> tuple[dict[str, Any] | None, object | None, OntologyWorkflowBlocker | None]:
    database_path = str(Path(target_database_path).resolve(strict=False))
    result = corpus_adapter.basic_relation_mining(
        {
            "corpus_db_path": database_path,
            "dry_run": dry_run,
            "target_identity": {
                "target_database_path": database_path,
                "database_path": database_path,
            },
        }
    )
    blocker = _blocker_from_result(result, "basic_relation_mining")
    if blocker is not None:
        return None, result, blocker
    output = _adapter_output(result)
    proven_path = output.get("database_path") or output.get("corpus_db_path")
    if canonical_path_text(proven_path or "") != canonical_path_text(database_path):
        return None, result, OntologyWorkflowBlocker(
            blocker_code="ontology_primitive_insufficient",
            step_id="basic_relation_mining",
            function_or_route="basic_relation_mining",
            recovery_state_class="support_only_unrecoverable",
            user_visible_summary="Corpus Builder did not prove the exact Kernel target database path for basic relation mining.",
        )
    return output, result, None


def _blocker_from_result(result: object, function_name: str) -> OntologyWorkflowBlocker | None:
    if isinstance(result, MissingCapabilityBlocker):
        payload = result.to_dict()
        return OntologyWorkflowBlocker(
            blocker_code="pipeline_capability_missing",
            step_id=function_name,
            function_or_route=str(payload.get("kernel_function", function_name)),
            recovery_state_class=str(payload.get("recovery_state_class", "support_only_unrecoverable")),
            user_visible_summary=str(payload.get("blocking_reason", "Required Pipeline capability is missing.")),
            diagnostics=tuple(dict(item) for item in payload.get("diagnostics", []) if isinstance(item, Mapping)),
        )
    if isinstance(result, AdapterCallResult) and result.status != "ok":
        return OntologyWorkflowBlocker(
            blocker_code=result.status,
            step_id=function_name,
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


__all__ = ["basic_relation_mining"]
