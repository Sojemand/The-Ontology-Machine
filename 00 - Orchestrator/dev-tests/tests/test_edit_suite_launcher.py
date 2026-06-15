from __future__ import annotations

import pytest

from orchestrator.ui import edit_suite_launcher


def test_launch_uses_sibling_edit_suite_run_bat(monkeypatch, tmp_path) -> None:
    project_root = tmp_path / "00 - Orchestrator"
    project_root.mkdir(parents=True, exist_ok=True)
    run_script = tmp_path / "06 - Edit Suite" / "run.bat"
    run_script.parent.mkdir(parents=True, exist_ok=True)
    run_script.write_text("@echo off\r\n", encoding="utf-8")
    captured: dict[str, str] = {}

    monkeypatch.setattr(edit_suite_launcher.os, "startfile", lambda target: captured.setdefault("target", target))

    launched = edit_suite_launcher.launch(project_root)

    assert launched == run_script
    assert captured["target"] == str(run_script)


def test_launch_rejects_missing_edit_suite_run_bat(tmp_path) -> None:
    project_root = tmp_path / "00 - Orchestrator"
    project_root.mkdir(parents=True, exist_ok=True)

    with pytest.raises(FileNotFoundError, match="Edit Suite launcher is missing"):
        edit_suite_launcher.launch(project_root)
