from __future__ import annotations

from typing import Callable

from semantic_control_kernel.domain.recovery.recovery_context import RecoveryContext
from semantic_control_kernel.domain.recovery.recovery_matrix import RecoveryMatrix
from semantic_control_kernel.domain.recovery.recovery_options import RecoveryOptionService
from semantic_control_kernel.domain.recovery.semantic_exception_payloads import (
    create_mirror_event,
    create_support_ref,
    progress_event,
    recovery_event_payload,
)
from semantic_control_kernel.domain.recovery.semantic_exception_policy import (
    allowed_tools_from_options,
    needs_support_bundle,
    recovery_result_status,
    recovery_status,
)
from semantic_control_kernel.domain.recovery.semantic_exception_types import (
    SemanticRecoveryException,
    SemanticStepRecoveryResult,
    StepResultT,
    UnexpectedKernelException,
)
from semantic_control_kernel.domain.recovery.support_bundle import SupportBundleService
from semantic_control_kernel.policy.recovery_policy import RecoveryPolicy
from semantic_control_kernel.repository.errors import ResumeStateNotFoundError
from semantic_control_kernel.repository.ids import generate_id
from semantic_control_kernel.repository.recovery_events import RecoveryEventStore
from semantic_control_kernel.services.kernel_mirror_event_service import KernelMirrorEventService
from semantic_control_kernel.types.enums import RecoveryStateClass
from semantic_control_kernel.validation.recovery_validation import validate_recovery_event


class SemanticExceptionHandler:
    def __init__(
        self,
        *,
        recovery_event_store: RecoveryEventStore,
        mirror_event_service: KernelMirrorEventService,
        support_bundle_service: SupportBundleService,
        option_service: RecoveryOptionService | None = None,
        policy: RecoveryPolicy | None = None,
        matrix: RecoveryMatrix | None = None,
    ) -> None:
        self.recovery_event_store = recovery_event_store
        self.mirror_event_service = mirror_event_service
        self.support_bundle_service = support_bundle_service
        self.matrix = matrix or RecoveryMatrix()
        self.option_service = option_service or RecoveryOptionService(self.matrix)
        self.policy = policy or RecoveryPolicy()

    def run_step(
        self,
        context: RecoveryContext,
        step: Callable[[], StepResultT],
    ) -> StepResultT | SemanticStepRecoveryResult:
        try:
            return step()
        except SemanticRecoveryException as exc:
            return self.handle_exception(context, exc)
        except Exception as exc:  # pragma: no cover - exercised through tests with a concrete RuntimeError
            wrapped = UnexpectedKernelException(
                cause_code="unexpected_kernel_exception",
                user_visible_cause="The Kernel stopped because an unrecoverable internal error occurred.",
                blocked_functions=context.blocked_functions,
                technical_context={"exception_class": type(exc).__name__, "message": str(exc)},
            )
            return self.handle_exception(context, wrapped)

    def handle_exception(
        self,
        context: RecoveryContext,
        exc: SemanticRecoveryException,
    ) -> SemanticStepRecoveryResult:
        recovery_state = self._classify(exc)
        recovery_event_id = generate_id("recovery_event_id")
        expires_at = self.policy.expires_at(recovery_state)
        support_ref = self._support_ref(context, exc, recovery_state, recovery_event_id)
        safe_tools = self._safe_tools(recovery_state, exc, support_ref is not None)
        options = self.option_service.create_options(
            recovery_event_id=recovery_event_id,
            recovery_state=recovery_state,
            target_identity=context.target_payload(),
            state_snapshot_identity=context.snapshot_payload(),
            expires_at=expires_at,
            support_bundle_ref=support_ref,
            safe_tools=safe_tools,
            evidence=exc.technical_context,
        )
        allowed_tools = allowed_tools_from_options(options)
        mirror = create_mirror_event(
            self.mirror_event_service,
            context=context,
            exc=exc,
            recovery_state=recovery_state,
            options=options,
            allowed_tools=allowed_tools,
            support_ref=support_ref,
            expires_at=expires_at,
        )
        payload = recovery_event_payload(
            context=context,
            exc=exc,
            recovery_state=recovery_state,
            recovery_event_id=recovery_event_id,
            mirror_event_id=mirror.payload["mirror_event_id"],
            options=options,
            allowed_tools=allowed_tools,
            support_ref=support_ref,
            expires_at=expires_at,
        )
        validate_recovery_event(payload)
        recovery_event = self.recovery_event_store.put_recovery_event(payload)
        self._supersede_older_events(context.workflow_run_id, recovery_event_id)
        receipt = self.recovery_event_store.append_recovery_receipt(
            recovery_event=recovery_event,
            recovery_id=options[0].payload["recovery_id"],
            result_status=recovery_result_status(recovery_state),
            selected_recovery_option=options[0].to_dict(),
            support_bundle_ref=support_ref,
        )
        progress = progress_event(
            context=context,
            exc=exc,
            recovery_state=recovery_state,
            recovery_event_id=recovery_event_id,
            recovery_receipt_id=receipt.payload["recovery_receipt_id"],
        )
        return SemanticStepRecoveryResult(
            status=recovery_status(recovery_state),
            recovery_event=recovery_event,
            mirror_event=mirror.to_dict(),
            progress_event=progress,
        )

    def _support_ref(self, context: RecoveryContext, exc: SemanticRecoveryException, recovery_state: str, recovery_event_id: str):
        if recovery_state != RecoveryStateClass.SUPPORT_ONLY_UNRECOVERABLE.value and not needs_support_bundle(recovery_state, exc):
            return None
        return create_support_ref(
            self.support_bundle_service,
            context=context,
            exc=exc,
            recovery_state=recovery_state,
            recovery_event_id=recovery_event_id,
        )

    def _classify(self, exc: SemanticRecoveryException) -> str:
        recovery_state = getattr(exc, "recovery_state", RecoveryStateClass.SUPPORT_ONLY_UNRECOVERABLE.value)
        if recovery_state not in self.matrix.entries:
            return RecoveryStateClass.SUPPORT_ONLY_UNRECOVERABLE.value
        return recovery_state

    def _safe_tools(self, recovery_state: str, exc: SemanticRecoveryException, has_support: bool) -> tuple[str, ...]:
        tools = list(self.matrix.allowed_tools_for_state(recovery_state))
        if recovery_state == RecoveryStateClass.FINAL_LLM_VALIDATION_FAILURE.value and not exc.safe_resume_available:
            tools = [tool for tool in tools if tool != "kernel_retry_recoverable_workflow"]
        if not has_support:
            tools = [tool for tool in tools if tool != "kernel_open_support_bundle"]
        return tuple(tools)

    def _supersede_older_events(self, workflow_run_id: str, recovery_event_id: str) -> None:
        superseded_events = self.recovery_event_store.supersede_active_for_workflow(workflow_run_id, recovery_event_id)
        for event in superseded_events:
            mirror_event_id = event.payload.get("mirror_event_id")
            if not isinstance(mirror_event_id, str) or not mirror_event_id:
                continue
            try:
                self.mirror_event_service.expire_event_scoped_tools(mirror_event_id, "event_superseded")
            except ResumeStateNotFoundError:
                continue
