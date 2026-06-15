"""Session artifact helpers for normalizer debug runs."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from ..models.results import NormalizationResult
from ..models.serialization import atomic_json_write


def append_log(session_root: Path, line: str) -> None:
    log_path = Path(session_root) / "run.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(f"{line.rstrip()}\n")


def cancel_requested(session_root: Path) -> bool:
    return (Path(session_root) / "cancel.request").exists()


def relative_path(session_root: Path, path: Path) -> str:
    try:
        return path.relative_to(session_root).as_posix()
    except ValueError:
        return str(path)


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
            "stage": "Normalizer",
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


def collect_outputs(session_root: Path, output_root: Path) -> dict[str, list[str]]:
    return {
        "normalized_outputs": [
            relative_path(session_root, path)
            for path in sorted(Path(output_root).rglob("*.structured.normalized.json"))
            if path.is_file()
        ]
    }


def counters_from_results(results: list[NormalizationResult]) -> dict[str, int]:
    return {
        "documents_total": len(results),
        "ok_count": sum(1 for result in results if result.status == "OK"),
        "error_count": sum(1 for result in results if result.status == "ERROR"),
        "needs_review_count": sum(1 for result in results if result.needs_review),
    }


def summary_text(results: list[NormalizationResult]) -> str:
    counters = counters_from_results(results)
    return (
        f"{counters['documents_total']} Dokumente: "
        f"{counters['ok_count']} OK  "
        f"{counters['error_count']} ERROR  "
        f"{counters['needs_review_count']} Needs Review"
    )
