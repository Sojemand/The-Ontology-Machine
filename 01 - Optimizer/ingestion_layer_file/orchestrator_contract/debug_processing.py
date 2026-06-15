"""Headless scan and debug-run implementations for the orchestrator contract."""

from __future__ import annotations

import threading
from pathlib import Path

from ..input_catalog import InputCatalog
from ..processor import policy as processor_policy
from . import debug_support, validation

_PAGE_ASSET_CHILD_RESERVED = len("\\page_999.png")


def scan_debug_input(payload: dict, *, root: Path, app_home: Path | None) -> dict:
    session_root = validation.require_session_root(payload)
    input_root = validation.require_input_root(payload)
    validation.require_mode(payload, allowed=("scan",))
    filters = validation.require_filters(payload)
    debug_support.append_log(session_root, "[SCAN] starte Input-Preview")
    if debug_support.cancel_requested(session_root):
        return _cancelled(session_root, "Scan abgebrochen")
    layout = _layout(root, app_home)
    catalog = InputCatalog(
        input_root,
        state_dir=layout.state_dir if validation.use_processed_hashes(payload) else None,
        output_dir=layout.output_dir,
    )
    if not catalog.refresh():
        raise FileNotFoundError(f"Input-Ordner nicht gefunden: {input_root}")
    filtered = list(catalog.iter_filtered(filters))
    if debug_support.cancel_requested(session_root):
        return _cancelled(session_root, "Scan abgebrochen")
    result = {
        "status": "ok",
        "summary": debug_support.filtered_summary(filtered),
        "total_count": len(filtered),
        "total_size": sum(entry.size_bytes for entry in filtered),
        "skipped_processed_count": catalog.skipped_processed_count if validation.use_processed_hashes(payload) else 0,
        "skipped_duplicate_count": catalog.skipped_duplicate_count,
        "entries": debug_support.catalog_entries(filtered),
    }
    debug_support.write_snapshot(session_root, status="ok", detail=f"{len(filtered)} Dateien", processed=len(filtered), total=len(filtered))
    debug_support.append_log(session_root, f"[SCAN] {len(filtered)} Dateien im Preview")
    return debug_support.write_result(session_root, result)


def debug_run(
    payload: dict,
    *,
    root: Path,
    app_home: Path | None,
    load_config,
    plugin_manager_cls,
    processor_cls,
) -> dict:
    session_root = validation.require_session_root(payload)
    output_root = validation.require_output_root(payload)
    mode = validation.require_mode(payload, allowed=("single", "batch"))
    input_root = validation.require_input_root(payload) if mode == "batch" else None
    filters = validation.require_filters(payload)
    worker_count = validation.require_worker_count(payload)
    if debug_support.cancel_requested(session_root):
        return _cancelled(session_root, "Debuglauf abgebrochen")
    layout = _layout(root, app_home)
    config = load_config(layout.default_config_path)
    config.parallel_workers = worker_count
    plugin_mgr = plugin_manager_cls(layout.plugins_dir, config)
    total = 1
    try:
        if mode == "single":
            result = _run_single(payload, session_root, output_root, config, plugin_mgr, processor_cls)
        else:
            assert input_root is not None
            result, total = _run_batch(
                payload,
                input_root,
                session_root,
                output_root,
                config,
                plugin_mgr,
                filters,
                processor_cls,
                layout.state_dir if validation.use_processed_hashes(payload) else None,
            )
        if debug_support.cancel_requested(session_root):
            return _cancelled(session_root, "Debuglauf abgebrochen")
        outputs = debug_support.collect_outputs(session_root, output_root)
        final = {"status": "ok", "summary": result, "outputs": outputs}
        debug_support.write_snapshot(session_root, status="ok", detail=result, processed=total, total=total, counters=_counters(outputs))
        debug_support.append_log(session_root, f"[RUN] {result}")
        return debug_support.write_result(session_root, final)
    finally:
        plugin_mgr.kill_all()


def _run_single(payload, session_root, output_root, config, plugin_mgr, processor_cls) -> str:
    source_path = validation.require_source_path(payload, enforce_input_root=False)
    logical_source_path = validation.normalize_logical_source_path(payload.get("logical_source_path")) or source_path.name
    raw_output_path, page_assets_dir = _single_output_targets(output_root, logical_source_path)
    debug_support.write_snapshot(session_root, status="running", detail=source_path.name, processed=0, total=1)
    processor = processor_cls(config, plugin_mgr)
    _run_with_cancel_watch(
        session_root,
        processor,
        lambda: processor.process_single(
            source_path,
            write_output=True,
            raw_output_path=raw_output_path,
            page_assets_dir=page_assets_dir,
            logical_source_path=logical_source_path,
        ),
    )
    return "1 Datei verarbeitet"


def _single_output_targets(output_root: Path, logical_source_path: str) -> tuple[Path, Path]:
    logical_path = Path(logical_source_path)
    relative_parent = logical_path.parent if str(logical_path.parent) != "." else Path()
    stem = logical_path.with_suffix("").name or "sample"
    raw_dir = output_root / "raw_extracts" / relative_parent
    page_assets_parent = output_root / "page_assets" / relative_parent
    raw_name = processor_policy.budget_output_name(raw_dir, f"{stem}.raw.json")
    asset_name = processor_policy.budget_output_name(
        page_assets_parent,
        stem,
        reserved=_PAGE_ASSET_CHILD_RESERVED,
    )
    return raw_dir / raw_name, page_assets_parent / asset_name


def _run_batch(payload, input_root, session_root, output_root, config, plugin_mgr, filters, processor_cls, state_dir):
    catalog = InputCatalog(input_root, state_dir=state_dir, output_dir=output_root)
    if not catalog.refresh():
        raise FileNotFoundError(f"Input-Ordner nicht gefunden: {input_root}")
    total = catalog.count_after_filter(filters)
    debug_support.write_snapshot(session_root, status="running", detail="Batch gestartet", processed=0, total=total)
    processor = processor_cls(
        config,
        plugin_mgr,
        catalog,
        filters,
        output_root,
        callback=lambda report: _on_report(session_root, report, total),
    )
    report = _run_with_cancel_watch(session_root, processor, processor.process)
    return f"{report.successful} Dateien verarbeitet", total


def _run_with_cancel_watch(session_root: Path, processor, operation):
    stop_event = threading.Event()
    watcher = threading.Thread(target=_watch_cancel, args=(stop_event, session_root, processor), daemon=True)
    watcher.start()
    try:
        return operation()
    finally:
        stop_event.set()
        watcher.join(timeout=1)


def _watch_cancel(stop_event: threading.Event, session_root: Path, processor) -> None:
    while not stop_event.wait(0.2):
        if debug_support.cancel_requested(session_root):
            debug_support.append_log(session_root, "[CANCEL] cancel.request erkannt")
            processor.cancel()
            return


def _on_report(session_root: Path, report, total: int) -> None:
    atomic = debug_support.report_snapshot(report, total=total)
    debug_support.write_snapshot(
        session_root,
        status=str(atomic["status"]),
        detail=str(atomic["detail"]),
        processed=int(atomic["processed"]),
        total=int(atomic["total"]),
        counters=dict(atomic["counters"]),
    )


def _cancelled(session_root: Path, summary: str) -> dict:
    debug_support.write_snapshot(session_root, status="cancelled", detail=summary)
    debug_support.append_log(session_root, f"[CANCELLED] {summary}")
    return debug_support.write_result(session_root, {"status": "cancelled", "summary": summary})


def _counters(outputs: dict[str, list[str]]) -> dict[str, int]:
    return {
        "raw_extracts_written": len(outputs.get("raw_extracts", [])),
        "page_images_written": len(outputs.get("page_images", [])),
    }


def _layout(root: Path, app_home: Path | None):
    from ..paths import ensure_app_layout

    return ensure_app_layout(module_root_path=root, app_home_path=app_home)
