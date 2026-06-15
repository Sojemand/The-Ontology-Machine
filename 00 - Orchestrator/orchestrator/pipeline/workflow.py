"""Top-level queue and run workflow for the orchestrator pipeline."""

from __future__ import annotations

from ..integrations import default_module_keys
from ..models import RunSummary, utc_now_iso
from . import artifact_repository, debug, health_workflow, intake_workflow, record_repository, release_workflow, runtime_retention, runtime_semantics, stage_scheduler, storage_repository


def build_pending_queue(engine, ui_state):
    return record_repository.build_pending_queue(engine, ui_state)


def run(engine, ui_state, *, owner_input_hashes: set[str] | None = None) -> RunSummary:
    with storage_repository.mutation_lock(engine, "Run"):
        storage_repository.reload_state(engine)
        pending_queue = build_pending_queue(engine, ui_state)
        if owner_input_hashes is not None:
            pending_queue = [record for record in pending_queue if record.content_hash in owner_input_hashes]
        if ui_state.mode == "single":
            pending_queue = pending_queue[:1]
        tracked_hashes = {record.content_hash for record in pending_queue}
        run_id = utc_now_iso().replace(":", "-")
        runtime_dir = engine._runtime_root / run_id
        runtime_dir.mkdir(parents=True, exist_ok=True)
        runtime_retention.prune_run_history(engine._runtime_root, protected_names={runtime_dir.name})
        previous_log_path = engine._active_log_path
        engine._active_log_path = runtime_dir / "run.log"
        ctx = storage_repository.RunContext(ui_state=ui_state, run_id=run_id, runtime_dir=runtime_dir, run_log_path=engine._active_log_path, tracked_hashes=tracked_hashes, managed_roots=storage_repository.managed_roots(engine, ui_state))
        debug.reset_snapshot(engine, total=len(tracked_hashes))
        debug.append_log(engine, f"Run {ctx.run_id} started")
        debug.recompute_snapshot_counts(engine, tracked_hashes)
        ready_queue = intake_workflow.prepare_pending_queue(engine, pending_queue, ctx) if pending_queue else []
        required_module_keys = intake_workflow.required_live_modules(ready_queue, default_module_keys()) if ready_queue else ()
        try:
            if pending_queue:
                if ready_queue:
                    release_workflow.ensure_selected_release_is_active(engine, ui_state)
                health_workflow.run_preflight_healthcheck(
                    engine,
                    module_keys=required_module_keys,
                    scope="pipeline_run",
                    records=ready_queue,
                    ui_state=ui_state,
                )
            start_records = _build_scheduler_start_records(engine, ready_queue, tracked_hashes, ctx.managed_roots)
            if start_records:
                if ready_queue:
                    runtime_semantics.ensure_initialized(engine, ctx)
                stage_scheduler.run(engine, ctx, start_records)
        finally:
            engine._snapshot.is_running = False
            debug.emit_snapshot(engine)
            artifact_repository.prune_empty_dirs(ctx.runtime_dir, stop_at=(engine._state_dir,))
            artifact_repository.prune_empty_dirs(engine._runtime_root, stop_at=(engine._state_dir,))
            debug.append_log(engine, "Run aborted" if engine._snapshot.aborted else "Run finished")
            runtime_retention.prune_run_history(engine._runtime_root, protected_names={ctx.runtime_dir.name})
            engine._active_log_path = previous_log_path
        return RunSummary(
            total=engine._snapshot.total,
            success=engine._snapshot.success,
            errors=engine._snapshot.errors,
            needs_review=engine._snapshot.needs_review,
            retries=engine._snapshot.retries,
            run_id=run_id,
            run_log_path=str(ctx.run_log_path),
            tracked_hashes=tuple(sorted(tracked_hashes)),
        )


def _build_scheduler_start_records(engine, ready_queue, tracked_hashes, managed_roots):
    ordered: dict[str, object] = {}
    for record in ready_queue:
        ordered[record.content_hash] = record
    for record in record_repository.collect_retry_records(
        engine,
        filter_hashes=tracked_hashes,
        managed_roots=managed_roots,
    ):
        ordered.setdefault(record.content_hash, record)
    return list(ordered.values())
