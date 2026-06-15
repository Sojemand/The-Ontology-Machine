from __future__ import annotations

import argparse
import shutil
from pathlib import Path
from typing import Any, Callable

from tools.go_live_bundle.blockers import _blocking_issues
from tools.go_live_bundle.client_events import _write_client_frontend_snapshot
from tools.go_live_bundle.command_runner import _load_command_records, _validate_command_bounds
from tools.go_live_bundle.e2e_matrix import _write_e2e_matrix
from tools.go_live_bundle.evidence_reports import (
    _write_blockers,
    _write_dead_code_report,
    _write_docs_summary,
    _write_go_live_manifest,
    _write_phase19_evidence,
    _write_readiness_decision,
    _write_readme_markers,
    _write_residual_risks,
    _write_rollback_drill,
    _write_test_summary,
    _write_worktree_manifest,
)
from tools.go_live_bundle.fixtures import _ensure_realistic_corpus
from tools.go_live_bundle.paths import _default_run_id, _git_head_sha, _git_status_short, _mkdir, _source_commit_marker
from tools.go_live_bundle.scans import _scan_forbidden_matches
from tools.go_live_bundle.support_samples import _write_support_bundle_sample
from tools.go_live_bundle.surface_snapshots import _live_tool_surface_contracts, _write_runtime_snapshot


def main(
    module_root: Path,
    argv: list[str] | None,
    *,
    write_commands: Callable[..., list[dict[str, Any]]],
    write_tool_snapshots: Callable[[Path, str], None],
) -> int:
    parser = argparse.ArgumentParser(description="Generate the Phase 20 go-live evidence bundle.")
    parser.add_argument("--run-id", help="Explicit go-live run id.")
    parser.add_argument("--scaffold-only", action="store_true", help="Write the bundle without executing the full command matrix.")
    parser.add_argument("--resume", action="store_true", help="Resume an existing go-live bundle instead of recreating it.")
    parser.add_argument("--start-index", type=int, default=1, help="1-based command index to start executing from.")
    parser.add_argument("--end-index", type=int, help="1-based command index to stop executing at.")
    args = parser.parse_args(argv)
    start_index, end_index = _validate_command_bounds(args.start_index, args.end_index)

    run_id = args.run_id or _default_run_id()
    fixture_root = _ensure_realistic_corpus()
    bundle_root = module_root / "release" / "go_live" / run_id
    if bundle_root.exists() and not args.resume:
        shutil.rmtree(bundle_root)
    source_commit = _source_commit_marker()
    worktree_status = _git_status_short()
    fixture_root = _ensure_realistic_corpus()
    if args.resume and bundle_root.exists():
        scaffold_records = _load_command_records(bundle_root)
    else:
        _mkdir(bundle_root / "commands")
        _mkdir(bundle_root / "e2e_matrix")
        _mkdir(bundle_root / "snapshots")
        _mkdir(bundle_root / "redaction_checks")
        scaffold_records = write_commands(bundle_root, run_id, execute=False)

    scaffold_tool_surface_contracts = _live_tool_surface_contracts()
    scaffold_blockers = _blocking_issues(
        [],
        command_records=scaffold_records,
        scaffold_only=True,
        tool_surface_contracts=scaffold_tool_surface_contracts,
    )
    phase19_path = _write_phase19_evidence(bundle_root, run_id, scaffold_records)
    write_tool_snapshots(bundle_root, run_id)
    _write_client_frontend_snapshot(bundle_root, run_id)
    _write_runtime_snapshot(bundle_root, run_id)
    _write_support_bundle_sample(bundle_root, run_id)
    _write_e2e_matrix(bundle_root, run_id, fixture_root)
    _write_dead_code_report(bundle_root, run_id, [])
    _write_worktree_manifest(bundle_root, run_id, source_commit, worktree_status)
    _write_docs_summary(bundle_root, run_id, scaffold_blockers)
    rollback_source = _git_head_sha() or source_commit
    _write_rollback_drill(bundle_root, run_id, rollback_source)
    _write_blockers(bundle_root, scaffold_blockers)
    _write_residual_risks(bundle_root)
    _write_test_summary(bundle_root, run_id, scaffold_blockers, scaffold_records)
    scaffold_manifest = _write_go_live_manifest(bundle_root, run_id, source_commit, phase19_path, scaffold_blockers, scaffold_records)
    _write_readiness_decision(bundle_root, run_id, scaffold_manifest, scaffold_blockers, scaffold_records)

    command_records = write_commands(
        bundle_root,
        run_id,
        execute=not args.scaffold_only,
        existing_records=scaffold_records,
        start_index=start_index,
        end_index=end_index,
    )
    dead_code_matches = _scan_forbidden_matches()
    tool_surface_contracts = _live_tool_surface_contracts()
    blockers = _blocking_issues(
        dead_code_matches,
        command_records=command_records,
        scaffold_only=args.scaffold_only,
        tool_surface_contracts=tool_surface_contracts,
    )
    phase19_path = _write_phase19_evidence(bundle_root, run_id, command_records)
    write_tool_snapshots(bundle_root, run_id)
    _write_dead_code_report(bundle_root, run_id, dead_code_matches)
    _write_worktree_manifest(bundle_root, run_id, source_commit, worktree_status)
    _write_docs_summary(bundle_root, run_id, blockers)
    _write_rollback_drill(bundle_root, run_id, rollback_source)
    _write_blockers(bundle_root, blockers)
    _write_residual_risks(bundle_root)
    _write_test_summary(bundle_root, run_id, blockers, command_records)
    manifest = _write_go_live_manifest(bundle_root, run_id, source_commit, phase19_path, blockers, command_records)
    _write_readiness_decision(bundle_root, run_id, manifest, blockers, command_records)
    _write_readme_markers(bundle_root)

    print(str(bundle_root))
    return 0
