from __future__ import annotations

import sys
from pathlib import Path

from tools import visible_logged_runner


def test_visible_logged_runner_mirrors_output_to_console_and_logs(tmp_path: Path, capsys) -> None:
    stdout_log = tmp_path / "stdout.log"
    stderr_log = tmp_path / "stderr.log"

    exit_code = visible_logged_runner.main(
        [
            "--cwd",
            str(tmp_path),
            "--stdout-log",
            str(stdout_log),
            "--stderr-log",
            str(stderr_log),
            "--",
            sys.executable,
            "-c",
            "import sys; print('visible-out'); print('visible-err', file=sys.stderr)",
        ]
    )

    captured = capsys.readouterr()

    assert exit_code == 0
    assert "visible-out" in captured.out
    assert "visible-err" in captured.err
    assert "visible-out" in stdout_log.read_text(encoding="utf-8")
    assert "visible-err" in stderr_log.read_text(encoding="utf-8")
