"""Debug load execution workflow."""

from __future__ import annotations

from ..context import ModuleContext
from . import debug_common_workflow, debug_preview, debug_run_batches, debug_support


def run_debug(payload: dict, *, context: ModuleContext, parse_debug_run_command_fn, load_batch_fn) -> dict:
    try:
        command = parse_debug_run_command_fn(payload)
        if debug_support.cancel_requested(command.session_root):
            return debug_common_workflow.cancelled(command.session_root, summary="Debuglauf abgebrochen")
        debug_support.append_log(command.session_root, "[RUN] corpus_builder debug_run gestartet")
        preview = debug_run_batches.preview_for_run(context, command)
        preview_path = debug_support.write_json(
            command.output_root / "preview_report.json",
            debug_preview.preview_payload(preview),
        )
        base_metrics = debug_preview.preview_metrics(preview)
        debug_support.write_snapshot(
            command.session_root,
            status="running",
            detail="Bereite Corpus-Load vor",
            processed=0,
            total=base_metrics["bundle_count"],
            counters=base_metrics,
        )
        batch, cancelled, extra = debug_run_batches.run_batches(
            context,
            command,
            bundles=list(preview["bundles"]),
            base_metrics=base_metrics,
            load_batch_fn=load_batch_fn,
        )
        load_path = _write_load_report(command, batch, extra)
        metrics = {**base_metrics, "loaded": batch.loaded, "skipped": batch.skipped, "archived": batch.archived, "errors": batch.errors}
        status = debug_common_workflow.result_status(batch, cancelled=cancelled)
        summary = debug_common_workflow.summary_text(batch, cancelled=cancelled)
        outputs = _outputs(command, preview_path, load_path)
        debug_support.write_snapshot(
            command.session_root,
            status=status,
            detail=summary,
            processed=len(batch.results),
            total=base_metrics["bundle_count"],
            counters=metrics,
        )
        debug_support.append_log(command.session_root, f"[{status.upper()}] {summary}")
        return debug_support.write_result(command.session_root, {"status": status, "summary": summary, "metrics": metrics, "outputs": outputs})
    except Exception as exc:
        return debug_common_workflow.error(payload, summary="Debuglauf fehlgeschlagen", message=str(exc))


def _write_load_report(command, batch, extra: dict) -> object:
    return debug_support.write_json(
        command.output_root / "load_report.json",
        {
            "mode": command.mode,
            "corpus_db_path": str(command.output_root / "corpus.db"),
            "loaded": batch.loaded,
            "skipped": batch.skipped,
            "archived": batch.archived,
            "errors": batch.errors,
            "results": [debug_common_workflow.result_row(item) for item in batch.results],
            **extra,
        },
    )


def _outputs(command, preview_path, load_path) -> dict[str, list[str]]:
    outputs = {
        "preview_report": [debug_support.relative_path(command.session_root, preview_path)],
        "load_report": [debug_support.relative_path(command.session_root, load_path)],
    }
    corpus_db = command.output_root / "corpus.db"
    if corpus_db.exists():
        outputs["corpus_db"] = [debug_support.relative_path(command.session_root, corpus_db)]
    return outputs
