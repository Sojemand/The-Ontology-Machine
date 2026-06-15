"""Workflow stage for Edit Suite startup."""

from __future__ import annotations

import logging

from .bootstrap import STATE_ROOT, ensure_startup_prerequisites
from .surface import build_parser


def _load_app_class():
    from .ui import EditSuiteApp

    return EditSuiteApp


def setup_logging() -> None:
    ensure_startup_prerequisites()
    logging.basicConfig(
        filename=str(STATE_ROOT / "edit_suite.log"),
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        encoding="utf-8",
    )


def start_gui() -> None:
    app_class = _load_app_class()
    app = app_class()
    app.mainloop()


def main(argv: list[str] | None = None) -> None:
    setup_logging()
    build_parser().parse_args(argv)
    start_gui()


__all__ = ["STATE_ROOT", "build_parser", "ensure_startup_prerequisites", "main", "setup_logging"]
