"""Debug-run result, cancellation, and error payload helpers."""
from __future__ import annotations

from pathlib import Path

from ..models.results import NormalizationResult
from ..providers import sanitize_secret_text
from . import debug_support


def cancelled(
    session_root: Path,
    output_root: Path,
    results: list[NormalizationResult],
    *,
    total: int,
    detail: str,
) -> dict:
    metrics = debug_support.counters_from_results(results)
    outputs = debug_support.collect_outputs(session_root, output_root)
    debug_support.write_snapshot(
        session_root,
        status="cancelled",
        detail=detail,
        processed=len(results),
        total=total,
        counters=metrics,
    )
    debug_support.append_log(session_root, f"[CANCELLED] {detail}")
    return debug_support.write_result(
        session_root,
        {"status": "cancelled", "summary": detail, "outputs": outputs, "metrics": metrics},
    )


def error_result(payload: dict, *, summary: str, message: str) -> dict:
    safe_message = sanitize_secret_text(message)
    session_root_text = str(payload.get("session_root", "")).strip()
    if not session_root_text:
        return {"status": "error", "error": safe_message}
    session_root = Path(session_root_text)
    output_root_text = str(payload.get("output_root", "")).strip()
    output_root = Path(output_root_text) if output_root_text else (session_root / "outputs")
    session_root.mkdir(parents=True, exist_ok=True)
    output_root.mkdir(parents=True, exist_ok=True)
    if debug_support.cancel_requested(session_root):
        return cancelled(session_root, output_root, [], total=0, detail="Debuglauf abgebrochen")
    metrics = debug_support.counters_from_results([])
    outputs = debug_support.collect_outputs(session_root, output_root)
    debug_support.append_log(session_root, f"[ERROR] {safe_message}")
    debug_support.write_snapshot(session_root, status="error", detail=safe_message, processed=0, total=0, counters=metrics)
    return debug_support.write_result(
        session_root,
        {"status": "error", "summary": summary, "error": safe_message, "outputs": outputs, "metrics": metrics},
    )


def log_result(session_root: Path, result: NormalizationResult) -> None:
    message = sanitize_secret_text(result.message)
    review_reason = sanitize_secret_text(result.review_reason)
    suffix = f" | {message}" if message else ""
    if review_reason:
        suffix += f" | review_reason={review_reason}"
    debug_support.append_log(
        session_root,
        f"[{result.status}] {Path(result.input_path).name} -> {result.output_path or '-'} ({result.duration_ms}ms){suffix}",
    )
