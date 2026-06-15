from __future__ import annotations

from pathlib import Path

from phase20_truth_support import module


def test_execute_command_spec_uses_file_backed_capture_for_long_running_dispatchers(
    monkeypatch,
    tmp_path: Path,
) -> None:
    log_path = tmp_path / "commands" / "01_root_all_dev_tests.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    capture_paths: dict[str, Path] = {}

    class FakeProcess:
        def __init__(self, stdout, stderr) -> None:
            capture_paths["stdout"] = Path(stdout.name)
            capture_paths["stderr"] = Path(stderr.name)
            stdout.write("root matrix finished\\n")
            stderr.write("no pipe hang\\n")
            self._return_code = 0

        def poll(self) -> int:
            return self._return_code

        def wait(self, timeout=None) -> int:
            return self._return_code

    def fake_popen(*args, **kwargs):
        return FakeProcess(kwargs["stdout"], kwargs["stderr"])

    def fail_run(*args, **kwargs):
        raise AssertionError("subprocess.run must not be used for command output capture")

    monkeypatch.setattr(module.subprocess, "Popen", fake_popen)
    monkeypatch.setattr(module.subprocess, "run", fail_run)
    spec = module.CommandSpec(
        module_key="root",
        purpose="all_dev_tests",
        working_directory=".",
        command="run-dev-tests.bat --all",
        expected_test_scope="Root full dispatcher regression matrix.",
    )

    record = module._execute_command_spec(1, spec, tmp_path, "glv_unit", log_path)
    log_text = log_path.read_text(encoding="utf-8")

    assert record["result"] == "pass"
    assert "root matrix finished" in log_text
    assert "no pipe hang" in log_text
    assert not capture_paths["stdout"].exists()
    assert not capture_paths["stderr"].exists()


def test_write_commands_can_resume_a_subset_without_resetting_previous_records(tmp_path: Path, monkeypatch) -> None:
    bundle_root = tmp_path / "bundle"
    (bundle_root / "commands").mkdir(parents=True, exist_ok=True)
    scaffold = module._write_commands(bundle_root, "glv_unit", execute=False)

    def fake_execute(index, spec, _bundle_root, run_id, log_path):
        log_path.write_text(f"go_live_run_id={run_id}\nresult=pass\n", encoding="utf-8")
        return {
            "sequence_index": index,
            "module_key": spec.module_key,
            "purpose": spec.purpose,
            "command": spec.command,
            "working_directory": spec.working_directory,
            "expected_test_scope": spec.expected_test_scope,
            "produced_evidence_path": f"commands/{log_path.name}",
            "log_path": f"commands/{log_path.name}",
            "exit_code": 0,
            "result": "pass",
            "blocking_issue_anchor": "",
            "duration_seconds": 1.0,
        }

    monkeypatch.setattr(module, "_execute_command_spec", fake_execute)
    updated = module._write_commands(
        bundle_root,
        "glv_unit",
        execute=True,
        existing_records=scaffold,
        start_index=2,
        end_index=3,
    )

    assert updated[0]["result"] == "blocked"
    assert updated[1]["result"] == "pass"
    assert updated[2]["result"] == "pass"
    assert updated[3]["result"] == "blocked"


def test_frontend_build_uses_runner_config_loader_to_avoid_esbuild_config_bundle_failures() -> None:
    spec = next(item for item in module.FRONTEND_COMMANDS if item.purpose == "build")

    actual = module._actual_command(spec, module.CLIENT_FRONTEND_ROOT)

    assert actual[-2:] == ["--configLoader", "runner"]
    assert actual[0].endswith("node.exe")
    assert actual[1].endswith("node_modules\\vite\\bin\\vite.js")
