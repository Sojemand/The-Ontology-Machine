from __future__ import annotations

from enum import Enum


class StateMachineStrEnum(str, Enum):
    @classmethod
    def values(cls) -> tuple[str, ...]:
        return tuple(member.value for member in cls)


class EligibilityStatus(StateMachineStrEnum):
    ALLOWED = "allowed"
    BLOCKED = "blocked"
    CONFIRMATION_REQUIRED = "confirmation_required"
    DEPRECATED_FORBIDDEN = "deprecated_forbidden"


class ConfirmationGate(StateMachineStrEnum):
    NONE = "none"
    DESTRUCTIVE = "destructive"
    DESTRUCTIVE_WHEN_PROJECTION_REMOVAL = "destructive_when_projection_removal"
    REQUIRED_BY_WORKFLOW_WHEN_FILLED_DATABASE_PATH = "required_by_workflow_when_filled_database_path"
    USER_TYPE_DECISION_TAXONOMY = "user_type_decision_taxonomy"
    USER_TYPE_DECISION_PROJECTIONS = "user_type_decision_projections"
    USER_CHOICE = "user_choice"
    INPUT_PRESENCE_CONFIRMATION = "input_presence_confirmation"
    OVERWRITE_ONLY = "overwrite_only"


class BlockerSeverity(StateMachineStrEnum):
    RECOVERABLE_ERROR = "recoverable_error"
    FINAL_ERROR = "final_error"
    WARNING = "warning"
