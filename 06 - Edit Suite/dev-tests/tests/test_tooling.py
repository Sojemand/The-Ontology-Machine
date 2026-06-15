from __future__ import annotations

from conftest import PIPELINE_ROOT


def test_root_tooling_includes_edit_suite_slot() -> None:
    build_runtime = "\n".join(
        [
            (PIPELINE_ROOT / "tools" / "build-runtimes.py").read_text(encoding="utf-8"),
            (PIPELINE_ROOT / "tools" / "runtime_build_config.py").read_text(encoding="utf-8"),
        ]
    )
    run_dev_tests = (PIPELINE_ROOT / "tools" / "run-dev-tests.py").read_text(encoding="utf-8")
    bootstrap = (PIPELINE_ROOT / "tools" / "dev-tests" / "bootstrap.bat").read_text(encoding="utf-8")
    root_dispatcher = (PIPELINE_ROOT / "run-dev-tests.bat").read_text(encoding="utf-8")
    assert '"06 - Edit Suite"' in build_runtime
    assert '"06 - Edit Suite"' in run_dev_tests
    assert r"06 - Edit Suite\runtime\python\python.exe" in bootstrap.replace("/", "\\")
    assert r"06 - Edit Suite\runtime\python\python.exe" in root_dispatcher.replace("/", "\\")


def test_launcher_runs_runtime_preflight_before_gui() -> None:
    run_bat = (PIPELINE_ROOT / "06 - Edit Suite" / "run.bat").read_text(encoding="utf-8")

    assert "edit_suite.bootstrap.runtime_report" in run_bat
    assert "--mode runtime" in run_bat
    assert "-m edit_suite\n" in run_bat.replace("\r\n", "\n")
