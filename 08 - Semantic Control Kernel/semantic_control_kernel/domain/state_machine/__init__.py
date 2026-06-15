from __future__ import annotations

from semantic_control_kernel.domain.state_machine.evaluator import StateMachineEvaluator, evaluate_transition
from semantic_control_kernel.domain.state_machine.identity import build_target_identity
from semantic_control_kernel.domain.state_machine.models import (
    ConfirmationGate,
    EligibilityResult,
    EligibilityStatus,
    StateBlocker,
    StateEvidenceBundle,
    StateEvidenceRef,
    StateSpecDisagreement,
    TargetIdentity,
    TargetSelector,
    TransitionInputRefs,
    TransitionRule,
)
from semantic_control_kernel.domain.state_machine.recovery_mapping import BLOCKER_CODES, RECOVERY_BY_BLOCKER
from semantic_control_kernel.domain.state_machine.resolver import KernelStateResolver
from semantic_control_kernel.domain.state_machine.transition_table import (
    TRANSITION_RULES,
    TRANSITION_RULE_BY_FUNCTION,
    get_transition_rule,
    parse_spec_02_transition_rows,
)

__all__ = (
    "BLOCKER_CODES",
    "RECOVERY_BY_BLOCKER",
    "TRANSITION_RULES",
    "TRANSITION_RULE_BY_FUNCTION",
    "ConfirmationGate",
    "EligibilityResult",
    "EligibilityStatus",
    "KernelStateResolver",
    "StateBlocker",
    "StateEvidenceBundle",
    "StateEvidenceRef",
    "StateMachineEvaluator",
    "StateSpecDisagreement",
    "TargetIdentity",
    "TargetSelector",
    "TransitionInputRefs",
    "TransitionRule",
    "build_target_identity",
    "evaluate_transition",
    "get_transition_rule",
    "parse_spec_02_transition_rows",
)
