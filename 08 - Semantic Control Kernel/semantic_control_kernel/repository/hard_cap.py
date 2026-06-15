from __future__ import annotations

import shutil
from pathlib import Path

from semantic_control_kernel.repository.hard_cap_file_ops import (
    delete_overflow_files_older_than,
    delete_unlocked_overflow_files,
    delete_overflow_files,
    file_count_exceeds,
    prune_directory_children_by_count_and_size,
    prune_directory_children,
    prune_run_directory_root,
    remove_empty_dir,
    sorted_dirs,
    sorted_files,
)
from semantic_control_kernel.repository.hard_cap_limits import (
    ARCHIVE_RESET_HARD_CAP,
    DEBUG_ADAPTER_FILES_PER_WORKFLOW_HARD_CAP,
    DEBUG_ADAPTER_WORKFLOW_DIR_HARD_CAP,
    DEBUG_LLM_FILES_PER_RUN_HARD_CAP,
    DEBUG_LLM_RUN_DIR_HARD_CAP,
    FS_LOCK_FILE_HARD_CAP,
    LOCK_HISTORY_HARD_CAP,
    MIRROR_EVENT_HARD_CAP,
    NESTED_HISTORY_DIR_HARD_CAP,
    NESTED_HISTORY_FILES_PER_DIR_HARD_CAP,
    PENDING_CONFIRMATION_HISTORY_HARD_CAP,
    PENDING_INTERACTION_HISTORY_HARD_CAP,
    PROGRESS_FILES_PER_WORKFLOW_HARD_CAP,
    PROGRESS_WORKFLOW_DIR_HARD_CAP,
    QUARANTINE_ENTRY_HARD_CAP,
    RAW_ADAPTER_CALL_DIR_HARD_CAP,
    RAW_ADAPTER_CALL_DIR_BYTES_HARD_CAP,
    RAW_ADAPTER_CALL_TOTAL_BYTES_HARD_CAP,
    RECEIPT_CONFIRMATION_HARD_CAP,
    RECEIPT_OPERATION_HARD_CAP,
    RECEIPT_RECOVERY_HARD_CAP,
    SUPPORT_BUNDLE_HARD_CAP,
    SUPPORT_CLEANUP_HISTORY_HARD_CAP,
    TMP_FILE_HARD_CAP,
    TMP_FILE_MIN_AGE_SECONDS,
    TRACE_WORKFLOW_DIR_HARD_CAP,
    WORKFLOW_HISTORY_HARD_CAP,
)
from semantic_control_kernel.repository.hard_cap_protection import (
    protected_receipt_ids,
    support_bundle_manifests,
    support_bundle_relative_child_names,
)
from semantic_control_kernel.repository.paths import StatePaths


class KernelStateHardCapService:
    def __init__(self, paths: StatePaths) -> None:
        self.paths = paths
        from semantic_control_kernel.repository.atomic_json import AtomicJsonStore

        self._json = AtomicJsonStore(paths, "state_hard_cap")

    def prune_all(self) -> None:
        for action in (
            self.prune_orphan_temp_files,
            self.prune_fs_locks,
            self.prune_mirror_events,
            self.prune_progress_workflows,
            self.prune_workflow_run_history,
            self.prune_pending_confirmation_history,
            self.prune_pending_interaction_history,
            self.prune_lock_history,
            self.prune_support_bundles,
            self.prune_receipts,
            self.prune_support_cleanup_history,
            self.prune_debug_trace_workflows,
            self.prune_debug_adapter_workflows,
            self.prune_debug_llm_runs,
            self.prune_raw_adapter_calls,
            self.prune_archive_resets,
        ):
            action()
        for root_dir in (self.paths.attach_states_history_dir, self.paths.artifact_trees_history_dir, self.paths.bindings_history_dir):
            self.prune_nested_history_root(root_dir)
        for root_dir in (self.paths.quarantine_corrupt_dir, self.paths.quarantine_partial_writes_dir):
            self.prune_quarantine_dir(root_dir)

    def prune_mirror_events(self) -> None:
        overflow = len(sorted_files(self.paths.events_mirror_dir)) - MIRROR_EVENT_HARD_CAP
        if overflow <= 0:
            return
        for stale_path in sorted_files(self.paths.events_mirror_dir)[:overflow]:
            self._json.delete_json(stale_path)
            self._json.delete_json(self.paths.events_tool_availability_dir / stale_path.name)

    def prune_progress_workflows(self) -> None:
        prune_run_directory_root(
            self.paths.events_progress_dir,
            dir_cap=PROGRESS_WORKFLOW_DIR_HARD_CAP,
            file_cap=PROGRESS_FILES_PER_WORKFLOW_HARD_CAP,
            protected_dirs=self._active_workflow_run_ids(),
        )

    def prune_workflow_run_history(self) -> None:
        protected_names = {f"{workflow_run_id}.json" for workflow_run_id in self._active_workflow_run_ids()}
        delete_overflow_files(self.paths.workflow_runs_history_dir, keep=WORKFLOW_HISTORY_HARD_CAP, protected_names=protected_names)

    def prune_pending_confirmation_history(self) -> None:
        delete_overflow_files(self.paths.pending_confirmations_history_dir, keep=PENDING_CONFIRMATION_HISTORY_HARD_CAP)

    def prune_pending_interaction_history(self) -> None:
        delete_overflow_files(self.paths.pending_interactions_history_dir, keep=PENDING_INTERACTION_HISTORY_HARD_CAP)

    def prune_lock_history(self) -> None:
        delete_overflow_files(self.paths.locks_history_dir, keep=LOCK_HISTORY_HARD_CAP)

    def prune_nested_history_root(self, root_dir: Path) -> None:
        if not root_dir.exists():
            return
        for child in sorted_dirs(root_dir):
            delete_overflow_files(child, keep=NESTED_HISTORY_FILES_PER_DIR_HARD_CAP)
            remove_empty_dir(child)
        overflow = len([path for path in sorted_dirs(root_dir) if path.is_dir()]) - NESTED_HISTORY_DIR_HARD_CAP
        if overflow > 0:
            for stale_dir in sorted_dirs(root_dir)[:overflow]:
                shutil.rmtree(stale_dir, ignore_errors=True)

    def prune_support_bundles(self) -> None:
        manifests = support_bundle_manifests(self.paths, self._json)
        overflow = len(manifests) - SUPPORT_BUNDLE_HARD_CAP
        if overflow <= 0:
            return
        from semantic_control_kernel.repository.support_bundles import SupportBundleStore

        store = SupportBundleStore(self.paths)
        for manifest in manifests[:overflow]:
            support_bundle_id = str(manifest.get("support_bundle_id") or "")
            if support_bundle_id:
                store.delete_bundle(support_bundle_id)

    def prune_receipts(self, *, rebuild_indexes: bool = True) -> set[str]:
        if not self._receipt_dirs_exceed_caps():
            return set()
        protected_ids = protected_receipt_ids(self.paths, self._json)
        deleted_ids = self._prune_receipt_dir(self.paths.receipts_operations_dir, RECEIPT_OPERATION_HARD_CAP, protected_ids)
        deleted_ids |= self._prune_receipt_dir(self.paths.receipts_confirmations_dir, RECEIPT_CONFIRMATION_HARD_CAP, protected_ids)
        deleted_ids |= self._prune_receipt_dir(self.paths.receipts_recoveries_dir, RECEIPT_RECOVERY_HARD_CAP, protected_ids)
        if deleted_ids and rebuild_indexes:
            from semantic_control_kernel.repository.receipt_store import ReceiptStore

            ReceiptStore(self.paths).rebuild_indexes()
        return deleted_ids

    def prune_support_cleanup_history(self) -> None:
        delete_overflow_files(self.paths.support_cleanup_history_dir, keep=SUPPORT_CLEANUP_HISTORY_HARD_CAP)

    def prune_debug_trace_workflows(self) -> None:
        prune_directory_children(self.paths.debug_traces_dir, keep=TRACE_WORKFLOW_DIR_HARD_CAP, protected_names=self._active_workflow_run_ids())

    def prune_debug_adapter_workflows(self) -> None:
        protected_dirs = support_bundle_relative_child_names(self.paths, self._json, "debug/adapter_calls")
        prune_run_directory_root(self.paths.debug_adapter_calls_dir, dir_cap=DEBUG_ADAPTER_WORKFLOW_DIR_HARD_CAP, file_cap=DEBUG_ADAPTER_FILES_PER_WORKFLOW_HARD_CAP, protected_dirs=protected_dirs | self._active_workflow_run_ids())

    def prune_debug_llm_runs(self) -> None:
        protected_dirs = support_bundle_relative_child_names(self.paths, self._json, "debug/llm_attempts")
        prune_run_directory_root(self.paths.debug_llm_attempts_dir, dir_cap=DEBUG_LLM_RUN_DIR_HARD_CAP, file_cap=DEBUG_LLM_FILES_PER_RUN_HARD_CAP, protected_dirs=protected_dirs)

    def prune_raw_adapter_calls(self) -> None:
        protected_dirs = support_bundle_relative_child_names(self.paths, self._json, "adapter_calls")
        prune_directory_children_by_count_and_size(
            self.paths.adapter_calls_dir,
            keep=RAW_ADAPTER_CALL_DIR_HARD_CAP,
            max_total_bytes=RAW_ADAPTER_CALL_TOTAL_BYTES_HARD_CAP,
            max_child_bytes=RAW_ADAPTER_CALL_DIR_BYTES_HARD_CAP,
            protected_names=protected_dirs,
        )

    def prune_orphan_temp_files(self) -> None:
        self._json.quarantine_orphan_temp_files(older_than_seconds=TMP_FILE_MIN_AGE_SECONDS)
        delete_overflow_files_older_than(
            self.paths.tmp_dir,
            keep=TMP_FILE_HARD_CAP,
            min_age_seconds=TMP_FILE_MIN_AGE_SECONDS,
        )

    def prune_fs_locks(self) -> None:
        delete_unlocked_overflow_files(self.paths.fs_locks_dir, keep=FS_LOCK_FILE_HARD_CAP)

    def prune_archive_resets(self) -> None:
        prune_directory_children(self.paths.archive_resets_dir, keep=ARCHIVE_RESET_HARD_CAP)

    def prune_quarantine_dir(self, root_dir: Path) -> None:
        base_entries = [path for path in sorted_files(root_dir) if not path.name.endswith(".reason.json")] if root_dir.exists() else []
        overflow = len(base_entries) - QUARANTINE_ENTRY_HARD_CAP
        if overflow <= 0:
            return
        for stale_path in base_entries[:overflow]:
            stale_path.unlink(missing_ok=True)
            stale_path.with_name(stale_path.name + ".reason.json").unlink(missing_ok=True)

    def _prune_receipt_dir(self, directory: Path, keep: int, protected_receipt_ids: set[str]) -> set[str]:
        protected_names = {f"{receipt_id}.json" for receipt_id in protected_receipt_ids}
        return {path.stem for path in delete_overflow_files(directory, keep=keep, protected_names=protected_names)}

    def _receipt_dirs_exceed_caps(self) -> bool:
        return (
            file_count_exceeds(self.paths.receipts_operations_dir, RECEIPT_OPERATION_HARD_CAP)
            or file_count_exceeds(self.paths.receipts_confirmations_dir, RECEIPT_CONFIRMATION_HARD_CAP)
            or file_count_exceeds(self.paths.receipts_recoveries_dir, RECEIPT_RECOVERY_HARD_CAP)
        )

    def _active_workflow_run_ids(self) -> set[str]:
        return {path.stem for path in self.paths.workflow_runs_active_dir.glob("*.json")}
