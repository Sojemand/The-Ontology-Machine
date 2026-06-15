from __future__ import annotations

from collections.abc import Iterable
from enum import Enum

from semantic_control_kernel.types.enums import (
    AnalysisScope,
    AttachPointerOwner,
    ClientFrontendEventKind,
    DatabaseEmptiness,
    DialogType,
    InteractionKind,
    InteractionResponseStatus,
    LLMParseStatus,
    LLMResponseStatus,
    LLMValidationFailureCode,
    LLMValidationStatus,
    LockStatus,
    LockType,
    MergeCollisionResolutionStatus,
    MergeRoute,
    MirrorEventType,
    MirrorSeverity,
    MirrorSource,
    PipelineBatchKind,
    PipelineBatchStatus,
    ProjectionMergeMode,
    ProgressEventType,
    ProgressStatus,
    RecoveryActionType,
    RecoveryDialogType,
    RecoveryOwner,
    RecoveryResultStatus,
    RecoveryStateClass,
    RiskClass,
    SemanticReleaseState,
    UserDecision,
)

EnumRuleMap = dict[str, dict[str, Iterable[str] | type[Enum]]]

ENUM_FIELD_RULES: EnumRuleMap = {
    "kernel.analyze_sample.input.v1": {
        "source_ref.kind": ("interpreter_request_view_vision.v1", "interpreter_request_view_file.v1"),
    },
    "kernel.active_database_state.v1": {
        "database_emptiness": DatabaseEmptiness,
        "semantic_release_state": SemanticReleaseState,
    },
    "kernel.semantic_release_attach_state.v1": {"pointer_owner": AttachPointerOwner},
    "kernel.pipeline_batch_manifest.v1": {
        "batch_kind": PipelineBatchKind,
        "batch_status": PipelineBatchStatus,
    },
    "kernel.database_merge_selection.v1": {"merge_route": MergeRoute, "projection_merge_mode": ProjectionMergeMode},
    "kernel.database_merge_collision_manifest.v1": {"merge_route": MergeRoute},
    "kernel.database_merge_reconciliation_receipt.v1": {
        "result_status": MergeCollisionResolutionStatus,
    },
    "kernel.confirmation_request.v1": {"risk_class": RiskClass},
    "kernel.confirmation_receipt.v1": {"user_decision": UserDecision},
    "kernel.user_interaction_request.v1": {
        "interaction_kind": InteractionKind,
        "dialog_type": DialogType,
        "recovery_dialog_type": RecoveryDialogType,
        "risk_class": RiskClass,
    },
    "kernel.user_interaction_response.v1": {
        "response_status": InteractionResponseStatus,
        "confirmation_decision": UserDecision,
    },
    "kernel.client_frontend_event.v1": {"frontend_event_kind": ClientFrontendEventKind},
    "kernel.lock_state.v1": {"lock_type": LockType, "status": LockStatus},
    "kernel.progress_event.v1": {
        "event_type": ProgressEventType,
        "status": ProgressStatus,
    },
    "kernel.mirror_event.v1": {
        "mirror_source": MirrorSource,
        "event_type": MirrorEventType,
        "severity": MirrorSeverity,
    },
    "kernel.recovery_option.v1": {
        "owner": RecoveryOwner,
        "recovery_action_type": RecoveryActionType,
        "risk_class": RiskClass,
    },
    "kernel.recovery_receipt.v1": {
        "recovery_state": RecoveryStateClass,
        "result_status": RecoveryResultStatus,
    },
    "kernel.sample_analyses.v1": {"analysis_scope": AnalysisScope},
    "kernel.taxonomy_to_sample_analyses.v1": {"analysis_scope": AnalysisScope},
    "kernel.projections_to_sample_analyses.v1": {"analysis_scope": AnalysisScope},
    "kernel.create_taxonomy_update_state.input.v1": {"analysis_scope": AnalysisScope},
    "kernel.create_projections_update_state.input.v1": {"analysis_scope": AnalysisScope},
    "kernel.llm_response_capture.v1": {
        "status": LLMResponseStatus,
        "parse_status": LLMParseStatus,
        "validation_status": LLMValidationStatus,
        "validation_errors[]": LLMValidationFailureCode,
    },
}
