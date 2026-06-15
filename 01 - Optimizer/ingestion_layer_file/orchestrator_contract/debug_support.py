"""Session artifact helpers for headless debug contract actions."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from ..models import IngestionReport, atomic_json_write


def append_log(session_root: Path, line: str) -> None:
    log_path = Path(session_root) / "run.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(f"{line.rstrip()}\n")


def cancel_requested(session_root: Path) -> bool:
    return (Path(session_root) / "cancel.request").exists()


def write_snapshot(
    session_root: Path,
    *,
    status: str,
    detail: str,
    processed: int = 0,
    total: int = 0,
    counters: dict[str, int] | None = None,
) -> None:
    atomic_json_write(
        Path(session_root) / "snapshot.json",
        {
            "status": status,
            "stage": "Optimizer",
            "detail": detail,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "processed": int(processed),
            "total": int(total),
            "counters": dict(counters or {}),
        },
    )


def write_result(session_root: Path, payload: dict) -> dict:
    atomic_json_write(Path(session_root) / "result.json", payload)
    return payload


def filtered_summary(entries) -> dict[str, int]:
    summary: dict[str, int] = {}
    for entry in entries:
        key = entry.extension.lstrip(".") or "unknown"
        summary[key] = summary.get(key, 0) + 1
    return summary


def catalog_entries(entries, *, limit: int = 100) -> list[dict[str, object]]:
    return [
        {
            "relative_path": entry.relative_path,
            "filename": entry.filename,
            "extension": entry.extension,
            "size_bytes": entry.size_bytes,
            "content_hash": entry.content_hash,
        }
        for entry in list(entries)[:limit]
    ]


def report_snapshot(report: IngestionReport, *, total: int) -> dict[str, object]:
    return {
        "status": "running",
        "stage": "Optimizer",
        "detail": report.current_file or "running",
        "processed": int(report.total_files_processed),
        "total": int(total),
        "counters": {
            "raw_extracts_written": int(report.total_extracts_written),
            "page_assets_written": int(report.total_images_rendered),
        },
    }


def collect_outputs(session_root: Path, output_root: Path) -> dict[str, list[str]]:
    return {
        "raw_extracts": _relative_matches(session_root, output_root / "raw_extracts", "*.raw.json"),
        "page_assets": _relative_matches(session_root, output_root / "page_assets", "*.*"),
    }


def _relative_matches(session_root: Path, root: Path, pattern: str) -> list[str]:
    if not root.exists():
        return []
    return [str(path.relative_to(session_root)).replace("\\", "/") for path in sorted(root.rglob(pattern)) if path.is_file()]
