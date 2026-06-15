"""Workflow stage for orchestrator startup, logging and GUI launch."""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

_LOG_FILE_NAME = "orchestrator.log"
_LEGACY_LOG_FILE_NAME = "vision_orchestrator.log"


def setup_logging(state_root: Path) -> None:
    state_root.mkdir(parents=True, exist_ok=True)
    root = logging.getLogger()
    if root.handlers:
        return
    root.setLevel(logging.INFO)
    fmt_console = logging.Formatter("%(levelname)s: %(message)s")
    file_handler = _build_file_handler(state_root)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(fmt_console)
    root.addHandler(file_handler)
    root.addHandler(console_handler)


def start_gui(*, ensure_startup_prerequisites, load_app_class) -> None:
    try:
        ensure_startup_prerequisites()
        app_cls = load_app_class()
    except Exception as exc:
        logging.getLogger(__name__).error(str(exc))
        raise SystemExit(str(exc)) from exc

    app = app_cls()
    app.mainloop()


def reset_logging_files(state_root: Path, *, logger_obj: logging.Logger | None = None) -> tuple[Path, ...]:
    state_root.mkdir(parents=True, exist_ok=True)
    logger_obj = logger_obj or logging.getLogger()
    target = (state_root / _LOG_FILE_NAME).resolve()
    for handler in list(logger_obj.handlers):
        if Path(getattr(handler, "baseFilename", "")).resolve() != target:
            continue
        logger_obj.removeHandler(handler)
        handler.close()
    removed: list[Path] = []
    for path in _collect_log_targets(state_root):
        try:
            path.unlink(missing_ok=True)
        except Exception:
            continue
        removed.append(path)
    if not any(Path(getattr(handler, "baseFilename", "")).resolve() == target for handler in logger_obj.handlers):
        logger_obj.addHandler(_build_file_handler(state_root))
    return tuple(removed)


def _build_file_handler(state_root: Path) -> RotatingFileHandler:
    handler = RotatingFileHandler(state_root / _LOG_FILE_NAME, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    return handler


def _collect_log_targets(state_root: Path) -> tuple[Path, ...]:
    targets: list[Path] = []
    for pattern in (f"{_LOG_FILE_NAME}*", f"{_LEGACY_LOG_FILE_NAME}*"):
        for path in sorted(state_root.glob(pattern)):
            if path.is_file() and path not in targets:
                targets.append(path)
    return tuple(targets)
