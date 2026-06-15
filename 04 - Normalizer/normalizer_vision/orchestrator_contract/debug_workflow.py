"""Headless debug-run implementation for normalizer orchestrator sessions."""
from __future__ import annotations

from pathlib import Path

from ..models import NormalizerRuntimeSettings
from ..normalizer import DocumentNormalizer
from . import debug_support
from .debug_batches import run_batch, run_single
from .debug_results import cancelled, error_result


def run_debug(
    payload: dict,
    *,
    root: Path,
    parse_debug_run_command_fn,
) -> dict:
    try:
        command = parse_debug_run_command_fn(payload)
    except ValueError as exc:
        return error_result(payload, summary="Debuglauf fehlgeschlagen", message=str(exc))
    session_root = command.session_root
    output_root = command.output_root
    session_root.mkdir(parents=True, exist_ok=True)
    output_root.mkdir(parents=True, exist_ok=True)
    debug_support.append_log(session_root, "[RUN] normalizer debug_run gestartet")
    if debug_support.cancel_requested(session_root):
        return cancelled(session_root, output_root, [], total=0, detail="Debuglauf abgebrochen")
    try:
        normalizer = DocumentNormalizer.from_project(root, runtime_settings=_runtime_settings(command.runtime_settings))
        if command.mode == "single":
            results, total, was_cancelled = run_single(command, session_root=session_root, output_root=output_root, normalizer=normalizer)
        else:
            results, total, was_cancelled = run_batch(command, session_root=session_root, output_root=output_root, normalizer=normalizer)
    except Exception as exc:
        return error_result(
            {"session_root": str(session_root), "output_root": str(output_root)},
            summary="Debuglauf fehlgeschlagen",
            message=str(exc),
        )
    if was_cancelled:
        return cancelled(session_root, output_root, results, total=total, detail="Debuglauf abgebrochen")
    metrics = debug_support.counters_from_results(results)
    outputs = debug_support.collect_outputs(session_root, output_root)
    status = "ok" if metrics["error_count"] == 0 else "error"
    summary = debug_support.summary_text(results)
    debug_support.write_snapshot(
        session_root,
        status=status,
        detail=summary,
        processed=len(results),
        total=total,
        counters=metrics,
    )
    debug_support.append_log(session_root, f"[RUN] {summary}")
    return debug_support.write_result(
        session_root,
        {"status": status, "summary": summary, "outputs": outputs, "metrics": metrics},
    )


def _runtime_settings(settings) -> NormalizerRuntimeSettings:
    return NormalizerRuntimeSettings(model=settings.model, max_output_tokens=settings.max_output_tokens)
