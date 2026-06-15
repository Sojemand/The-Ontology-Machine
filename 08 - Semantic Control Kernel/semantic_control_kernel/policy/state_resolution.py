from __future__ import annotations

from datetime import datetime
from typing import Any, Mapping

from semantic_control_kernel.domain.state_machine.models import StateEvidenceBundle, TargetSelector
from semantic_control_kernel.domain.state_machine.resolver import KernelStateResolver
from semantic_control_kernel.types.state import ActiveDatabaseState


class StateResolutionPolicy:
    def __init__(self, resolver: KernelStateResolver | None = None) -> None:
        self.resolver = resolver or KernelStateResolver()

    def resolve_active_database_state(
        self,
        target_selector: TargetSelector | Mapping[str, Any],
        evidence_bundle: StateEvidenceBundle | Mapping[str, Any] | None,
        now_utc: datetime,
    ) -> ActiveDatabaseState:
        return self.resolver.resolve(target_selector, evidence_bundle, now_utc)
