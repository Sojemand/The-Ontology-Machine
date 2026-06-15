"""Path-stable surface for the orchestrator CLI and GUI entrypoint."""

from __future__ import annotations

from ..bootstrap import STATE_ROOT, StartupPrerequisiteError, ensure_startup_prerequisites
from .surface import build_parser, dispatch_command
from .workflow import setup_logging as _setup_logging_impl
from .workflow import start_gui as _start_gui_impl


def _load_app_class():
    from ..ui import OrchestratorApp

    return OrchestratorApp


def _setup_logging() -> None:
    _setup_logging_impl(STATE_ROOT)


def _start_gui() -> None:
    _start_gui_impl(
        ensure_startup_prerequisites=ensure_startup_prerequisites,
        load_app_class=_load_app_class,
    )


def main(argv: list[str] | None = None) -> None:
    _setup_logging()
    args = build_parser().parse_args(argv)
    dispatch_command(args, start_gui=_start_gui)


__all__ = [
    "STATE_ROOT",
    "StartupPrerequisiteError",
    "_load_app_class",
    "_setup_logging",
    "_start_gui",
    "build_parser",
    "dispatch_command",
    "ensure_startup_prerequisites",
    "main",
]
