from __future__ import annotations

from pathlib import Path


class StatePathDirectoryProperties:
    state_root: Path

    @property
    def tmp_dir(self) -> Path:
        return self.state_root / ".tmp"

    @property
    def fs_locks_dir(self) -> Path:
        return self.state_root / ".fs_locks"

    @property
    def workflow_runs_active_dir(self) -> Path:
        return self.state_root / "workflow_runs" / "active"

    @property
    def workflow_runs_history_dir(self) -> Path:
        return self.state_root / "workflow_runs" / "history"

    @property
    def resume_dir(self) -> Path:
        return self.state_root / "resume"

    @property
    def pending_confirmations_active_dir(self) -> Path:
        return self.state_root / "pending_confirmations" / "active"

    @property
    def pending_confirmations_history_dir(self) -> Path:
        return self.state_root / "pending_confirmations" / "history"

    @property
    def pending_interactions_active_dir(self) -> Path:
        return self.state_root / "pending_interactions" / "active"

    @property
    def pending_interactions_history_dir(self) -> Path:
        return self.state_root / "pending_interactions" / "history"

    @property
    def locks_active_dir(self) -> Path:
        return self.state_root / "locks" / "active"

    @property
    def locks_history_dir(self) -> Path:
        return self.state_root / "locks" / "history"

    @property
    def receipts_confirmations_dir(self) -> Path:
        return self.state_root / "receipts" / "confirmations"

    @property
    def receipts_operations_dir(self) -> Path:
        return self.state_root / "receipts" / "operations"

    @property
    def receipts_recoveries_dir(self) -> Path:
        return self.state_root / "receipts" / "recoveries"

    @property
    def receipt_index_by_workflow_dir(self) -> Path:
        return self.state_root / "receipts" / "index" / "by_workflow"

    @property
    def receipt_index_by_target_dir(self) -> Path:
        return self.state_root / "receipts" / "index" / "by_target"

    @property
    def events_progress_dir(self) -> Path:
        return self.state_root / "events" / "progress"

    @property
    def events_mirror_dir(self) -> Path:
        return self.state_root / "events" / "mirror"

    @property
    def events_recovery_dir(self) -> Path:
        return self.state_root / "events" / "recovery"

    @property
    def events_tool_availability_dir(self) -> Path:
        return self.state_root / "events" / "tool_availability"

    @property
    def attach_states_by_database_dir(self) -> Path:
        return self.state_root / "attach_states" / "by_database"

    @property
    def attach_states_history_dir(self) -> Path:
        return self.state_root / "attach_states" / "history"

    @property
    def artifact_trees_active_dir(self) -> Path:
        return self.state_root / "artifact_trees" / "active"

    @property
    def artifact_trees_history_dir(self) -> Path:
        return self.state_root / "artifact_trees" / "history"

    @property
    def bindings_records_dir(self) -> Path:
        return self.state_root / "bindings" / "records"

    @property
    def bindings_index_by_database_path_dir(self) -> Path:
        return self.state_root / "bindings" / "index" / "by_database_path"

    @property
    def bindings_index_by_artifact_root_dir(self) -> Path:
        return self.state_root / "bindings" / "index" / "by_artifact_root"

    @property
    def bindings_history_dir(self) -> Path:
        return self.state_root / "bindings" / "history"

    @property
    def adapter_calls_dir(self) -> Path:
        return self.state_root / "adapter_calls"

    @property
    def support_index_path(self) -> Path:
        return self.state_root / "support" / "index.json"

    @property
    def support_bundles_dir(self) -> Path:
        return self.state_root / "support" / "bundles"

    @property
    def support_cleanup_history_dir(self) -> Path:
        return self.state_root / "support" / "cleanup_history"

    @property
    def debug_traces_dir(self) -> Path:
        return self.state_root / "debug" / "traces"

    @property
    def debug_adapter_calls_dir(self) -> Path:
        return self.state_root / "debug" / "adapter_calls"

    @property
    def debug_background_continuations_dir(self) -> Path:
        return self.state_root / "debug" / "background_continuations"

    @property
    def debug_llm_attempts_dir(self) -> Path:
        return self.state_root / "debug" / "llm_attempts"

    @property
    def debug_redaction_reports_dir(self) -> Path:
        return self.state_root / "debug" / "redaction_reports"

    @property
    def archive_resets_dir(self) -> Path:
        return self.state_root / "archive" / "resets"

    @property
    def quarantine_corrupt_dir(self) -> Path:
        return self.state_root / "quarantine" / "corrupt"

    @property
    def quarantine_partial_writes_dir(self) -> Path:
        return self.state_root / "quarantine" / "partial_writes"
