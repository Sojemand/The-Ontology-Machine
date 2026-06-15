from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class CaseResult:
    id: str
    title: str
    status: str
    message: str
    driver: str


@dataclass(frozen=True)
class SuiteResult:
    name: str
    display_name: str
    status: str
    cases: tuple[CaseResult, ...]


def write_index(
    report_dir: Path,
    *,
    run_id: str,
    mode: str,
    status: str,
    suites: list[SuiteResult],
    started_at: str,
) -> Path:
    payload: dict[str, Any] = {
        "report_schema_version": 1,
        "run_id": run_id,
        "mode": mode,
        "status": status,
        "started_at": started_at,
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "suites": [asdict(suite) for suite in suites],
    }
    target = report_dir / "index.json"
    target.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    write_html_summary(report_dir / "index.html", payload)
    return target


def write_html_summary(path: Path, payload: dict[str, Any]) -> None:
    rows: list[str] = []
    for suite in payload.get("suites", []):
        rows.append(f"<h2>{_escape(suite['display_name'])}</h2>")
        rows.append("<ul>")
        for case in suite.get("cases", []):
            rows.append(
                "<li>"
                f"<strong>{_escape(case['id'])}</strong>: "
                f"{_escape(case['status'])} - {_escape(case['message'])}"
                "</li>"
            )
        rows.append("</ul>")
    html = "\n".join(
        [
            "<!doctype html>",
            "<meta charset=\"utf-8\">",
            "<title>Vision Pipeline Test Dojo Report</title>",
            "<body>",
            f"<h1>Test Dojo { _escape(payload.get('run_id', '')) }</h1>",
            f"<p>Status: {_escape(payload.get('status', 'unknown'))}</p>",
            *rows,
            "</body>",
        ]
    )
    path.write_text(html, encoding="utf-8")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _escape(value: object) -> str:
    import html

    return html.escape(str(value), quote=True)
