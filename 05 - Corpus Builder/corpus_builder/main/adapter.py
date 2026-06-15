"""Adapter stage for logging bootstrap."""
from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler

from ..context import ModuleContext


def setup_logging(context: ModuleContext) -> None:
    """Konfiguriert Logging: Datei (rotierend) + Konsole."""
    context.ensure_runtime_dirs()

    fmt_file = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    fmt_console = logging.Formatter("%(levelname)s: %(message)s")

    file_handler = RotatingFileHandler(
        context.output_dir / "corpus_builder_vision.log",
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setFormatter(fmt_file)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(fmt_console)

    root = logging.getLogger()
    if not root.handlers:
        root.setLevel(logging.INFO)
        root.addHandler(file_handler)
        root.addHandler(console_handler)

__all__ = ["setup_logging"]
