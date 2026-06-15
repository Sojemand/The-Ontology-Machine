"""Session-artifact helpers for validator debug runs."""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from ..models.report_io import atomic_json_write


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
            "stage": "Validator",
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


def report_root(output_root: Path) -> Path:
    return Path(output_root) / "validation_reports"


def config_snapshot_path(output_root: Path) -> Path:
    return Path(output_root) / "config_snapshot.json"


def report_index_path(output_root: Path) -> Path:
    return Path(output_root) / "report_index.json"


def write_config_snapshot(output_root: Path, config) -> Path:
    path = config_snapshot_path(output_root)
    atomic_json_write(path, asdict(config))
    return path


def write_report_index(output_root: Path, session_root: Path, reports: list[tuple[Path, object]]) -> Path:
    path = report_index_path(output_root)
    atomic_json_write(
        path,
        {
            "reports": [
                {
                    "path": relative_path(session_root, report_path),
                    "file_name": report.file_name,
                    "result": report.result,
                    "needs_review": bool(report.needs_review),
                    "summary": {
                        "total_issues": int(report.summary.total_issues),
                        "fail_count": int(report.summary.fail_count),
                        "warn_count": int(report.summary.warn_count),
                    },
                }
                for report_path, report in reports
            ]
        },
    )
    return path


def collect_outputs(
    session_root: Path,
    output_root: Path,
    *,
    report_paths: list[Path] | None = None,
) -> dict[str, list[str]]:
    validation_reports = (
        [relative_path(session_root, path) for path in report_paths if path.exists()]
        if report_paths is not None
        else _relative_matches(session_root, report_root(output_root), "*_validation_report.json")
    )
    outputs: dict[str, list[str]] = {
        "validation_reports": validation_reports,
    }
    config_path = config_snapshot_path(output_root)
    if config_path.exists():
        outputs["config_snapshot"] = [relative_path(session_root, config_path)]
    index_path = report_index_path(output_root)
    if index_path.exists():
        outputs["report_index"] = [relative_path(session_root, index_path)]
    return outputs


def counters_from_reports(reports: list) -> dict[str, int]:
    return {
        "reports_total": len(reports),
        "pass_count": sum(1 for report in reports if report.result == "PASS"),
        "warn_count": sum(1 for report in reports if report.result == "WARN"),
        "fail_count": sum(1 for report in reports if report.result == "FAIL"),
    }


def summary_text(reports: list) -> str:
    counters = counters_from_reports(reports)
    return (
        f"{counters['reports_total']} Reports: "
        f"{counters['pass_count']} PASS  "
        f"{counters['warn_count']} WARN  "
        f"{counters['fail_count']} FAIL"
    )


def relative_path(session_root: Path, path: Path) -> str:
    return path.relative_to(session_root).as_posix()


def _relative_matches(session_root: Path, root: Path, pattern: str) -> list[str]:
    if not root.exists():
        return []
    return [
        relative_path(session_root, path)
        for path in sorted(root.rglob(pattern))
        if path.is_file()
    ]
