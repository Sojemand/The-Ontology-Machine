from __future__ import annotations

from typing import Mapping

from semantic_control_kernel.repository.errors import ResumeStateNotFoundError
from semantic_control_kernel.repository.event_store import MirrorEventStore
from semantic_control_kernel.repository.interaction_store import InteractionRequestStore
from semantic_control_kernel.repository.paths import StatePaths
from semantic_control_kernel.repository.run_store import WorkflowRunStore
from semantic_control_kernel.services.kernel_mirror_event_service import KernelMirrorEventService
from semantic_control_kernel.services.user_interaction_service import KernelUserInteractionService
from semantic_control_kernel.types.events import UserInteractionRequest
from semantic_control_kernel.types.merge import MergeWorkflowBlocker
from semantic_control_kernel.workflows.merge.source_registry import (
    MergeSourceResolutionError,
    resolve_merge_source_descriptors,
)
from semantic_control_kernel.workflows.merge.interaction_payloads import (
    clean_database_paths,
    clean_path,
    interaction_snapshot_id,
    merge_placeholder_identity,
    merge_target_identity,
    options_for,
    prefilled_values_for,
    source_resolution_blocker,
    summary_for,
    target_resolution_blocker,
    title_for,
)
from semantic_control_kernel.workflows.merge.interaction_port_state import (
    MERGE_INTERACTION_FUNCTIONS,
    InlineMergeClientFrontendEventSink,
    MergeInteractionInputs,
    MergeInteractionProgress,
    clean_projection_merge_mode,
    clean_source_count,
)


class MergeInteractionPort:
    def __init__(
        self,
        state_paths: StatePaths,
        *,
        interaction_store: InteractionRequestStore | None = None,
        workflow_run_store: WorkflowRunStore | None = None,
        user_interaction_service: KernelUserInteractionService | None = None,
    ) -> None:
        self.state_paths = state_paths
        self.interaction_store = interaction_store or InteractionRequestStore(state_paths)
        self.workflow_run_store = workflow_run_store or WorkflowRunStore(state_paths)
        self.user_interaction_service = user_interaction_service or KernelUserInteractionService(
            interaction_store=self.interaction_store,
            mirror_event_service=KernelMirrorEventService(MirrorEventStore(state_paths)),
            event_sink=InlineMergeClientFrontendEventSink(),
            workflow_run_store=self.workflow_run_store,
        )

    def collect_merge_inputs(
        self,
        *,
        workflow_tool: str,
        workflow_run_id: str,
    ) -> MergeInteractionInputs | MergeWorkflowBlocker | None:
        self._ensure_workflow_run(workflow_tool, workflow_run_id)
        progress = self._progress_from_recorded_responses(workflow_run_id)
        if progress.next_interaction_function is not None:
            if self.pending_merge_request(workflow_run_id) is None:
                self._open_next_interaction(workflow_tool, workflow_run_id, progress)
            return None
        try:
            selected_sources = resolve_merge_source_descriptors(
                self.state_paths,
                progress.selected_database_paths,
            )
        except MergeSourceResolutionError as exc:
            return source_resolution_blocker(str(exc))
        target_root = clean_path(progress.target_artifact_root)
        if target_root is None:
            return target_resolution_blocker("Merge target Artifact Tree root was not provided by Kernel/UI state.")
        self.workflow_run_store.mark_run_running(
            workflow_run_id,
            target_identity=merge_target_identity(workflow_run_id, selected_sources, target_root),
            resume_state_ref="",
        )
        return MergeInteractionInputs(
            selected_sources=selected_sources,
            target_artifact_root=target_root,
            projection_merge_mode=clean_projection_merge_mode(progress.projection_merge_mode),
            selected_by_interaction_id=progress.source_interaction_request_id or "interaction_merge_selection",
        )

    def pending_merge_request(self, workflow_run_id: str) -> UserInteractionRequest | None:
        for request in self.interaction_store.list_pending_interactions_for_workflow(workflow_run_id):
            if request.payload.get("interaction_function") in MERGE_INTERACTION_FUNCTIONS:
                return request
        return None

    def pending_merge_request_ref(self, workflow_run_id: str) -> str | None:
        request = self.pending_merge_request(workflow_run_id)
        if request is None:
            return None
        return f"pending_interactions/active/{request.payload['interaction_request_id']}.json"

    def pending_merge_summary(self, workflow_run_id: str) -> str:
        request = self.pending_merge_request(workflow_run_id)
        if request is None:
            return "The Kernel is waiting for database merge input."
        return str(request.payload.get("user_visible_summary") or "The Kernel is waiting for database merge input.")

    def _ensure_workflow_run(self, workflow_tool: str, workflow_run_id: str) -> None:
        try:
            self.workflow_run_store.get_run(workflow_run_id)
        except ResumeStateNotFoundError:
            self.workflow_run_store.create_run(
                workflow_tool,
                merge_placeholder_identity(workflow_run_id),
                "kernel_database_merge_selection_collection",
                workflow_run_id=workflow_run_id,
            )

    def _progress_from_recorded_responses(self, workflow_run_id: str) -> MergeInteractionProgress:
        source_count: int | None = None
        selected_paths: tuple[str, ...] = ()
        selected_request_id: str | None = None
        target_root: str | None = None
        projection_merge_mode: str | None = None
        records = self.interaction_store.list_records_for_workflow(workflow_run_id)
        records.sort(key=lambda record: str(record.created_at))
        for record in records:
            request = record.interaction_request if isinstance(record.interaction_request, Mapping) else {}
            response = record.get("interaction_response", {}) if isinstance(record.get("interaction_response"), Mapping) else {}
            if record.status != "submitted":
                continue
            interaction_function = str(request.get("interaction_function") or "")
            if interaction_function == "choose_merge_database_count":
                parsed_count = clean_source_count(response.get("text_value"))
                if parsed_count is not None:
                    source_count = parsed_count
            elif interaction_function == "choose_databases_to_merge":
                selected_paths = clean_database_paths(response.get("selected_database_paths"))
                if source_count is None and len(selected_paths) >= 2:
                    source_count = len(selected_paths)
                selected_request_id = str(request.get("interaction_request_id") or "") or selected_request_id
            elif interaction_function == "choose_new_artifact_root_folder":
                target_root = clean_path(response.get("path_value"))
            elif interaction_function == "choose_merge_projection_mode":
                projection_merge_mode = clean_projection_merge_mode(response.get("choice_id"))
        return MergeInteractionProgress(
            source_count=source_count,
            selected_database_paths=selected_paths,
            source_interaction_request_id=selected_request_id,
            target_artifact_root=target_root,
            projection_merge_mode=projection_merge_mode,
        )

    def _open_next_interaction(
        self,
        workflow_tool: str,
        workflow_run_id: str,
        progress: MergeInteractionProgress,
    ) -> None:
        interaction_function = str(progress.next_interaction_function or "choose_databases_to_merge")
        self.user_interaction_service.request_interaction(
            interaction_function=interaction_function,
            workflow_run_id=workflow_run_id,
            function_or_route=workflow_tool,
            target_identity=merge_placeholder_identity(workflow_run_id),
            state_snapshot_identity={"state_snapshot_id": interaction_snapshot_id(workflow_run_id, interaction_function)},
            user_visible_title=title_for(interaction_function),
            user_visible_summary=summary_for(interaction_function, progress.source_count or len(progress.selected_database_paths)),
            options=options_for(self.state_paths, interaction_function),
            prefilled_values=prefilled_values_for(
                interaction_function,
                progress.selected_database_paths,
                source_count=progress.source_count or 0,
            ),
        )
