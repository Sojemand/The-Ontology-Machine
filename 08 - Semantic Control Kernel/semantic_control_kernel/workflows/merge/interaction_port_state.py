from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from semantic_control_kernel.repository.paths import utc_iso
from semantic_control_kernel.services.client_frontend_event_sink import ClientFrontendEventSink
from semantic_control_kernel.types.events import ClientFrontendEvent, ClientFrontendEventAck
from semantic_control_kernel.types.merge import PROJECTION_MERGE_MODE_DEFAULT, PROJECTION_MERGE_MODE_VALUES

MERGE_INTERACTION_FUNCTIONS: tuple[str, ...] = (
    "choose_merge_database_count",
    "choose_databases_to_merge",
    "choose_new_artifact_root_folder",
    "choose_merge_projection_mode",
)


class InlineMergeClientFrontendEventSink(ClientFrontendEventSink):
    def emit(self, event: ClientFrontendEvent) -> ClientFrontendEventAck:
        return ClientFrontendEventAck.from_dict(
            {
                "schema_version": ClientFrontendEventAck.SCHEMA_VERSION,
                "frontend_event_id": event.payload["frontend_event_id"],
                "accepted": True,
                "host_surface_identity": "semantic_control_kernel.inline_merge_interaction_port",
                "acknowledged_at": utc_iso(),
            }
        )


@dataclass(frozen=True)
class MergeInteractionInputs:
    selected_sources: tuple[dict[str, Any], ...]
    target_artifact_root: str
    projection_merge_mode: str
    selected_by_interaction_id: str


@dataclass(frozen=True)
class MergeInteractionProgress:
    source_count: int | None = None
    selected_database_paths: tuple[str, ...] = ()
    source_interaction_request_id: str | None = None
    target_artifact_root: str | None = None
    projection_merge_mode: str | None = None

    @property
    def next_interaction_function(self) -> str | None:
        if self.source_count is None:
            return "choose_merge_database_count"
        if len(self.selected_database_paths) < self.source_count:
            return "choose_databases_to_merge"
        if not self.target_artifact_root:
            return "choose_new_artifact_root_folder"
        if not self.projection_merge_mode:
            return "choose_merge_projection_mode"
        return None


def clean_source_count(value: object) -> int | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    try:
        count = int(text)
    except ValueError:
        return None
    return count if count >= 2 else None


def clean_projection_merge_mode(value: object) -> str:
    text = str(value or "").strip()
    if text in PROJECTION_MERGE_MODE_VALUES:
        return text
    return PROJECTION_MERGE_MODE_DEFAULT
