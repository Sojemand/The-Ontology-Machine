from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, TypeVar

from semantic_control_kernel.types.enums import RecoveryStateClass
from semantic_control_kernel.types.events import ProgressEvent
from semantic_control_kernel.types.recovery import RecoveryEvent


StepResultT = TypeVar("StepResultT")


@dataclass
class SemanticRecoveryException(Exception):
    cause_code: str
    user_visible_cause: str
    blocked_functions: tuple[str, ...] = ()
    technical_context: Mapping[str, Any] = field(default_factory=dict)
    safe_resume_available: bool = False


class StateBlocker(SemanticRecoveryException):
    recovery_state = RecoveryStateClass.SUPPORT_ONLY_UNRECOVERABLE.value


class TargetIdentityChanged(SemanticRecoveryException):
    recovery_state = RecoveryStateClass.TARGET_IDENTITY_CHANGED.value


class BrokenDatabaseArtifactBinding(SemanticRecoveryException):
    recovery_state = RecoveryStateClass.BROKEN_DATABASE_ARTIFACT_BINDING.value


class SemanticReleaseIncomplete(SemanticRecoveryException):
    recovery_state = RecoveryStateClass.SEMANTIC_RELEASE_INCOMPLETE_STAGED.value


class PartialPipelineRunDetected(SemanticRecoveryException):
    recovery_state = RecoveryStateClass.PARTIAL_PIPELINE_RUN.value


class MergeCollisionUnresolved(SemanticRecoveryException):
    recovery_state = RecoveryStateClass.UNRESOLVED_MERGE_COLLISION.value


class MissingManifestOrOriginals(SemanticRecoveryException):
    recovery_state = RecoveryStateClass.MISSING_MANIFEST_OR_ORIGINALS.value


class LLMFinalValidationFailure(SemanticRecoveryException):
    recovery_state = RecoveryStateClass.FINAL_LLM_VALIDATION_FAILURE.value


class ExpiredPendingInteraction(SemanticRecoveryException):
    recovery_state = RecoveryStateClass.EXPIRED_PENDING_INTERACTION.value


class StaleLockDetected(SemanticRecoveryException):
    recovery_state = RecoveryStateClass.STALE_LOCK.value


class AdapterMissingCapability(SemanticRecoveryException):
    recovery_state = RecoveryStateClass.SUPPORT_ONLY_UNRECOVERABLE.value


class AdapterExecutionFailed(SemanticRecoveryException):
    recovery_state = RecoveryStateClass.SUPPORT_ONLY_UNRECOVERABLE.value


class UnexpectedKernelException(SemanticRecoveryException):
    recovery_state = RecoveryStateClass.SUPPORT_ONLY_UNRECOVERABLE.value


@dataclass(frozen=True)
class SemanticStepRecoveryResult:
    status: str
    recovery_event: RecoveryEvent
    mirror_event: Mapping[str, Any]
    progress_event: ProgressEvent
