from __future__ import annotations

from semantic_control_kernel.types.base import make_contract_types


_CONTRACT_TYPES = (
    ("ActiveDatabaseState", "kernel.active_database_state.v1"),
    ("DatabaseArtifactBinding", "kernel.database_artifact_binding.v1"),
    ("SemanticReleaseAttachState", "kernel.semantic_release_attach_state.v1"),
    ("PipelineBatchManifest", "kernel.pipeline_batch_manifest.v1"),
    ("RecordSemanticMaterializationRef", "kernel.record_semantic_materialization_ref.v1"),
    ("LockState", "kernel.lock_state.v1"),
    ("WorkflowResumeState", "kernel.workflow_resume_state.v1"),
)

globals().update(make_contract_types(_CONTRACT_TYPES, __name__))
