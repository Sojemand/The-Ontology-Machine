"""Scan-only debug workflow."""

from __future__ import annotations

from ..context import ModuleContext
from . import debug_common_workflow, debug_preview, debug_support


def run_scan(payload: dict, *, context: ModuleContext, parse_scan_debug_input_command_fn) -> dict:
    try:
        command = parse_scan_debug_input_command_fn(payload)
        session_root = command.session_root
        output_root = session_root / "outputs"
        if debug_support.cancel_requested(session_root):
            return debug_common_workflow.cancelled(session_root, summary="Scan abgebrochen")
        debug_support.append_log(session_root, "[RUN] corpus_builder scan_debug_input gestartet")
        debug_support.write_snapshot(session_root, status="running", detail="Scanne Artefakte")
        preview = debug_preview.build_scan_preview(
            context,
            input_root=command.input_root,
            corpus_db_path=output_root / "corpus.db",
        )
        preview_path = debug_support.write_json(
            output_root / "preview_report.json",
            debug_preview.preview_payload(preview),
        )
        metrics = debug_preview.preview_metrics(preview)
        summary = f"{metrics['bundle_count']} Artefakte gefunden"
        debug_support.write_snapshot(
            session_root,
            status="ok",
            detail=summary,
            processed=metrics["bundle_count"],
            total=metrics["bundle_count"],
            counters=metrics,
        )
        debug_support.append_log(session_root, f"[OK] {summary}")
        return debug_support.write_result(
            session_root,
            {
                "status": "ok",
                "summary": summary,
                "metrics": metrics,
                "outputs": {"preview_report": [debug_support.relative_path(session_root, preview_path)]},
            },
        )
    except Exception as exc:
        return debug_common_workflow.error(payload, summary="Scan fehlgeschlagen", message=str(exc))
