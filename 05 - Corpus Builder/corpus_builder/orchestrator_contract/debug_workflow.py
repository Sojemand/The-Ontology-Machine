"""Path-stable debug action workflows."""

from __future__ import annotations

from ..context import ModuleContext
from ..services import load_batch
from .debug_run_workflow import run_debug as _run_debug
from .debug_scan_workflow import run_scan


def run_debug(payload: dict, *, context: ModuleContext, parse_debug_run_command_fn) -> dict:
    return _run_debug(
        payload,
        context=context,
        parse_debug_run_command_fn=parse_debug_run_command_fn,
        load_batch_fn=load_batch,
    )


__all__ = ["load_batch", "run_debug", "run_scan"]
