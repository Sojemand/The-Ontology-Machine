"""Headless debug-run implementation for the interpreter contract."""

from __future__ import annotations

from pathlib import Path

from ..interpreter.adapter import default_output_name
from ..profile_policy import payload_profile
from . import debug_support


def debug_run(
    payload: dict,
    *,
    load_dotenv_fn,
    load_config_fn,
    parse_debug_run_command_fn,
    load_request_payload_fn,
    process_single_fn,
    process_batch_fn,
) -> dict:
    try:
        command = parse_debug_run_command_fn(payload)
    except ValueError as exc:
        return _error_result(payload, summary="Debuglauf fehlgeschlagen", message=str(exc))
    session_root = command.session_root
    debug_support.append_log(session_root, "[RUN] interpreter debug_run gestartet")
    if debug_support.cancel_requested(session_root):
        return _cancelled(session_root, "Debuglauf abgebrochen")
    detail = command.request_path.name if command.request_path is not None else (command.input_root.name if command.input_root is not None else command.mode)
    debug_support.write_snapshot(session_root, status="running", detail=detail)
    try:
        load_dotenv_fn()
        config = _build_effective_config(load_config_fn(), command.runtime_settings)
        config.interpreter_profile = payload_profile(payload)
        result = (
            _run_batch(command, session_root, config, process_batch_fn)
            if command.mode == "batch"
            else _run_single(command, load_request_payload_fn, process_single_fn, config)
        )
    except Exception as exc:
        return _error_result(payload, summary="Debuglauf fehlgeschlagen", message=str(exc))
    if debug_support.cancel_requested(session_root):
        return _cancelled(session_root, "Debuglauf abgebrochen")
    if result.get("status") == "error":
        return _error_result(
            payload,
            summary=str(result.get("summary", "Debuglauf fehlgeschlagen")),
            message=str(result.get("error", "Interpreter-Fehler")),
            outputs=result.get("outputs"),
            metrics=result.get("metrics"),
        )
    summary = str(result.get("summary", "Interpretation abgeschlossen"))
    debug_support.write_snapshot(
        session_root,
        status="ok",
        detail=summary,
        processed=_snapshot_total(result),
        total=_snapshot_total(result),
        counters=_snapshot_counters(result),
    )
    debug_support.append_log(session_root, f"[RUN] {summary}")
    return debug_support.write_result(session_root, result)


def _build_effective_config(config, runtime_settings):
    config.model = runtime_settings.model
    config.max_output_tokens = runtime_settings.max_output_tokens
    config.thinking_effort = "no thinking"
    return config


def _cancelled(session_root: Path, summary: str) -> dict:
    debug_support.write_snapshot(session_root, status="cancelled", detail=summary)
    debug_support.append_log(session_root, f"[CANCELLED] {summary}")
    return debug_support.write_result(session_root, {"status": "cancelled", "summary": summary})


def _error_result(payload: dict, *, summary: str, message: str, outputs=None, metrics=None) -> dict:
    session_root_text = str(payload.get("session_root", "")).strip()
    if not session_root_text:
        return {"status": "error", "error": message}
    session_root = Path(session_root_text)
    if debug_support.cancel_requested(session_root):
        return _cancelled(session_root, "Debuglauf abgebrochen")
    debug_support.append_log(session_root, f"[ERROR] {message}")
    debug_support.write_snapshot(session_root, status="error", detail=message)
    return debug_support.write_result(
        session_root,
        {
            "status": "error",
            "summary": summary,
            "error": message,
            "outputs": dict(outputs or {}),
            "metrics": dict(metrics or {}),
        },
    )


def _run_single(command, load_request_payload_fn, process_single_fn, config):
    loaded_request = load_request_payload_fn(command.request_path)
    if debug_support.cancel_requested(command.session_root):
        return {"status": "cancelled", "summary": "Debuglauf abgebrochen"}
    output_path = command.output_root / default_output_name(
        loaded_request.request,
        fallback_stem=command.request_path.stem,
    )
    result = process_single_fn(loaded_request, output_path, config)
    if result.get("status") == "error":
        return {"status": "error", "summary": "Debuglauf fehlgeschlagen", "error": str(result.get("error", "Interpreter-Fehler"))}
    review_required = bool(result.get("needs_review", False))
    return {
        "status": "ok",
        "summary": "Interpretation abgeschlossen (Review erforderlich)" if review_required else "Interpretation abgeschlossen",
        "outputs": {"structured_output": [debug_support.relative_path(command.session_root, Path(str(result.get("output_path") or output_path)))]},
        "metrics": {"needs_review": review_required, "review_reason": str(result.get("review_reason", ""))},
    }


def _run_batch(command, session_root: Path, config, process_batch_fn):
    counters = {"ok": 0, "error": 0, "needs_review": 0}

    def _on_progress(item: dict, done: int, total: int) -> None:
        if item.get("status") in {"ok", "ok_review"}:
            counters["ok"] += 1
        else:
            counters["error"] += 1
        counters["needs_review"] += int(bool(item.get("needs_review")))
        debug_support.write_snapshot(session_root, status="running", detail=f"{done}/{total}: {item.get('file', '')}", processed=done, total=total, counters=counters)
        debug_support.append_log(session_root, f"[BATCH] {done}/{total} {item.get('file', '')}: {item.get('status', 'unknown')}")

    batch_result = process_batch_fn(
        command.input_root,
        command.output_root,
        config,
        num_workers=command.num_workers,
        on_progress=_on_progress,
        should_cancel=lambda: debug_support.cancel_requested(session_root),
    )
    outputs = [
        debug_support.relative_path(session_root, Path(str(item.get("output_path"))))
        for item in batch_result.get("results", [])
        if item.get("status") in {"ok", "ok_review"} and str(item.get("output_path", "")).strip()
    ]
    needs_review = sum(1 for item in batch_result.get("results", []) if bool(item.get("needs_review")))
    if batch_result.get("error"):
        return {
            "status": "error",
            "summary": "Batch abgeschlossen mit Fehlern",
            "error": f"{batch_result.get('error', 0)} von {batch_result.get('total', 0)} Requests fehlgeschlagen.",
            "outputs": {"structured_output": outputs},
            "metrics": {"ok": batch_result.get("ok", 0), "error": batch_result.get("error", 0), "total": batch_result.get("total", 0), "needs_review": needs_review, "total_cost_usd": batch_result.get("total_cost_usd")},
        }
    summary = "Batch abgeschlossen (Review erforderlich)" if needs_review else "Batch abgeschlossen"
    return {
        "status": "ok",
        "summary": summary,
        "outputs": {"structured_output": outputs},
        "metrics": {"ok": batch_result.get("ok", 0), "error": batch_result.get("error", 0), "total": batch_result.get("total", 0), "needs_review": needs_review, "total_cost_usd": batch_result.get("total_cost_usd")},
    }


def _snapshot_counters(response: dict) -> dict[str, int]:
    metrics = dict(response.get("metrics", {}))
    return {key: int(value) for key, value in metrics.items() if key in {"ok", "error", "total", "needs_review"}}


def _snapshot_total(response: dict) -> int:
    metrics = dict(response.get("metrics", {}))
    return int(metrics["total"]) if "total" in metrics else 1
