from __future__ import annotations

from pathlib import Path

import pytest

from semantic_control_kernel import __main__ as launcher


MODULE_ROOT = Path(__file__).resolve().parents[2]


def test_help_exits_zero_and_mentions_runtime_report(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as excinfo:
        launcher.main(["--help"])

    assert excinfo.value.code == 0
    captured = capsys.readouterr()
    assert "--runtime-report" in captured.out


def test_runtime_report_delegates_to_bootstrap_runtime_report(monkeypatch: pytest.MonkeyPatch) -> None:
    observed: dict[str, list[str]] = {}

    def fake_main(argv: list[str]) -> int:
        observed["argv"] = argv
        return 17

    monkeypatch.setattr(launcher.runtime_report, "main", fake_main)

    exit_code = launcher.main(["--runtime-report", "--root", str(MODULE_ROOT), "--strict"])

    assert exit_code == 17
    assert observed["argv"] == ["--root", str(MODULE_ROOT), "--strict"]


def test_runtime_report_requires_root(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = launcher.main(["--runtime-report"])

    assert exit_code == 2
    assert "--runtime-report requires --root <module_root>" in capsys.readouterr().err


def test_rejects_unsupported_commands(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = launcher.main(["workflow"])

    assert exit_code == 2
    assert "Unsupported Semantic Control Kernel command: workflow" in capsys.readouterr().err


def test_root_and_strict_require_runtime_report(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = launcher.main(["--root", str(MODULE_ROOT)])

    assert exit_code == 2
    assert "--root and --strict are valid only with --runtime-report" in capsys.readouterr().err
