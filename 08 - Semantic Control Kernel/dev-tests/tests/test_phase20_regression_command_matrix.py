from __future__ import annotations

import sys
from pathlib import Path

from phase20_go_live_support import command_matrix, latest_go_live_dir


MODULE_ROOT = Path(__file__).resolve().parents[2]
if str(MODULE_ROOT) not in sys.path:
    sys.path.insert(0, str(MODULE_ROOT))

from tools.generate_go_live_bundle import ALL_COMMANDS  # noqa: E402


def test_every_required_phase20_command_is_represented_with_log_and_result() -> None:
    root = latest_go_live_dir()
    payload = command_matrix()
    commands = payload["commands"]

    assert len(commands) == len(ALL_COMMANDS)
    actual = [(item["working_directory"], item["command"]) for item in commands]
    expected = [(spec.working_directory, spec.command) for spec in ALL_COMMANDS]
    assert actual == expected

    for item in commands:
        assert item["log_path"]
        assert item["produced_evidence_path"]
        assert item["result"] in {"pass", "fail", "blocked"}
        assert isinstance(item["exit_code"], int)
        assert (root / item["log_path"]).is_file()


def test_kernel_test_commands_use_module_local_paths_and_not_host_python() -> None:
    for item in command_matrix()["commands"]:
        command = str(item["command"])
        if str(item["working_directory"]) != "08 - Semantic Control Kernel":
            continue
        if not command.startswith("dev-tests\\run-tests.bat tests\\"):
            continue
        normalized = command.replace("/", "\\")
        assert "dev-tests\\tests\\" not in normalized
        assert not normalized.lower().startswith("python ")
