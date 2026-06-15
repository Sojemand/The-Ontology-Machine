from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from semantic_control_kernel.repository.paths import utc_iso
from semantic_control_kernel.services.client_frontend_event_sink import ClientFrontendEventSink
from semantic_control_kernel.types.batches import PipelineRunTarget
from semantic_control_kernel.types.events import ClientFrontendEvent, ClientFrontendEventAck

RESET_INTERACTION_FUNCTIONS: tuple[str, ...] = (
    "choose_artifact_root_folder",
    "name_database",
    "user_confirmation",
)


class _InlineClientFrontendEventSink(ClientFrontendEventSink):
    def emit(self, event: ClientFrontendEvent) -> ClientFrontendEventAck:
        return ClientFrontendEventAck.from_dict(
            {
                "accepted": True,
                "acknowledged_at": utc_iso(),
                "frontend_event_id": event.payload["frontend_event_id"],
                "host_surface_identity": "semantic_control_kernel.inline_reset_interaction_port",
                "schema_version": ClientFrontendEventAck.SCHEMA_VERSION,
            }
        )


@dataclass(frozen=True)
class ResetInteractionInputs:
    target: PipelineRunTarget
    confirmation_receipt: dict[str, Any]


@dataclass(frozen=True)
class _ResetInteractionProgress:
    artifact_root: str | None = None
    target_database_name: str | None = None
    latest_confirmation_decision: str | None = None

    @property
    def next_interaction_function(self) -> str | None:
        if not self.artifact_root:
            return "choose_artifact_root_folder"
        if not self.target_database_name:
            return "name_database"
        return None
