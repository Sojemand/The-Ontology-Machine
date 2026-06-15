from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Any


MODULE_ROOT = Path(__file__).resolve().parents[1]
if str(MODULE_ROOT) not in sys.path:
    sys.path.insert(0, str(MODULE_ROOT))

from tools.go_live_bundle import command_runner as _command_runner
from tools.go_live_bundle import surface_snapshots as _surface_snapshots
from tools.go_live_bundle.cli import main as _run_cli
from tools.go_live_bundle.client_events import (
    _EventAck,
    _Phase20EventSink,
    _build_client_frontend_snapshot_payload,
    _create_phase20_support_bundle,
    _event_belongs_to_phase20_snapshot,
    _list_all_client_frontend_events,
    _phase20_expiry,
    _phase20_state_paths,
    _phase20_state_snapshot_identity,
    _phase20_support_only_option,
    _phase20_target_identity,
    _write_client_frontend_snapshot,
)
from tools.go_live_bundle.command_matrix import (
    ALL_COMMANDS,
    FRONTEND_COMMANDS,
    KERNEL_COMMANDS,
    MCP_COMMANDS,
    OWNER_COMMANDS,
    ROOT_COMMANDS,
    SCAN_COMMANDS,
    CommandSpec,
)
from tools.go_live_bundle.evidence_reports import (
    _blocking_issues,
    _e2e,
    _phase19_capability,
    _write_blockers,
    _write_dead_code_report,
    _write_docs_summary,
    _write_e2e_matrix,
    _write_go_live_manifest,
    _write_phase19_evidence,
    _write_readiness_decision,
    _write_readme_markers,
    _write_residual_risks,
    _write_rollback_drill,
    _write_test_summary,
    _write_worktree_manifest,
    bundle_root_from_snapshots,
)
from tools.go_live_bundle.fixtures import _ensure_realistic_corpus, _write_realistic_fixture_manifest
from tools.go_live_bundle.paths import (
    ACTIVE_SCAN_ROOTS,
    CLIENT_FRONTEND_ROOT,
    FORBIDDEN_PATTERN,
    GENERATED_DIR_NAMES,
    GO_LIVE_BUNDLE_ROOT,
    MCP_SERVER_ROOT,
    PHASE19_REQUIRED_KERNEL_TESTS,
    PHASE20_TRUTH_INPUTS,
    PIPELINE_ROOT,
    _decision_from_results,
    _default_run_id,
    _git_head_sha,
    _git_status_short,
    _json_file,
    _mkdir,
    _run_git,
    _slug,
    _source_commit_marker,
    _write_json,
    phase20_truth_hash,
)
from tools.go_live_bundle.scans import (
    _execute_scan_command,
    _file_matches,
    _scan_forbidden_matches,
    _scan_recovery_tool_matches,
    _should_scan_file,
)
from tools.go_live_bundle.support_samples import _write_support_bundle_sample
from tools.go_live_bundle.surface_snapshots import (
    _live_tool_surface_contracts,
    _read_frontend_exported_string_list,
    _write_runtime_snapshot,
)


def _write_commands(
    bundle_root: Path,
    run_id: str,
    *,
    execute: bool,
    existing_records: list[dict[str, Any]] | None = None,
    start_index: int = 1,
    end_index: int | None = None,
) -> list[dict[str, Any]]:
    return _command_runner._write_commands(
        bundle_root,
        run_id,
        execute=execute,
        existing_records=existing_records,
        start_index=start_index,
        end_index=end_index,
        execute_command_spec=_execute_command_spec,
    )


def _load_command_records(bundle_root: Path) -> list[dict[str, Any]]:
    return _command_runner._load_command_records(bundle_root)


def _validate_command_bounds(start_index: int, end_index: int | None) -> tuple[int, int | None]:
    return _command_runner._validate_command_bounds(start_index, end_index)


def _write_command_matrix_files(bundle_root: Path, run_id: str, structured: list[dict[str, Any]]) -> None:
    _command_runner._write_command_matrix_files(bundle_root, run_id, structured)


def _scaffold_record(index: int, spec: CommandSpec, run_id: str, log_path: Path) -> dict[str, Any]:
    return _command_runner._scaffold_record(index, spec, run_id, log_path)


def _execute_command_spec(index: int, spec: CommandSpec, bundle_root: Path, run_id: str, log_path: Path) -> dict[str, Any]:
    return _command_runner._execute_command_spec(index, spec, bundle_root, run_id, log_path)


def _run_command_with_file_capture(
    actual_command: list[str],
    workdir: Path,
    *,
    timeout_seconds: int,
    log_path: Path,
) -> tuple[int, str, str, bool]:
    return _command_runner._run_command_with_file_capture(
        actual_command,
        workdir,
        timeout_seconds=timeout_seconds,
        log_path=log_path,
    )


def _pump_capture_output(path: Path, offset: int, stream: Any) -> int:
    return _command_runner._pump_capture_output(path, offset, stream)


def _coerce_output(value: bytes | str | None) -> str:
    return _command_runner._coerce_output(value)


def _actual_command(spec: CommandSpec, workdir: Path) -> list[str]:
    return _command_runner._actual_command(spec, workdir)


def _targeted_pytest_command(spec: CommandSpec, workdir: Path) -> list[str]:
    return _command_runner._targeted_pytest_command(spec, workdir)


def _module_local_test_path(name: str) -> str:
    return _command_runner._module_local_test_path(name)


def _suite_python(workdir: Path) -> Path:
    return _command_runner._suite_python(workdir)


def _write_tool_snapshots(bundle_root: Path, run_id: str) -> None:
    _surface_snapshots._write_tool_snapshots(
        bundle_root,
        run_id,
        contracts_loader=_live_tool_surface_contracts,
    )


def main(argv: list[str] | None = None) -> int:
    return _run_cli(MODULE_ROOT, argv, write_commands=_write_commands, write_tool_snapshots=_write_tool_snapshots)


if __name__ == "__main__":
    raise SystemExit(main())
