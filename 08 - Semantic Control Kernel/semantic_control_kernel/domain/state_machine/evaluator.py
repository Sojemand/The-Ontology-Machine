from __future__ import annotations

from typing import Any, Mapping

from semantic_control_kernel.domain.state_machine.blockers import LOCK_BLOCKER_CODES, make_state_blocker
from semantic_control_kernel.domain.state_machine.evaluator_support import (
    actual_state_text,
    confirmation_stale_reason,
    post_state_when_allowed,
    required_state_blocker,
    snapshot_id,
    state_payload,
    target_identity,
)
from semantic_control_kernel.domain.state_machine.models import (
    ConfirmationGate,
    EligibilityResult,
    EligibilityStatus,
    StateBlocker,
    TransitionInputRefs,
    TransitionRule,
)
from semantic_control_kernel.domain.state_machine.transition_table import TRANSITION_RULES
from semantic_control_kernel.types.state import ActiveDatabaseState


class StateMachineEvaluator:
    def __init__(self, transition_rules: tuple[TransitionRule, ...] = TRANSITION_RULES) -> None:
        self._rules = {rule.function_or_route: rule for rule in transition_rules}

    def evaluate(
        self,
        function_or_route: str,
        active_state: ActiveDatabaseState | Mapping[str, Any],
        input_refs: TransitionInputRefs | Mapping[str, Any],
        confirmation_ref: str | None = None,
    ) -> EligibilityResult:
        state = state_payload(active_state)
        refs = input_refs if isinstance(input_refs, TransitionInputRefs) else TransitionInputRefs.from_dict(input_refs)
        rule = self._rules.get(function_or_route)
        if rule is None:
            blocker = self._blocker("unknown_state", function_or_route, "<known transition>", actual_state_text(state), state)
            return self._blocked(function_or_route, state, (blocker,))

        if rule.deprecated:
            blocker = self._blocker(
                "deprecated_function",
                function_or_route,
                rule.required_state_text,
                actual_state_text(state),
                state,
            )
            return EligibilityResult(
                function_or_route=function_or_route,
                status=EligibilityStatus.DEPRECATED_FORBIDDEN.value,
                state_snapshot_id=snapshot_id(state),
                target_identity=target_identity(state),
                post_state_when_allowed=None,
                blockers=(blocker,),
                required_confirmation_gate=None,
            )

        return self._evaluate_rule(rule, state, refs, confirmation_ref)

    def _evaluate_rule(
        self,
        rule: TransitionRule,
        state: Mapping[str, Any],
        refs: TransitionInputRefs,
        confirmation_ref: str | None,
    ) -> EligibilityResult:
        blockers = self._lock_blockers(rule, state) or tuple(
            self._blocker(code, rule.function_or_route, rule.required_state_text, actual_state_text(state), state)
            for code in refs.explicit_blockers
        )
        if blockers:
            return self._blocked(rule.function_or_route, state, blockers)

        state_blocker = required_state_blocker(rule, state, refs, self._blocker)
        if state_blocker is not None:
            return self._blocked(rule.function_or_route, state, (state_blocker,))

        missing_inputs = [input_name for input_name in rule.required_inputs if not refs.has_input(input_name)]
        if missing_inputs:
            blocker = self._blocker(
                "input_missing",
                rule.function_or_route,
                ", ".join(missing_inputs),
                "missing input ref",
                state,
            )
            return self._blocked(rule.function_or_route, state, (blocker,))

        confirmation_result = self._confirmation_result(rule, state, refs, confirmation_ref)
        if confirmation_result is not None:
            return confirmation_result

        return EligibilityResult(
            function_or_route=rule.function_or_route,
            status=EligibilityStatus.ALLOWED.value,
            state_snapshot_id=snapshot_id(state),
            target_identity=target_identity(state),
            post_state_when_allowed=post_state_when_allowed(rule, state),
            blockers=(),
            required_confirmation_gate=None,
        )

    def _lock_blockers(self, rule: TransitionRule, state: Mapping[str, Any]) -> tuple[StateBlocker, ...]:
        if not rule.mutates_state_or_artifacts:
            return ()
        blockers = []
        for blocker_payload in state.get("blocking_reasons", ()):
            if isinstance(blocker_payload, Mapping) and blocker_payload.get("blocker_code") in LOCK_BLOCKER_CODES:
                blockers.append(StateBlocker.from_dict(blocker_payload))
        if blockers:
            return tuple(blockers)
        for lock_ref in state.get("active_lock_refs", ()):
            if not isinstance(lock_ref, Mapping):
                continue
            status = lock_ref.get("status")
            if status == "expired":
                code = "expired_lock_requires_recovery"
            elif status in {"active", "pending_resume"}:
                code = "active_run_lock_conflict"
            else:
                continue
            blockers.append(self._blocker(code, rule.function_or_route, "no blocking lock", status, state))
        return tuple(blockers)

    def _confirmation_result(
        self,
        rule: TransitionRule,
        state: Mapping[str, Any],
        refs: TransitionInputRefs,
        confirmation_ref: str | None,
    ) -> EligibilityResult | None:
        if rule.confirmation_gate == ConfirmationGate.NONE.value:
            return None
        if confirmation_ref is None:
            return EligibilityResult(
                function_or_route=rule.function_or_route,
                status=EligibilityStatus.CONFIRMATION_REQUIRED.value,
                state_snapshot_id=snapshot_id(state),
                target_identity=target_identity(state),
                post_state_when_allowed=None,
                blockers=(),
                required_confirmation_gate=rule.confirmation_gate,
            )
        receipt = refs.confirmation_receipts.get(confirmation_ref)
        if not receipt:
            blocker = self._blocker("confirmation_missing", rule.function_or_route, rule.confirmation_gate, confirmation_ref, state)
            return self._blocked(rule.function_or_route, state, (blocker,))
        stale_reason = confirmation_stale_reason(rule, state, confirmation_ref, receipt)
        if stale_reason:
            blocker = self._blocker("confirmation_stale", rule.function_or_route, rule.confirmation_gate, stale_reason, state)
            return self._blocked(rule.function_or_route, state, (blocker,))
        return None

    def _blocker(
        self,
        code: str,
        function_or_route: str,
        required_state: str,
        actual_state: str,
        state: Mapping[str, Any],
    ) -> StateBlocker:
        return make_state_blocker(
            blocker_code=code,
            function_or_route=function_or_route,
            required_state=required_state,
            actual_state=actual_state,
            target_identity=target_identity(state),
            state_snapshot_id=snapshot_id(state),
            evidence_refs=tuple(str(item) for item in state.get("evidence_refs", ())),
        )

    def _blocked(self, function_or_route: str, state: Mapping[str, Any], blockers: tuple[StateBlocker, ...]) -> EligibilityResult:
        return EligibilityResult(
            function_or_route=function_or_route,
            status=EligibilityStatus.BLOCKED.value,
            state_snapshot_id=snapshot_id(state),
            target_identity=target_identity(state),
            post_state_when_allowed=None,
            blockers=blockers,
            required_confirmation_gate=None,
        )


def evaluate_transition(
    function_or_route: str,
    active_state: ActiveDatabaseState | Mapping[str, Any],
    input_refs: TransitionInputRefs | Mapping[str, Any],
    confirmation_ref: str | None = None,
) -> EligibilityResult:
    return StateMachineEvaluator().evaluate(function_or_route, active_state, input_refs, confirmation_ref)
