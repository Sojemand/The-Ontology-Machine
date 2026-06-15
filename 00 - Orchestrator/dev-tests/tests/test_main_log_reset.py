from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler

from orchestrator.main.workflow import reset_logging_files


def test_reset_logging_files_recreates_orchestrator_log_handler(tmp_path: Path) -> None:
    logger = logging.getLogger("tests.main_log_reset")
    logger.handlers.clear()
    logger.propagate = False
    logger.setLevel(logging.INFO)
    state_root = tmp_path / "state"
    state_root.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(state_root / "orchestrator.log", maxBytes=1024, backupCount=1, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)
    logger.info("before")
    handler.flush()
    (state_root / "orchestrator.log.1").write_text("backup", encoding="utf-8")
    (state_root / "vision_orchestrator.log").write_text("legacy", encoding="utf-8")

    removed = reset_logging_files(state_root, logger_obj=logger)
    logger.info("after")
    for current in logger.handlers:
        current.flush()

    text = (state_root / "orchestrator.log").read_text(encoding="utf-8")

    assert sorted(path.name for path in removed) == ["orchestrator.log", "orchestrator.log.1", "vision_orchestrator.log"]
    assert "before" not in text
    assert "after" in text

    for current in list(logger.handlers):
        logger.removeHandler(current)
        current.close()
