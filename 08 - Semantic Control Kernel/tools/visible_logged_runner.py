from __future__ import annotations

import argparse
import subprocess
import sys
import threading
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run a command while mirroring stdout/stderr to the console and log files.",
    )
    parser.add_argument("--cwd", required=True, help="Working directory for the child process.")
    parser.add_argument("--stdout-log", required=True, help="Path to the stdout log file.")
    parser.add_argument("--stderr-log", required=True, help="Path to the stderr log file.")
    parser.add_argument("command", nargs=argparse.REMAINDER, help="Command to execute after '--'.")
    args = parser.parse_args(argv)

    command = list(args.command)
    if command and command[0] == "--":
        command = command[1:]
    if not command:
        parser.error("No child command was provided.")

    cwd = Path(args.cwd)
    stdout_log_path = Path(args.stdout_log)
    stderr_log_path = Path(args.stderr_log)
    stdout_log_path.parent.mkdir(parents=True, exist_ok=True)
    stderr_log_path.parent.mkdir(parents=True, exist_ok=True)

    with stdout_log_path.open("w", encoding="utf-8", errors="replace") as stdout_log, stderr_log_path.open(
        "w",
        encoding="utf-8",
        errors="replace",
    ) as stderr_log:
        process = subprocess.Popen(
            command,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
        )
        assert process.stdout is not None
        assert process.stderr is not None

        stdout_thread = threading.Thread(
            target=_pump_stream,
            args=(process.stdout, sys.stdout, stdout_log),
            daemon=True,
        )
        stderr_thread = threading.Thread(
            target=_pump_stream,
            args=(process.stderr, sys.stderr, stderr_log),
            daemon=True,
        )
        stdout_thread.start()
        stderr_thread.start()

        exit_code = int(process.wait())
        stdout_thread.join()
        stderr_thread.join()
        return exit_code


def _pump_stream(source, console_stream, log_handle) -> None:
    for chunk in iter(source.readline, ""):
        console_stream.write(chunk)
        console_stream.flush()
        log_handle.write(chunk)
        log_handle.flush()
    source.close()


if __name__ == "__main__":
    raise SystemExit(main())
