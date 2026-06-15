from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType

from semantic_control_kernel.policy.merge_policy import DRIFT_PREFLIGHT


WORKFLOW_ENTRIES: tuple[str, ...] = (
    "database_merge_additive_only",
    "empty_databases_merge_path",
    "filled_databases_merge_path",
)

INTERNAL_WORKFLOW_FUNCTIONS: tuple[str, ...] = (
    "merge_database_empty",
    "merge_database_filled_additive",
    "merge_taxonomy_and_projections_additive",
    "reconcile_merged_semantic_release",
    "reconcile_merged_database",
    "write_combined_database",
    "fill_artifact_folder_tree",
    "backfill_sql",
)


@dataclass(frozen=True)
class MergeStep:
    step_id: str
    operation: str
    adapter_or_port: str
    progress_event: str
    resume_point: str

    def to_dict(self) -> dict[str, str]:
        return {
            "adapter_or_port": self.adapter_or_port,
            "operation": self.operation,
            "progress_event": self.progress_event,
            "resume_point": self.resume_point,
            "step_id": self.step_id,
        }


@dataclass(frozen=True)
class MergeRoute:
    workflow_tool: str
    step_ids: tuple[str, ...]
    final_state: str

    def to_dict(self) -> dict[str, object]:
        return {
            "final_state": self.final_state,
            "step_ids": list(self.step_ids),
            "workflow_tool": self.workflow_tool,
        }


def _s(step_id: str, operation: str, adapter_or_port: str, progress_event: str, resume_point: str) -> MergeStep:
    return MergeStep(
        step_id=step_id,
        operation=operation,
        adapter_or_port=adapter_or_port,
        progress_event=progress_event,
        resume_point=resume_point,
    )


STEP_CATALOG: tuple[MergeStep, ...] = (
    _s("resolving_sources", "choose_merge_database_count_then_choose_databases_to_merge", "UserInteractionAdapter", "resolving_sources", "before selection"),
    _s("classifying_merge_route", "database_merge_additive_only", "Kernel route classifier", "classifying_merge_route", "after selection"),
    _s("creating_target_artifact_tree", "create_standard_artifact_folder_tree", "WorkspaceAdapter.prepare_artifact_tree", "creating_target_artifact_tree", "after target tree creation"),
    _s("creating_target_database", "create_empty_database", "CorpusAdapter.create_empty_database", "creating_target_database", "after target database creation"),
    _s("running_empty_merge", "merge_database_empty", "MergeAdapter.merge_empty_databases", "running_empty_merge", "after empty merge"),
    _s("filling_artifact_tree", "fill_artifact_folder_tree", "compatibility label", "filling_artifact_tree", "after artifact fill"),
    _s("running_filled_merge", "merge_database_filled_additive", "MergeAdapter.merge_filled_databases", "running_filled_merge", "after filled SQL merge"),
    _s("building_collision_manifest", "merge_taxonomy_and_projections_additive", "MergeAdapter.merge_semantic_release_candidates", "building_collision_manifest", "after collision manifest"),
    _s("awaiting_reconciliation", "reconcile_merged_database", "Kernel merge reconciliation dialog", "awaiting_reconciliation", "after reconciliation"),
    _s("writing_combined_database", "write_combined_database", "compatibility label", "writing_combined_database", "after combined DB write"),
    _s("attaching_semantic_release", "attach_custom_semantic_release_to_database", "Kernel attach-state write", "attaching_semantic_release", "after release attach"),
    _s("activating_semantic_release", "activate_semantic_release", "SemanticReleaseAdapter.activate_semantic_release", "activating_semantic_release", "after activation"),
    _s("completed", "merge_finalization_receipt", "Kernel repository", "completed", "no resume"),
)

STEP_BY_ID = MappingProxyType({step.step_id: step for step in STEP_CATALOG})

ROUTES: tuple[MergeRoute, ...] = (
    MergeRoute(
        workflow_tool="empty_databases_merge_path",
        step_ids=(
            "creating_target_artifact_tree",
            "creating_target_database",
            "running_empty_merge",
            "building_collision_manifest",
            "awaiting_reconciliation",
            "attaching_semantic_release",
            "activating_semantic_release",
            "completed",
        ),
        final_state="semantic_release_active",
    ),
    MergeRoute(
        workflow_tool="filled_databases_merge_path",
        step_ids=(
            "creating_target_artifact_tree",
            "creating_target_database",
            "running_filled_merge",
            "building_collision_manifest",
            "awaiting_reconciliation",
            "attaching_semantic_release",
            "activating_semantic_release",
            "completed",
        ),
        final_state="semantic_release_active",
    ),
)

ROUTE_BY_TOOL = MappingProxyType({route.workflow_tool: route for route in ROUTES})


def route_sequence(workflow_tool: str) -> tuple[str, ...]:
    try:
        return ROUTE_BY_TOOL[workflow_tool].step_ids
    except KeyError as exc:
        raise ValueError(f"Unknown Phase 12 merge workflow: {workflow_tool}") from exc
