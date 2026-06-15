"""Summary result types for orchestrator actions."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class RunSummary:
    total: int = 0
    success: int = 0
    errors: int = 0
    needs_review: int = 0
    retries: int = 0
    run_id: str = ""
    run_log_path: str = ""
    tracked_hashes: tuple[str, ...] = ()


@dataclass
class ResetSummary:
    cleared_records: int = 0
    restored_sources: int = 0
    renamed_conflicts: int = 0
    removed_targets: int = 0


@dataclass
class PipelineLogResetSummary:
    cleared_records: int = 0
    removed_pipeline_targets: tuple[str, ...] = ()
    removed_log_targets: tuple[str, ...] = ()
