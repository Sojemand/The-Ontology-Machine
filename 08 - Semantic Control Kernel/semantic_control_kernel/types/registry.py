from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping

from semantic_control_kernel.types.analysis import (
    AnalyzeSampleInput,
    CreateProjectionsToSampleAnalysesInput,
    CreateTaxonomyToSampleAnalysesInput,
    ProjectionsToSampleAnalyses,
    SampleAnalyses,
    TaxonomyProjectionAuthoringView,
    TaxonomyToSampleAnalyses,
)
from semantic_control_kernel.types.base import KernelContract, make_contract_type
from semantic_control_kernel.types.events import (
    ClientFrontendEvent,
    ClientFrontendEventAck,
    ClientFrontendEventBatch,
    MirrorEvent,
    ProgressEvent,
    UserInteractionRequest,
    UserInteractionResponse,
)
from semantic_control_kernel.types.identity import (
    InterpreterRequestViewFileRef,
    InterpreterRequestViewVisionRef,
)
from semantic_control_kernel.types.llm_artifacts import LLMResponseCapture, LLMPromptSnapshot
from semantic_control_kernel.types.merge import (
    DatabaseMergeCollisionManifest,
    DatabaseMergeIdMap,
    DatabaseMergeSelection,
)
from semantic_control_kernel.types.rebuild import DatabaseRebuildManifest
from semantic_control_kernel.types.receipts import (
    ConfirmationReceipt,
    ConfirmationRequest,
    DatabaseMergeReconciliationReceipt,
    OperationReceipt,
    RecoveryReceipt,
)
from semantic_control_kernel.types.recovery import RecoveryOption
from semantic_control_kernel.types.resume import ResumeOption
from semantic_control_kernel.types.state import (
    ActiveDatabaseState,
    DatabaseArtifactBinding,
    LockState,
    PipelineBatchManifest,
    RecordSemanticMaterializationRef,
    SemanticReleaseAttachState,
    WorkflowResumeState,
)
from semantic_control_kernel.types.update_states import (
    CreateProjectionsUpdateStateInput,
    CreateTaxonomyUpdateStateInput,
)


DefaultTaxonomyProjectionlessReleaseState = make_contract_type(
    "DefaultTaxonomyProjectionlessReleaseState",
    "kernel.default_taxonomy_projectionless_release_state.v1",
    __name__,
)

WorkflowExplanationContext = make_contract_type(
    "WorkflowExplanationContext",
    "kernel.workflow_explanation_context.v1",
    __name__,
)


@dataclass(frozen=True)
class ContractRegistryEntry:
    schema_version: str
    python_type: type[KernelContract]
    source_spec: str
    producer: str
    consumers: tuple[str, ...]
    persistence: str
    required_fields: tuple[str, ...]
    optional_fields: tuple[str, ...]
    extension_policy: str
    validation_depth: str


def _fields(*fields: str) -> tuple[str, ...]:
    return fields


def _consumers(value: str) -> tuple[str, ...]:
    return tuple(part.strip() for part in value.split(",") if part.strip())


def _entry(
    schema_version: str,
    python_type: type[KernelContract],
    producer: str,
    consumers: str,
    persistence: str,
    required_fields: tuple[str, ...],
    optional_fields: tuple[str, ...],
    validation_depth: str,
) -> ContractRegistryEntry:
    extension_policy = "reference_only" if validation_depth == "reference_only" else "closed_object"
    return ContractRegistryEntry(
        schema_version=schema_version,
        python_type=python_type,
        source_spec="11_kernel_internal_data_contracts.md",
        producer=producer,
        consumers=_consumers(consumers),
        persistence=persistence,
        required_fields=required_fields,
        optional_fields=optional_fields,
        extension_policy=extension_policy,
        validation_depth=validation_depth,
    )


_ENTRIES: tuple[ContractRegistryEntry, ...] = (
    _entry("interpreter_request_view_vision.v1", InterpreterRequestViewVisionRef, "scan/image route request builder", "analyze sample input adapter", "no separate artifact", _fields(), _fields(), "reference_only"),
    _entry("interpreter_request_view_file.v1", InterpreterRequestViewFileRef, "born-digital/file route request builder", "analyze sample input adapter", "no separate artifact", _fields(), _fields(), "reference_only"),
    _entry("kernel.analyze_sample.input.v1", AnalyzeSampleInput, "route-normalization adapter", "analyze_samples LLM call", "sa/<analysis_run_id>/in/<sample_id>/input.json", _fields("schema_version", "sample_id", "source_ref", "route", "document", "completeness"), _fields(), "closed_top_level"),
    _entry("kernel.active_database_state.v1", ActiveDatabaseState, "KernelStateResolver", "state table, workflows, confirmations, locks, adapters", "receipt/resume snapshots only; reproducible from owner evidence", _fields("schema_version", "state_snapshot_id", "artifact_tree", "active_database", "database_emptiness", "semantic_release_state", "blocking_reasons"), _fields("attached_release", "active_release", "runtime_locale", "active_lock_refs", "pending_confirmation_refs", "pending_interaction_refs", "evidence_refs"), "closed_deep"),
    _entry("kernel.database_artifact_binding.v1", DatabaseArtifactBinding, "DatabaseArtifactBindingRegistry and database creation/rebuild routes", "state resolver, run, merge enrichment, rebuild", "Phase 3 owner decision; Kernel registry unless Phase 3 changes with proof", _fields("schema_version", "database_path", "database_id", "artifact_root_path", "corpus_path", "input_path", "documents_path", "error_cases_path", "semantic_release_path", "binding_provenance", "created_at", "updated_at"), _fields("source_workspace_identity", "last_verified_semantic_release_path", "last_verified_semantic_release_fingerprint"), "closed_deep"),
    _entry("kernel.semantic_release_attach_state.v1", SemanticReleaseAttachState, "attach semantic release functions", "activate, resolver, merge/rebuild finalization", "AttachStateStore", _fields("schema_version", "release_path", "release_id", "release_version", "release_fingerprint", "runtime_locale", "target_database_path", "attach_receipt_id", "attached_at", "pointer_owner"), _fields(), "closed_deep"),
    _entry("kernel.default_taxonomy_projectionless_release_state.v1", DefaultTaxonomyProjectionlessReleaseState, "empty_database_default_taxonomy_no_projections", "resume, projection authoring, audit, final notices", "<artifact_root>/Semantic Release/staged/taxonomy/default_taxonomy_without_projections/projectionless_release_state.json", _fields("schema_version", "workflow_run_id", "workflow_tool", "target_identity", "artifact_root_path", "database_path", "semantic_release_path", "source_default_release_ref", "projectionless_release_ref", "taxonomy_ref", "removed_projection_refs", "remaining_projection_refs", "missing_component_type", "completeness_state", "adapter_receipt_refs"), _fields("created_at"), "closed_deep"),
    _entry("kernel.pipeline_batch_manifest.v1", PipelineBatchManifest, "pipeline_run", "pipeline audit, rebuild audit", "Documents/logs/pipeline_batches/<pipeline_batch_id>/pipeline_batch_manifest.json and/or database batch table", _fields("schema_version", "pipeline_batch_id", "workflow_run_id", "created_at", "finalized_at", "batch_kind", "batch_status", "active_database", "artifact_root", "semantic_release", "active_projections", "input_files", "owner_run_refs", "output_artifacts", "materialized_records", "record_counts", "cleanup_eligibility", "manifest_fingerprint"), _fields("support_bundle_ref"), "closed_deep"),
    _entry("kernel.record_semantic_materialization_ref.v1", RecordSemanticMaterializationRef, "pipeline_run materialization writer", "pipeline audit and rebuild audit", "database records or payload metadata", _fields("schema_version", "pipeline_batch_id", "document_id", "record_id", "semantic_release_id", "semantic_release_version", "release_fingerprint", "taxonomy_fingerprint", "projection_id", "projection_fingerprint"), _fields(), "closed_deep"),
    _entry("kernel.database_merge_selection.v1", DatabaseMergeSelection, "merge source selection route", "merge preflight, locks, target creation, reconciliation, audit", "<target_artifact_root>/Documents/logs/merge_runs/<merge_run_id>/merge_selection.json", _fields("schema_version", "merge_run_id", "created_at", "selected_by_interaction_id", "source_databases", "target_artifact_root", "target_database_path", "merge_route", "projection_merge_mode", "selection_fingerprint"), _fields(), "closed_deep"),
    _entry("kernel.database_merge_collision_manifest.v1", DatabaseMergeCollisionManifest, "merge routes and reconcile helpers", "reconciliation, confirmations, audit", "<target_artifact_root>/Documents/logs/merge_runs/<merge_run_id>/merge_collision_manifest.json", _fields("schema_version", "merge_run_id", "merge_route", "created_at", "updated_at", "source_databases", "target_artifact_root", "target_database_path", "duplicate_policy", "collisions", "resolution_summary", "manifest_revision", "manifest_fingerprint"), _fields(), "closed_deep"),
    _entry("kernel.database_merge_id_map.v1", DatabaseMergeIdMap, "filled additive merge/write combined database", "reconcile and audit", "<target_artifact_root>/Documents/logs/merge_runs/<merge_run_id>/merge_id_map.json", _fields("schema_version", "merge_run_id", "created_at", "source_databases", "target_database_path", "mappings", "record_count", "map_fingerprint"), _fields(), "closed_deep"),
    _entry("kernel.database_merge_reconciliation_receipt.v1", DatabaseMergeReconciliationReceipt, "merge reconciliation dialog", "merge finalization, activation, recovery, audit", "<target_artifact_root>/Documents/logs/merge_runs/<merge_run_id>/merge_reconciliation_receipt.json when user decisions were required", _fields("schema_version", "merge_run_id", "reconciliation_receipt_id", "collision_manifest_ref", "selected_resolutions", "target_identity", "state_snapshot_identity", "created_at", "manifest_revision_before", "manifest_revision_after", "updated_collision_manifest_ref", "result_status", "receipt_fingerprint"), _fields("confirmation_receipt_refs", "workflow_run_id"), "closed_deep"),
    _entry("kernel.database_rebuild_manifest.v1", DatabaseRebuildManifest, "rebuild-from-artifacts workflow", "activation, audit, support, later merge checks", "<artifact_root>/Documents/logs/rebuild_runs/<rebuild_run_id>/rebuild_manifest.json", _fields("schema_version", "rebuild_run_id", "workflow_run_id", "artifact_root", "target_database_path", "loaded_semantic_release_id", "loaded_semantic_release_version", "loaded_release_fingerprint", "corpus_builder_run_ref", "embedding_policy", "embedding_result", "activation_receipt_id", "record_count", "created_at", "finalized_at", "manifest_fingerprint"), _fields("overwrite_receipt_id", "adapter_call_refs"), "closed_deep"),
    _entry("kernel.confirmation_request.v1", ConfirmationRequest, "ConfirmationService", "UserInteractionAdapter, host surface", "WorkflowResumeStore while pending", _fields("schema_version", "confirmation_request_id", "workflow_run_id", "function_or_route", "target_identity", "state_snapshot_identity", "explanation_text", "risk_class", "confirmation_scope", "expiration_policy", "required_receipt_shape"), _fields(), "closed_deep"),
    _entry("kernel.confirmation_receipt.v1", ConfirmationReceipt, "UserInteractionAdapter or host surface", "ConfirmationService, LockStore, mutating functions, adapters", "ReceiptStore", _fields("schema_version", "confirmation_receipt_id", "confirmation_request_id", "confirmed_target_identity", "confirmed_state_snapshot_identity", "user_decision", "confirmed_at", "explanation_hash", "host_surface_identity"), _fields(), "closed_deep"),
    _entry("kernel.user_interaction_request.v1", UserInteractionRequest, "KernelUserInteractionService", "Client Frontend event sink, InteractionRequestStore, workflow resume", "InteractionRequestStore while pending", _fields("schema_version", "interaction_request_id", "workflow_run_id", "function_or_route", "interaction_function", "interaction_kind", "dialog_type", "target_identity", "state_snapshot_identity", "user_visible_title", "user_visible_summary", "response_shape", "expiration_policy", "created_at"), _fields("options", "prefilled_values", "mirror_event_id", "recovery_id", "recovery_dialog_type", "risk_class", "confirmation_request_id"), "closed_deep"),
    _entry("kernel.user_interaction_response.v1", UserInteractionResponse, "Client Frontend event sink or fake sink", "KernelUserInteractionService, workflow resume, confirmation service", "InteractionRequestStore history; confirmation responses also create confirmation receipts", _fields("schema_version", "interaction_response_id", "interaction_request_id", "response_status", "target_identity", "state_snapshot_identity", "host_surface_identity", "submitted_at"), _fields("path_value", "text_value", "choice_id", "selected_database_paths", "confirmation_decision", "recovery_id", "cancellation_reason"), "closed_deep"),
    _entry("kernel.client_frontend_event.v1", ClientFrontendEvent, "KernelUserInteractionService, workflow runner, recovery service", "Client Frontend event sink", "transient event sink payload; mirrored through progress or mirror stores", _fields("schema_version", "frontend_event_id", "frontend_event_kind", "mirror_event_id", "created_at"), _fields("interaction_request", "progress_event", "mirror_event", "tool_availability"), "closed_deep"),
    _entry("kernel.client_frontend_event_ack.v1", ClientFrontendEventAck, "Client Frontend event sink", "Kernel event emitter", "no persistence unless ack fails", _fields("schema_version", "frontend_event_id", "accepted", "host_surface_identity", "acknowledged_at"), _fields("rejection_reason"), "closed_deep"),
    _entry("kernel.client_frontend_event_batch.v1", ClientFrontendEventBatch, "Client Frontend HTTP bridge", "Client Frontend browser", "HTTP response only", _fields("schema_version", "cursor", "events"), _fields(), "closed_deep"),
    _entry("kernel.operation_receipt.v1", OperationReceipt, "state-changing Kernel functions", "audit, resume, reports, resolver, workflow steps", "ReceiptStore", _fields("schema_version", "operation_receipt_id", "function_name", "workflow_run_id", "target_identity_before", "target_identity_after", "input_artifact_refs", "output_artifact_refs", "final_kernel_state", "created_at"), _fields("pipeline_adapter_receipts"), "closed_deep"),
    _entry("kernel.lock_state.v1", LockState, "LockStore", "resolver, confirmations, adapters, resume", "LockStore", _fields("schema_version", "lock_id", "lock_type", "target_identity", "owner_workflow_run_id", "acquired_at", "expiry_policy", "status"), _fields("released_at", "failure_reason", "release_reason", "liveness_evidence"), "closed_deep"),
    _entry("kernel.workflow_resume_state.v1", WorkflowResumeState, "WorkflowResumeStore", "workflow entries, confirmations, resolver", "WorkflowResumeStore", _fields("schema_version", "workflow_run_id", "paused_function", "state_snapshot_identity", "pending_confirmation_refs", "held_lock_refs", "selected_targets", "next_expected_transition", "created_at", "updated_at"), _fields("pending_interaction_refs", "expires_at", "support_bundle_ref"), "closed_deep"),
    _entry("kernel.resume_option.v1", ResumeOption, "ResumeOptionService", "Agent support/control resume selection, Client Frontend tool context", "derived from WorkflowResumeStore; not stored as primary state", _fields("schema_version", "resume_option_ref", "workflow_ref", "resume_family", "source_workflow_tool", "continuation_workflow_tool", "state_snapshot_id", "target_identity", "target_summary", "label", "description", "effect", "risk_class", "status", "agent_tool", "agent_instruction"), _fields(), "closed_deep"),
    _entry("kernel.workflow_explanation_context.v1", WorkflowExplanationContext, "workflow final-notice builders", "mirror agent_explanation_guidance, Pipeline Manager Agent, audit/support", "embedded in final mirror technical_detail_ref; not a standalone persisted state object", _fields("schema_version", "workflow_run_id", "workflow_tool", "current_state_summary", "completed_step_ids_total", "completed_step_ids_at_run_start", "completed_step_ids_this_run", "already_available", "performed_this_run", "provenance_policy"), _fields("satisfied_precondition_step_ids", "unchanged_artifacts", "changed_artifacts", "evidence_refs"), "closed_deep"),
    _entry("kernel.progress_event.v1", ProgressEvent, "workflow runner and Pipeline adapters", "Frontend progress UI, mirror service, Agent context", "operation log and long-running receipts", _fields("schema_version", "workflow_run_id", "workflow_tool", "step_id", "step_label", "event_type", "status", "sequence_index", "user_visible_summary", "current_state_summary", "timestamp"), _fields("artifact_refs", "receipt_refs"), "closed_deep"),
    _entry("kernel.mirror_event.v1", MirrorEvent, "KernelMirrorEventService", "Agent context, Pipeline Manager Agent, audit/support", "MirrorEventStore or operation log", _fields("schema_version", "mirror_event_id", "mirror_source", "is_kernel_auto_call", "event_type", "severity", "user_visible_summary", "current_state_summary"), _fields("workflow_run_id", "workflow_tool", "user_visible_cause", "kernel_dialog_state", "recovery_options", "allowed_agent_tools", "agent_explanation_guidance", "technical_detail_ref", "support_bundle_ref", "progress_event"), "closed_deep"),
    _entry("kernel.recovery_option.v1", RecoveryOption, "RecoveryOptionService", "dialogs, mirror service, event-scoped tools", "bound to mirror event and receipt", _fields("schema_version", "recovery_id", "recovery_event_id", "label", "description", "owner", "recovery_action_type", "effect", "risk_class", "target_identity", "state_snapshot_identity", "agent_tool", "kernel_dialog_action", "starts_new_workflow", "continuation_workflow_tool", "requires_confirmation", "expires_at"), _fields(), "closed_deep"),
    _entry("kernel.recovery_receipt.v1", RecoveryReceipt, "recovery services/tools", "ReceiptStore, resume, resolver, support", "ReceiptStore", _fields("schema_version", "recovery_receipt_id", "recovery_id", "recovery_event_id", "mirror_event_id", "workflow_run_id", "recovery_state", "selected_recovery_option", "target_identity_before", "target_identity_after", "state_snapshot_identity", "result_status", "written_refs", "mutated_refs", "user_confirmation_refs", "support_bundle_ref", "created_at"), _fields(), "closed_deep"),
    _entry("kernel.sample_analyses.v1", SampleAnalyses, "analyze_samples LLM output after validation", "reports and taxonomy/projection creation", "sa/<analysis_run_id>/sa.json", _fields("schema_version", "analysis_scope", "input_contract", "sample_set", "taxonomy_seed", "projection_seed", "user_report_samples_seed", "quality"), _fields(), "closed_top_level"),
    _entry("kernel.taxonomy_projection_authoring_view.v1", TaxonomyProjectionAuthoringView, "deterministic taxonomy view builder", "create_projections_to_sample_analyses", "proj_sa/<analysis_run_id>/tax_view.json", _fields("schema_version", "taxonomy_ref", "budget_policy", "allowed_codes", "term_summaries", "promotion_slots", "fallback_codes"), _fields(), "closed_top_level"),
    _entry("kernel.create_taxonomy_to_sample_analyses.input.v1", CreateTaxonomyToSampleAnalysesInput, "Kernel request builder", "create_taxonomy_to_sample_analyses LLM call", "tax_sa/<analysis_run_id>/tax_in.json", _fields("schema_version", "sample_analyses"), _fields(), "closed_top_level"),
    _entry("kernel.create_projections_to_sample_analyses.input.v1", CreateProjectionsToSampleAnalysesInput, "Kernel request builder", "create_projections_to_sample_analyses LLM call", "proj_sa/<analysis_run_id>/proj_in.json", _fields("schema_version", "sample_analyses", "taxonomy_authoring_view"), _fields(), "closed_top_level"),
    _entry("kernel.taxonomy_to_sample_analyses.v1", TaxonomyToSampleAnalyses, "create_taxonomy_to_sample_analyses LLM output", "create_taxonomy_update_state", "tax_sa/<analysis_run_id>/tax_sa.json", _fields("schema_version", "source_schema_version", "analysis_scope", "sample_ids", "target", "taxonomy_proposal", "validation", "quality"), _fields(), "closed_top_level"),
    _entry("kernel.projections_to_sample_analyses.v1", ProjectionsToSampleAnalyses, "create_projections_to_sample_analyses LLM output", "create_projections_update_state", "proj_sa/<analysis_run_id>/proj_sa.json", _fields("schema_version", "source_schema_version", "taxonomy_view_schema_version", "analysis_scope", "sample_ids", "taxonomy_ref", "target", "projection_strategy", "projection_proposals", "validation", "quality"), _fields(), "closed_top_level"),
    _entry("kernel.create_taxonomy_update_state.input.v1", CreateTaxonomyUpdateStateInput, "create_taxonomy_update_state", "create_custom_taxonomy", "materialized update-state artifact in taxonomy run folder", _fields("schema_version", "source_schema_version", "analysis_scope", "analysis_run_id", "sample_ids", "source_artifacts", "taxonomy_identity", "taxonomy_core", "taxonomy_text", "semantic_binding", "kernel_policy", "validation_stamp"), _fields(), "closed_top_level"),
    _entry("kernel.create_projections_update_state.input.v1", CreateProjectionsUpdateStateInput, "create_projections_update_state", "create_custom_projection", "materialized update-state artifact in projection run folder", _fields("schema_version", "source_schema_version", "taxonomy_view_schema_version", "analysis_scope", "analysis_run_id", "sample_ids", "source_artifacts", "taxonomy_ref", "projection_precursors", "validation_stamp"), _fields(), "closed_top_level"),
    _entry("kernel.llm_prompt_snapshot.v1", LLMPromptSnapshot, "PromptSnapshotStore", "audit, support, retry validation", "function run folder prompt.json", _fields("schema_version", "analysis_run_id", "llm_function", "created_at", "model_request", "prompt", "bindings"), _fields(), "closed_top_level"),
    _entry("kernel.llm_response_capture.v1", LLMResponseCapture, "LLMFunctionAdapter", "validation, audit, support", "function run folder raw.json", _fields("schema_version", "analysis_run_id", "llm_function", "created_at", "provider", "model", "response_id", "status", "raw_provider_response", "output_text", "parsed_json", "parse_status", "validation_status", "validation_errors"), _fields("attempt_index", "max_attempts"), "closed_top_level"),
)


CONTRACT_REGISTRY: Mapping[str, ContractRegistryEntry] = MappingProxyType(
    {entry.schema_version: entry for entry in _ENTRIES}
)
