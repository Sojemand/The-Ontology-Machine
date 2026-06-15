from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class OntologyWorkflowBlocker:
    blocker_code: str
    step_id: str
    function_or_route: str
    recovery_state_class: str
    user_visible_summary: str
    diagnostics: tuple[Mapping[str, object], ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "blocker_code": self.blocker_code,
            "step_id": self.step_id,
            "function_or_route": self.function_or_route,
            "recovery_state_class": self.recovery_state_class,
            "user_visible_summary": self.user_visible_summary,
            "diagnostics": [dict(item) for item in self.diagnostics],
        }


__all__ = ["OntologyWorkflowBlocker"]
