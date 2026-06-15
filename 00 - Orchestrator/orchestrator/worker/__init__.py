"""Path-stable surface for orchestrator worker execution."""

from __future__ import annotations

import os
import signal
import sys

from ..pipeline import OrchestratorBusyError, OrchestratorCancelled, OrchestratorEngine
from ..orchestrator_contract.types import EMBEDDINGS_ACTION, RESET_ACTION, RESET_PIPELINE_LOGS_ACTION, RUN_ACTION
from .adapter import (
    terminate_windows_process as _terminate_windows_process,
    windows_collect_process_tree as _windows_collect_process_tree,
)
from .runtime import terminate_process_tree as _terminate_process_tree
from .workflow import run_worker_process as _run_worker_process

__all__ = [
    "OrchestratorBusyError",
    "OrchestratorCancelled",
    "EMBEDDINGS_ACTION",
    "OrchestratorEngine",
    "RESET_ACTION",
    "RESET_PIPELINE_LOGS_ACTION",
    "RUN_ACTION",
    "run_worker_process",
    "terminate_process_tree",
]


def run_worker_process(
    project_root: str,
    action: str,
    ui_state_data: dict,
    event_queue,
    cancel_event,
) -> None:
    _run_worker_process(
        project_root,
        action,
        ui_state_data,
        event_queue,
        cancel_event,
        engine_cls=OrchestratorEngine,
        cancelled_error=OrchestratorCancelled,
        busy_error=OrchestratorBusyError,
    )


def terminate_process_tree(pid: int) -> None:
    _terminate_process_tree(
        pid,
        platform=sys.platform,
        windows_collect_process_tree=_windows_collect_process_tree,
        terminate_windows_process=_terminate_windows_process,
        os_module=os,
        signal_module=signal,
    )
