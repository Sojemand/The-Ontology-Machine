from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from .command_matrix import ALL_COMMANDS, CommandSpec
from .paths import _json_file, _slug, _write_json
from .process_execution import _execute_command_spec


def _write_commands(
    bundle_root: Path,
    run_id: str,
    *,
    execute: bool,
    existing_records: list[dict[str, Any]] | None = None,
    start_index: int = 1,
    end_index: int | None = None,
    execute_command_spec: Callable[[int, CommandSpec, Path, str, Path], dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    runner = execute_command_spec or _execute_command_spec
    bounded_end = end_index or len(ALL_COMMANDS)
    if execute and existing_records is not None:
        structured = [dict(record) for record in existing_records]
        for index, spec in enumerate(ALL_COMMANDS, start=1):
            if index < start_index or index > bounded_end:
                continue
            filename = f"{index:02d}_{spec.module_key}_{_slug(spec.purpose)}.log"
            log_path = bundle_root / "commands" / filename
            structured[index - 1] = runner(index, spec, bundle_root, run_id, log_path)
            _write_command_matrix_files(bundle_root, run_id, structured)
        return structured

    structured: list[dict[str, Any]] = []
    for index, spec in enumerate(ALL_COMMANDS, start=1):
        filename = f"{index:02d}_{spec.module_key}_{_slug(spec.purpose)}.log"
        log_path = bundle_root / "commands" / filename
        record = runner(index, spec, bundle_root, run_id, log_path) if execute else _scaffold_record(index, spec, run_id, log_path)
        structured.append(record)
    _write_command_matrix_files(bundle_root, run_id, structured)
    return structured


def _load_command_records(bundle_root: Path) -> list[dict[str, Any]]:
    command_matrix_path = bundle_root / "commands" / "command_matrix.json"
    if not command_matrix_path.exists():
        return _write_commands(bundle_root, bundle_root.name, execute=False)
    payload = _json_file(command_matrix_path)
    records = payload.get("commands")
    if not isinstance(records, list) or len(records) != len(ALL_COMMANDS):
        raise ValueError("Existing command_matrix.json ist unvollstaendig oder ungueltig.")
    return [dict(record) for record in records]


def _validate_command_bounds(start_index: int, end_index: int | None) -> tuple[int, int | None]:
    if start_index < 1:
        raise ValueError("--start-index muss >= 1 sein.")
    if end_index is not None and end_index < start_index:
        raise ValueError("--end-index darf nicht kleiner als --start-index sein.")
    if start_index > len(ALL_COMMANDS):
        raise ValueError("--start-index liegt ausserhalb der Command-Matrix.")
    if end_index is not None and end_index > len(ALL_COMMANDS):
        raise ValueError("--end-index liegt ausserhalb der Command-Matrix.")
    return start_index, end_index


def _write_command_matrix_files(bundle_root: Path, run_id: str, structured: list[dict[str, Any]]) -> None:
    _write_json(bundle_root / "commands" / "command_matrix.json", {"schema_version": "semantic_control_kernel.phase20.command_matrix.v1", "commands": structured})
    lines = [
        "# Command Matrix",
        "",
        f"- `go_live_run_id`: `{run_id}`",
        "- Structured source: `commands/command_matrix.json`",
        "",
        "| # | Module | Purpose | Command | Workdir | Exit | Result | Log | Blocker |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for record in structured:
        lines.append(
            f"| {record['sequence_index']} | `{record['module_key']}` | `{record['purpose']}` | `{record['command']}` | "
            f"`{record['working_directory']}` | `{record['exit_code']}` | `{record['result']}` | `{record['log_path']}` | `{record['blocking_issue_anchor']}` |"
        )
    (bundle_root / "command_matrix.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _scaffold_record(index: int, spec: CommandSpec, run_id: str, log_path: Path) -> dict[str, Any]:
    record = {
        "sequence_index": index,
        "module_key": spec.module_key,
        "purpose": spec.purpose,
        "command": spec.command,
        "working_directory": spec.working_directory,
        "expected_test_scope": spec.expected_test_scope,
        "produced_evidence_path": f"commands/{log_path.name}",
        "log_path": f"commands/{log_path.name}",
        "exit_code": spec.exit_code,
        "result": spec.result,
        "blocking_issue_anchor": spec.blocker_anchor,
        "duration_seconds": 0.0,
    }
    log_path.write_text(
        "\n".join(
            [
                f"go_live_run_id={run_id}",
                f"command={spec.command}",
                f"working_directory={spec.working_directory}",
                f"expected_test_scope={spec.expected_test_scope}",
                f"exit_code={spec.exit_code}",
                f"result={spec.result}",
                "note=Phase 20 scaffold-only mode; replace with live command output during a real go-live attempt.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return record
