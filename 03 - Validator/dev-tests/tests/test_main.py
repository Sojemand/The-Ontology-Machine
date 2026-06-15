from __future__ import annotations

import json
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

import pytest

from validator_vision.main import adapter as main_adapter
from validator_vision.main import surface as main_surface
from validator_vision.main import workflow as main_workflow
from validator_vision.main.types import ValidateBatchCommand, ValidateCommand


def _set_validator_home(monkeypatch, scratch_dir: Path) -> Path:
    home = scratch_dir / "validator-home"
    monkeypatch.setenv("VALIDATOR_VISION_HOME", str(home))
    return home


def test_setup_logging_falls_back_to_console_when_file_logging_fails(monkeypatch, scratch_dir: Path):
    root_logger = logging.getLogger()
    original_handlers = list(root_logger.handlers)
    original_level = root_logger.level
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)

    try:
        _set_validator_home(monkeypatch, scratch_dir)
        main_adapter.setup_logging(
            ensure_layout=lambda: (_ for _ in ()).throw(PermissionError("denied")),
            resolve_log_dir=lambda home: home / "logs",
        )

        assert any(isinstance(handler, logging.StreamHandler) for handler in root_logger.handlers)
        assert not any(isinstance(handler, RotatingFileHandler) for handler in root_logger.handlers)
    finally:
        for handler in list(root_logger.handlers):
            root_logger.removeHandler(handler)
            handler.close()
        for handler in original_handlers:
            root_logger.addHandler(handler)
        root_logger.setLevel(original_level)


def test_run_validate_rejects_directory_input(scratch_dir: Path, tmp_report_root: Path, capsys):
    structured_dir = scratch_dir / "structured-dir"
    structured_dir.mkdir()
    report_path = tmp_report_root / "doc.vision_validation_report.json"

    exit_code = main_workflow.run_validate(
        ValidateCommand(structured_path=structured_dir, report_path=report_path)
    )
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "muss eine Datei sein" in captured.out


def test_run_validate_rejects_report_directory(scratch_dir: Path, capsys):
    structured_path = scratch_dir / "doc.structured.json"
    structured_path.write_text(json.dumps({"content": {"free_text": "hello"}}), encoding="utf-8")
    report_dir = scratch_dir / "reports"
    report_dir.mkdir()

    exit_code = main_workflow.run_validate(
        ValidateCommand(structured_path=structured_path, report_path=report_dir)
    )
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "Report-Ziel muss eine Datei sein" in captured.out


def test_run_batch_returns_success_for_empty_directory(monkeypatch, scratch_dir: Path, tmp_report_root: Path, capsys):
    _set_validator_home(monkeypatch, scratch_dir)
    empty_dir = scratch_dir / "structured"
    empty_dir.mkdir()

    exit_code = main_workflow.run_batch(
        ValidateBatchCommand(structured_dir=empty_dir, report_root=tmp_report_root)
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "0 Dokumente validiert" in captured.out


def test_run_batch_rejects_report_root_file(scratch_dir: Path, capsys):
    structured_dir = scratch_dir / "structured"
    structured_dir.mkdir()
    report_file = scratch_dir / "report.json"
    report_file.write_text("{}", encoding="utf-8")

    exit_code = main_workflow.run_batch(
        ValidateBatchCommand(structured_dir=structured_dir, report_root=report_file)
    )
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "Report-Root muss ein Verzeichnis sein" in captured.out


def test_parser_exposes_only_headless_validation_commands() -> None:
    parser = main_surface.build_parser()
    commands = parser._subparsers._group_actions[0].choices
    assert sorted(commands) == ["validate", "validate-batch"]


@pytest.mark.parametrize("command", ["show-report", "check-config"])
def test_parser_rejects_removed_commands(command: str) -> None:
    parser = main_surface.build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args([command])
