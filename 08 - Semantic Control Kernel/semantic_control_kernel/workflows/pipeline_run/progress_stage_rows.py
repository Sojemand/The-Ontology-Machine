from __future__ import annotations

from typing import Any, Mapping

_READY_STAGE_STATUSES = {"bereit", "ready"}
_DONE_STAGE_STATUSES = {"fertig", "done", "completed", "complete"}


def visible_summary(snapshot: Mapping[str, Any]) -> str:
    total = int(snapshot.get("total") or 0)
    completed = int(snapshot.get("completed") or 0)
    success = int(snapshot.get("success") or 0)
    errors = int(snapshot.get("errors") or 0)
    needs_review = int(snapshot.get("needs_review") or 0)
    current_file = str(snapshot.get("current_file") or "").strip()
    current = f"; current {current_file}" if current_file else ""
    error_cases = error_cases_folder(snapshot)
    error_case_text = ""
    if error_cases:
        file_count = int(error_cases.get("file_count") or 0)
        if file_count:
            error_case_text = f"; Error Cases folder has {file_count} source file(s)"
    return (
        f"Ingestion: {completed}/{total} complete; {success} ok; "
        f"{needs_review} review; {errors} errors{error_case_text}{current}"
    )


def state_summary(snapshot: Mapping[str, Any]) -> str:
    active_stage = active_stage_summary(snapshot)
    pending = int(snapshot.get("pending") or 0)
    retries = int(snapshot.get("retries") or 0)
    attempt = int(snapshot.get("current_attempt") or 0)
    parts = [
        f"pending={pending}",
        f"retries={retries}",
        f"attempt={attempt}",
    ]
    if active_stage:
        parts.append(f"stage={active_stage}")
    return "; ".join(parts)


def active_stage_summary(snapshot: Mapping[str, Any]) -> str:
    rows = stage_rows(snapshot)
    completed_rows: list[Mapping[str, Any]] = []
    for row in rows:
        status_key = str(row.get("status") or "").strip().casefold()
        if not status_key or status_key in _READY_STAGE_STATUSES:
            continue
        if status_key in _DONE_STAGE_STATUSES:
            completed_rows.append(row)
            continue
        return format_stage_summary(row)
    if completed_rows:
        return format_stage_summary(completed_rows[-1])
    return ""


def stage_artifact_refs(snapshot: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows = stage_rows(snapshot)
    if not rows:
        return []
    return [
        {
            "schema_version": "kernel.orchestrator_stage_statuses.v1",
            "kind": "orchestrator_stage_statuses",
            "stages": rows,
        }
    ]


def stage_rows(snapshot: Mapping[str, Any]) -> list[dict[str, Any]]:
    stages = snapshot.get("stage_statuses")
    if not isinstance(stages, Mapping):
        return []
    rows: list[dict[str, Any]] = []
    for name, value in stages.items():
        if not isinstance(value, Mapping):
            continue
        rows.append(
            {
                "name": str(name),
                "status": str(value.get("status") or "").strip(),
                "detail": str(value.get("detail") or "").strip(),
                "progress_current": int_value(value.get("progress_current")),
                "progress_total": int_value(value.get("progress_total")),
                "progress_label": str(value.get("progress_label") or "").strip(),
            }
        )
    error_row = error_cases_stage_row(snapshot)
    if error_row:
        rows.append(error_row)
    return rows


def error_cases_stage_row(snapshot: Mapping[str, Any]) -> dict[str, Any] | None:
    error_cases = error_cases_folder(snapshot)
    errors = int_value(snapshot.get("errors"))
    needs_review = int_value(snapshot.get("needs_review"))
    file_count = int_value(error_cases.get("file_count")) if error_cases else 0
    if not any((errors, needs_review, file_count)):
        return None
    latest = error_cases.get("latest_files") if error_cases else []
    latest_files = ", ".join(str(item) for item in latest[:3]) if isinstance(latest, list) else ""
    detail_parts = [
        f"{errors} error(s)" if errors else "",
        f"{needs_review} review" if needs_review else "",
        f"{file_count} source file(s) in folder" if file_count else "",
        latest_files,
    ]
    return {
        "name": "Error Cases",
        "status": "Found" if errors or file_count else "Review",
        "detail": " | ".join(part for part in detail_parts if part),
        "progress_current": file_count or errors,
        "progress_total": 0,
        "progress_label": "",
    }


def error_cases_folder(snapshot: Mapping[str, Any]) -> Mapping[str, Any]:
    value = snapshot.get("error_cases_folder")
    return value if isinstance(value, Mapping) else {}


def format_stage_summary(row: Mapping[str, Any]) -> str:
    status = str(row.get("status") or "").strip()
    progress_current = int(row.get("progress_current") or 0)
    progress_total = int(row.get("progress_total") or 0)
    progress = f" {progress_current}/{progress_total}" if progress_total else ""
    label = str(row.get("progress_label") or row.get("detail") or "").strip()
    detail = f" {label}" if label else ""
    return f"{row.get('name')}: {status}{progress}{detail}".strip()


def int_value(value: object) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0
