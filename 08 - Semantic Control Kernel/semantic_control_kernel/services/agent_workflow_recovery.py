from __future__ import annotations

from typing import Any, Mapping

from semantic_control_kernel.domain.recovery.recovery_context import RecoveryContext
from semantic_control_kernel.domain.recovery.semantic_exception_handler import (
    SemanticExceptionHandler,
    SemanticRecoveryException,
)
from semantic_control_kernel.domain.recovery.support_bundle import SupportBundleService
from semantic_control_kernel.repository.event_store import MirrorEventStore
from semantic_control_kernel.repository.paths import StatePaths
from semantic_control_kernel.repository.recovery_events import RecoveryEventStore
from semantic_control_kernel.repository.support_bundles import SupportBundleStore
from semantic_control_kernel.services.kernel_mirror_event_service import KernelMirrorEventService
from semantic_control_kernel.types.enums import RecoveryStateClass


def semantic_recovery_for_blocked_execution(
    tool_name: str,
    execution: Mapping[str, Any],
    blocker: Mapping[str, Any] | None,
    state_paths: StatePaths,
):
    if blocker is None:
        return None
    recovery_state = recovery_state_from_blocker(blocker)
    context = RecoveryContext(
        workflow_run_id=str(execution.get("workflow_run_id") or f"wr_blocked_{tool_name}"),
        workflow_tool=str(execution.get("workflow_tool") or tool_name),
        failed_kernel_step=str(execution.get("blocked_step_id") or blocker.get("step_id") or tool_name),
        target_identity=target_identity_from_execution(execution),
        state_snapshot_identity=state_snapshot_identity_from_execution(execution),
        blocked_functions=(str(blocker.get("function_or_route") or tool_name),),
        support_refs=tuple(support_refs_from_blocker(blocker)),
        detected_by="AgentToolWorkflowDispatch",
    )
    exc = SemanticRecoveryException(
        cause_code=str(blocker.get("blocker_code") or "workflow_blocked"),
        user_visible_cause=str(blocker.get("user_visible_summary") or f"{tool_name} is blocked."),
        blocked_functions=context.blocked_functions,
        technical_context={
            "blocker": dict(blocker),
            "workflow_status": str(execution.get("status") or "blocked"),
        },
    )
    setattr(exc, "recovery_state", recovery_state)
    return SemanticExceptionHandler(
        recovery_event_store=RecoveryEventStore(state_paths),
        mirror_event_service=KernelMirrorEventService(MirrorEventStore(state_paths)),
        support_bundle_service=SupportBundleService(SupportBundleStore(state_paths)),
    ).handle_exception(context, exc)


def recovery_state_from_blocker(blocker: Mapping[str, Any]) -> str:
    candidate = str(blocker.get("recovery_state_class") or RecoveryStateClass.SUPPORT_ONLY_UNRECOVERABLE.value)
    if candidate in RecoveryStateClass.values():
        return candidate
    return RecoveryStateClass.SUPPORT_ONLY_UNRECOVERABLE.value


def target_identity_from_execution(execution: Mapping[str, Any]) -> Mapping[str, Any]:
    target_identity = execution.get("target_identity")
    if isinstance(target_identity, Mapping):
        return dict(target_identity)
    target = execution.get("target")
    if isinstance(target, Mapping) and isinstance(target.get("target_identity"), Mapping):
        return dict(target["target_identity"])
    return {}


def state_snapshot_identity_from_execution(execution: Mapping[str, Any]) -> Mapping[str, Any]:
    state_snapshot_id = (
        execution.get("state_snapshot_id")
        or execution.get("initial_state_snapshot_id")
        or f"{execution.get('workflow_run_id', 'workflow')}:{execution.get('blocked_step_id', 'blocked')}"
    )
    return {"state_snapshot_id": str(state_snapshot_id)}


def support_refs_from_blocker(blocker: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    refs: list[Mapping[str, Any]] = []
    diagnostics = blocker.get("diagnostics")
    if isinstance(diagnostics, list):
        for index, item in enumerate(diagnostics):
            if isinstance(item, Mapping):
                ref_payload = extract_included_refs(item)
                if ref_payload:
                    refs.append({"diagnostic_index": index, "refs": ref_payload})
    return refs


def extract_included_refs(value: Any) -> Any:
    if isinstance(value, Mapping):
        payload: dict[str, Any] = {}
        for key, child in value.items():
            key_text = str(key)
            cleaned = clean_included_ref_value(child) if is_reference_field(key_text) else extract_included_refs(child)
            if has_included_ref_content(cleaned):
                payload[key_text] = cleaned
        return payload
    if isinstance(value, list):
        items = [extract_included_refs(item) for item in value]
        return [item for item in items if has_included_ref_content(item)]
    return None


def clean_included_ref_value(value: Any) -> Any:
    if isinstance(value, str):
        text = value.strip()
        return text or None
    if isinstance(value, Mapping):
        payload: dict[str, Any] = {}
        for key, child in value.items():
            cleaned = clean_included_ref_value(child)
            if has_included_ref_content(cleaned):
                payload[str(key)] = cleaned
        return payload
    if isinstance(value, list):
        items = [clean_included_ref_value(item) for item in value]
        return [item for item in items if has_included_ref_content(item)]
    if value is None:
        return None
    return value


def is_reference_field(key: str) -> bool:
    return key.endswith("_ref") or key.endswith("_refs") or key in {"artifact_path", "artifact_paths", "object_ref", "support_bundle_path"}


def has_included_ref_content(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, Mapping):
        return bool(value)
    if isinstance(value, list):
        return bool(value)
    return True


def blocked_extra(blocker: Mapping[str, Any] | None, recovery) -> Mapping[str, Any]:
    extra: dict[str, Any] = {}
    if blocker is not None:
        extra["blocker"] = dict(blocker)
    if recovery is not None:
        extra["recovery_event"] = {
            "recovery_event_id": recovery.recovery_event.payload["recovery_event_id"],
            "recovery_state": recovery.recovery_event.payload["recovery_state"],
            "mirror_event_id": recovery.recovery_event.payload["mirror_event_id"],
        }
    return extra
