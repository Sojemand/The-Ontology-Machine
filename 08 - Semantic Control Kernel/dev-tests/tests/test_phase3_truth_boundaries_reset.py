from __future__ import annotations

from pathlib import Path

from semantic_control_kernel.repository.paths import StatePaths
from semantic_control_kernel.repository.reset import KernelStateResetService


def test_reset_archives_runtime_state_and_preserves_kernel_audit_truth(tmp_path: Path) -> None:
    paths = StatePaths.from_state_root(tmp_path / "state")
    paths.ensure_layout()
    (paths.workflow_runs_active_dir / "wr.json").write_text("{}", encoding="utf-8")
    (paths.resume_dir / "wr.resume.json").write_text("{}", encoding="utf-8")
    (paths.events_recovery_dir / "rev" / "recovery_event.json").parent.mkdir(parents=True, exist_ok=True)
    (paths.events_recovery_dir / "rev" / "recovery_event.json").write_text("{}", encoding="utf-8")
    (paths.events_tool_availability_dir / "mev.json").write_text("{}", encoding="utf-8")
    (paths.bindings_records_dir / "binding.json").write_text("{}", encoding="utf-8")
    (paths.bindings_index_by_database_path_dir / "db_hash.json").write_text("{}", encoding="utf-8")
    (paths.bindings_index_by_artifact_root_dir / "root_hash.json").write_text("{}", encoding="utf-8")
    (paths.bindings_history_dir / "db_hash" / "stale.json").parent.mkdir(parents=True, exist_ok=True)
    (paths.bindings_history_dir / "db_hash" / "stale.json").write_text("{}", encoding="utf-8")
    (paths.attach_states_by_database_dir / "db_hash.json").write_text("{}", encoding="utf-8")
    (paths.attach_states_history_dir / "db_hash" / "old.json").parent.mkdir(parents=True, exist_ok=True)
    (paths.attach_states_history_dir / "db_hash" / "old.json").write_text("{}", encoding="utf-8")
    preserved_files = [
        paths.receipts_operations_dir / "opr.json",
        paths.support_index_path,
        paths.quarantine_partial_writes_dir / "partial.tmp",
    ]
    for path in preserved_files:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{}", encoding="utf-8")
    owner_module_path = tmp_path / "owner_module_state" / "database.sqlite"
    owner_module_path.parent.mkdir()
    owner_module_path.write_text("owner", encoding="utf-8")

    manifest = KernelStateResetService(paths).reset_runtime_state("test reset")

    reset_root = paths.archive_resets_dir / manifest.reset_id
    assert (reset_root / "workflow_runs" / "active" / "wr.json").exists()
    assert (reset_root / "resume" / "wr.resume.json").exists()
    assert (reset_root / "events" / "recovery" / "rev" / "recovery_event.json").exists()
    assert (reset_root / "events" / "tool_availability" / "mev.json").exists()
    assert (reset_root / "bindings" / "records" / "binding.json").exists()
    assert (reset_root / "bindings" / "index" / "by_database_path" / "db_hash.json").exists()
    assert (reset_root / "bindings" / "index" / "by_artifact_root" / "root_hash.json").exists()
    assert (reset_root / "attach_states" / "by_database" / "db_hash.json").exists()
    assert not list(paths.workflow_runs_active_dir.glob("*.json"))
    assert not list(paths.events_recovery_dir.glob("*"))
    assert not list(paths.bindings_records_dir.glob("*.json"))
    assert not list(paths.bindings_index_by_database_path_dir.glob("*.json"))
    assert not list(paths.bindings_index_by_artifact_root_dir.glob("*.json"))
    assert not list(paths.attach_states_by_database_dir.glob("*.json"))
    assert (paths.receipts_operations_dir / "opr.json").exists()
    assert (paths.bindings_history_dir / "db_hash" / "stale.json").exists()
    assert (paths.attach_states_history_dir / "db_hash" / "old.json").exists()
    assert (paths.quarantine_partial_writes_dir / "partial.tmp").exists()
    assert owner_module_path.read_text(encoding="utf-8") == "owner"
