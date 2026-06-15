from __future__ import annotations

from typing import Any, Mapping

from semantic_control_kernel.domain.state_machine.evaluator import StateMachineEvaluator
from semantic_control_kernel.domain.state_machine.models import EligibilityResult, TransitionInputRefs
from semantic_control_kernel.types.state import ActiveDatabaseState


class EligibilityPolicy:
    def __init__(self, evaluator: StateMachineEvaluator | None = None) -> None:
        self.evaluator = evaluator or StateMachineEvaluator()

    def evaluate(
        self,
        function_or_route: str,
        active_state: ActiveDatabaseState | Mapping[str, Any],
        input_refs: TransitionInputRefs | Mapping[str, Any],
        confirmation_ref: str | None = None,
    ) -> EligibilityResult:
        return self.evaluator.evaluate(function_or_route, active_state, input_refs, confirmation_ref)
