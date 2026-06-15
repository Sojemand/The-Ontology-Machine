from __future__ import annotations

from typing import Any, Mapping, Sequence

from semantic_control_kernel.repository.support_bundles import SupportBundleStore
from semantic_control_kernel.types.recovery import SupportBundleRef


class SupportBundleService:
    def __init__(self, store: SupportBundleStore) -> None:
        self.store = store

    def create_support_bundle(
        self,
        *,
        category: str,
        workflow_run_id: str,
        recovery_event_id: str,
        summary: str,
        included_refs: Sequence[Mapping[str, Any]] = (),
        technical_context: Mapping[str, Any] | None = None,
    ) -> SupportBundleRef:
        return self.store.write_support_bundle(
            category=category,
            workflow_run_id=workflow_run_id,
            recovery_event_id=recovery_event_id,
            summary=summary,
            included_refs=included_refs,
            technical_context=technical_context,
        )
