"""Generic artifact indexing and preview helpers for the debug host."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from ..debug_host.polling import resolve_output_path

_TEXT_EXTENSIONS = {".db", ".json", ".log", ".txt", ".md"}


@dataclass(frozen=True)
class ArtifactEntry:
    label: str
    path: Path
    source: str
    summary: str = ""
    result: str = ""


def collect_entries(session, import_path: str) -> list[ArtifactEntry]:
    seen: set[Path] = set()
    entries: list[ArtifactEntry] = []
    for entry in session_entries(session):
        if entry.path not in seen:
            seen.add(entry.path)
            entries.append(entry)
    for entry in import_entries(import_path):
        if entry.path not in seen:
            seen.add(entry.path)
            entries.append(entry)
    return entries


def session_entries(session) -> list[ArtifactEntry]:
    return _session_entries(session)


def import_entries(import_path: str) -> list[ArtifactEntry]:
    return _import_entries(import_path)


def preview_text(entry: ArtifactEntry | None) -> str:
    if entry is None:
        return ""
    if entry.path.suffix.lower() == ".db":
        return (
            "SQLite database artifact.\n"
            "Inline preview is not available.\n"
            "Use Open Artifacts or an external SQLite viewer.\n\n"
            f"{entry.path}"
        )
    try:
        if entry.path.suffix.lower() == ".json":
            payload = json.loads(entry.path.read_text(encoding="utf-8"))
            return json.dumps(payload, indent=2, ensure_ascii=False)
        return entry.path.read_text(encoding="utf-8")
    except Exception as exc:
        return f"{entry.path}\n\nCould not load artifact: {exc}"


def summary_text(entries: list[ArtifactEntry]) -> str:
    if not entries:
        return ""
    pass_count = sum(1 for entry in entries if entry.result == "PASS")
    warn_count = sum(1 for entry in entries if entry.result == "WARN")
    fail_count = sum(1 for entry in entries if entry.result == "FAIL")
    if pass_count or warn_count or fail_count:
        return (
            f"{len(entries)} artifacts: "
            f"{pass_count} PASS  {warn_count} WARN  {fail_count} FAIL"
        )
    return f"{len(entries)} artifacts loaded"


def _session_entries(session) -> list[ArtifactEntry]:
    if session is None:
        return []
    entries: list[ArtifactEntry] = []
    seen: set[Path] = set()
    files = [
        getattr(session, "request_path", None),
        getattr(session, "response_path", None),
        getattr(session, "snapshot_path", None),
        getattr(session, "result_path", None),
        getattr(session, "run_log_path", None),
    ]
    for path in files:
        if path is None or not path.exists() or not path.is_file() or path in seen:
            continue
        seen.add(path)
        entries.append(_entry_for(path, source="session"))
    result = getattr(session, "result", None)
    if result is not None:
        for mapping_name in ("artifacts", "outputs"):
            mapping = getattr(result, mapping_name, {}) or {}
            for group, values in sorted(mapping.items()):
                for value in values:
                    path = resolve_output_path(session.session_root, str(value))
                    if not path.exists() or not path.is_file() or path in seen:
                        continue
                    seen.add(path)
                    entries.append(_entry_for(path, source=group))
    output_root = getattr(session, "output_root", None)
    if output_root is None or not output_root.exists():
        return entries
    for path in sorted(output_root.rglob("*")):
        if not path.is_file() or path in seen:
            continue
        seen.add(path)
        entries.append(_entry_for(path, source="output_tree"))
    return entries


def _import_entries(import_path: str) -> list[ArtifactEntry]:
    root_text = str(import_path or "").strip()
    if not root_text:
        return []
    root = Path(root_text)
    if not root.exists():
        return []
    if root.is_file():
        return [_entry_for(root, source="import")]
    entries: list[ArtifactEntry] = []
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.suffix.lower() in _TEXT_EXTENSIONS:
            entries.append(_entry_for(path, source="import"))
    return entries


def _entry_for(path: Path, *, source: str) -> ArtifactEntry:
    label = path.name
    summary = str(path)
    result = ""
    if path.suffix.lower() == ".json":
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            payload = None
        if isinstance(payload, dict):
            result = str(payload.get("result", "")).strip().upper()
            file_name = str(payload.get("file_name", "")).strip()
            issue_total = _issue_total(payload)
            if result and file_name:
                label = f"{result:4s}  {file_name}"
            if issue_total is not None and result:
                summary = f"{path} | issues={issue_total}"
    return ArtifactEntry(label=label, path=path, source=source, summary=summary, result=result)


def _issue_total(payload: dict) -> int | None:
    summary = payload.get("summary")
    if not isinstance(summary, dict):
        return None
    value = summary.get("total_issues")
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
