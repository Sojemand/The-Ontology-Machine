from __future__ import annotations

from semantic_control_kernel.domain.recovery.recovery_context import RecoveryContext
from semantic_control_kernel.domain.recovery.recovery_matrix import RecoveryMatrix, RecoveryMatrixEntry
from semantic_control_kernel.domain.recovery.semantic_exception_handler import (
    AdapterExecutionFailed,
    AdapterMissingCapability,
    BrokenDatabaseArtifactBinding,
    ExpiredPendingInteraction,
    LLMFinalValidationFailure,
    MergeCollisionUnresolved,
    MissingManifestOrOriginals,
    PartialPipelineRunDetected,
    SemanticExceptionHandler,
    SemanticReleaseIncomplete,
    StaleLockDetected,
    StateBlocker,
    TargetIdentityChanged,
    UnexpectedKernelException,
)

__all__ = [
    "AdapterExecutionFailed",
    "AdapterMissingCapability",
    "BrokenDatabaseArtifactBinding",
    "ExpiredPendingInteraction",
    "LLMFinalValidationFailure",
    "MergeCollisionUnresolved",
    "MissingManifestOrOriginals",
    "PartialPipelineRunDetected",
    "RecoveryContext",
    "RecoveryMatrix",
    "RecoveryMatrixEntry",
    "SemanticExceptionHandler",
    "SemanticReleaseIncomplete",
    "StaleLockDetected",
    "StateBlocker",
    "TargetIdentityChanged",
    "UnexpectedKernelException",
]
