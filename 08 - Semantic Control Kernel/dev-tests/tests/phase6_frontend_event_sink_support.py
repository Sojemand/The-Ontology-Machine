from __future__ import annotations

import ast
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from semantic_control_kernel.repository.event_store import MirrorEventStore, ProgressEventStore
from semantic_control_kernel.repository.interaction_store import InteractionRequestStore
from semantic_control_kernel.repository.paths import StatePaths
from semantic_control_kernel.repository.receipt_store import ReceiptStore
from semantic_control_kernel.repository.reset import KernelStateResetService
from semantic_control_kernel.repository.run_store import WorkflowRunStore
from semantic_control_kernel.services.kernel_mirror_event_service import KernelMirrorEventService
from semantic_control_kernel.services.user_interaction_service import KernelUserInteractionService
import semantic_control_kernel.surface.client_frontend_bridge as bridge_module
from semantic_control_kernel.surface.background_continuation import launch_interaction_continuation, terminate_background_continuations
from semantic_control_kernel.surface.client_frontend_bridge import cancel_user_interaction, list_client_frontend_events, submit_user_interaction_response
from semantic_control_kernel.surface.client_frontend_event_scope import recent_terminal_workflow_run_ids
from semantic_control_kernel.surface.client_frontend_continuation import (
    append_background_continuation_progress,
    append_background_continuation_terminal_progress,
)
from semantic_control_kernel.testing.fakes.fake_client_frontend_sink import FakeClientFrontendSink
from semantic_control_kernel.types.enums import ClientFrontendEventKind
from semantic_control_kernel.types.events import ProgressEvent, UserInteractionResponse


MODULE_ROOT = Path(__file__).resolve().parents[2]
TARGET = {"target_hash": "tgt_phase6", "artifact_root_path_hash": "art_phase6"}
SNAPSHOT = {"state_snapshot_id": "ss_phase6"}


def _service(tmp_path: Path, *, accepted: bool = True):
    paths = StatePaths.from_state_root(tmp_path / "state")
    sink = FakeClientFrontendSink(accepted=accepted)
    return (
        KernelUserInteractionService(
            interaction_store=InteractionRequestStore(paths),
            mirror_event_service=KernelMirrorEventService(MirrorEventStore(paths)),
            event_sink=sink,
            workflow_run_store=WorkflowRunStore(paths),
        ),
        sink,
        paths,
    )

__all__ = [
    "ast",
    "json",
    "datetime",
    "timedelta",
    "timezone",
    "Path",
    "MirrorEventStore",
    "ProgressEventStore",
    "InteractionRequestStore",
    "StatePaths",
    "ReceiptStore",
    "KernelStateResetService",
    "WorkflowRunStore",
    "KernelMirrorEventService",
    "KernelUserInteractionService",
    "bridge_module",
    "launch_interaction_continuation",
    "terminate_background_continuations",
    "cancel_user_interaction",
    "list_client_frontend_events",
    "submit_user_interaction_response",
    "recent_terminal_workflow_run_ids",
    "append_background_continuation_progress",
    "append_background_continuation_terminal_progress",
    "FakeClientFrontendSink",
    "ClientFrontendEventKind",
    "ProgressEvent",
    "UserInteractionResponse",
    "MODULE_ROOT",
    "TARGET",
    "SNAPSHOT",
    "_service",
]
