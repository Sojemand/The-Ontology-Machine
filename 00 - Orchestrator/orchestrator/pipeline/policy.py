"""Soft naming and review policy for the orchestrator pipeline."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any

from .. import policy_store
from . import debug, path_budget
from .policy_reviews import (
    clear_record_review_state,
    mark_record_stage_review,
    normalizer_failure_reason,
    payload_needs_review,
    payload_review_reason,
    record_needs_review,
    refresh_record_review_reason,
    structured_needs_review,
    structured_processing_payload,
    structured_review_reason,
)

_SLUG_RE = re.compile(r"[^A-Za-z0-9._-]+")
_INVALID_FILENAME_CHARS_RE = re.compile(r'[<>:"/\\\\|?*\x00-\x1F]+')
_MAX_PATH_SEGMENT_LENGTH = 96


def publication_name(key: str) -> str:
    return policy_store.publication_name(key)


def request_file_name(key: str = "interpreter_request") -> str:
    return policy_store.request_file_name(key)


def safe_file_name(raw_value: str) -> str:
    text = str(raw_value or "").strip().replace("\\", "/")
    candidate = text.rsplit("/", 1)[-1]
    candidate = _budget_segment(_INVALID_FILENAME_CHARS_RE.sub("_", candidate).strip(" ."))
    if candidate in {"", ".", ".."}:
        return "document"
    return candidate


def safe_relative_path(raw_value: str) -> Path | None:
    text = str(raw_value or "").strip()
    if not text:
        return None
    windows_path = PureWindowsPath(text)
    posix_text = text.replace("\\", "/")
    posix_path = PurePosixPath(posix_text)
    if windows_path.is_absolute() or windows_path.drive or windows_path.root or posix_path.is_absolute():
        return None
    parts: list[str] = []
    for part in posix_text.split("/"):
        normalized = part.strip()
        if not normalized or normalized == ".":
            continue
        if normalized == ".." or ":" in normalized:
            return None
        cleaned = _INVALID_FILENAME_CHARS_RE.sub("_", normalized).strip(" .") or "document"
        parts.append(_budget_segment(cleaned))
    return Path(*parts) if parts else None


def record_relative_output_path(engine: Any, record: Any, *, purpose: str) -> Path:
    relative_path = safe_relative_path(record.relative_path)
    if relative_path is not None:
        return relative_path
    fallback_name = safe_file_name(record.file_name or Path(record.source_path or record.original_source_path).name)
    if str(record.relative_path or "").strip():
        debug.append_log(
            engine,
            f"[SECURITY] {purpose}: Invalid relative path was reduced to file name: {record.relative_path}",
        )
    return Path(fallback_name)


def structured_output_path(engine: Any, record: Any) -> Path:
    relative_path = record_relative_output_path(engine, record, purpose="Structured-Output")
    return relative_path.parent / f"{relative_path.name}.structured.json"


def raw_output_path(engine: Any, record: Any) -> Path:
    relative_path = record_relative_output_path(engine, record, purpose="Raw-Output")
    return relative_path.parent / f"{relative_path.name}.raw.json"


def validation_output_path(engine: Any, record: Any, source_path: Path) -> Path:
    relative_path = record_relative_output_path(engine, record, purpose="Validator-Report")
    suffix = _validation_report_suffix(record, source_path.name)
    return relative_path.parent / f"{relative_path.name}{suffix}"


def planned_validation_output_path(engine: Any, record: Any) -> Path:
    relative_path = record_relative_output_path(engine, record, purpose="Validator-Report")
    return relative_path.parent / f"{relative_path.name}{_validation_report_suffix(record, '')}"


def normalized_output_path(engine: Any, record: Any) -> Path:
    relative_path = record_relative_output_path(engine, record, purpose="Normalizer-Output")
    return relative_path.parent / f"{relative_path.name}.structured.normalized.json"


def interpreter_request_output_path(engine: Any, record: Any) -> Path:
    relative_path = record_relative_output_path(engine, record, purpose="Interpreter-Request")
    return relative_path / request_file_name()


def log_output_path(engine: Any, record: Any) -> Path:
    relative_path = record_relative_output_path(engine, record, purpose="Run-Log")
    return relative_path.parent / f"{relative_path.name}.run.log"


def error_manifest_output_path(engine: Any, record: Any) -> Path:
    relative_path = record_relative_output_path(engine, record, purpose="Error-Manifest")
    return relative_path.parent / f"{relative_path.name}.error_manifest.json"


def error_stage_folder(stage: str) -> str:
    stage_name = str(stage or "").strip()
    return stage_name if stage_name in set(policy_store.pipeline_stage_names()) else "Unbekannt"


def bundle_slug(record: Any) -> str:
    base = record.relative_path or record.file_name or "document"
    safe = _SLUG_RE.sub("_", base.replace("/", "__").replace("\\", "__")).strip("._")
    return (safe or "document")[:80]


def hash8(content_hash: str) -> str:
    return content_hash.replace("sha256:", "")[:8]


def bundle_file_name(prefix: str, source: Path, *, index: int | None = None) -> str:
    safe_name = safe_file_name(source.name)
    if index is None:
        return f"{prefix}__{safe_name}"
    return f"{prefix}__{index:02d}__{safe_name}"


def conflict_target(target_path: Path, *, action: str, content_hash: str) -> Path:
    for candidate in conflict_target_candidates(target_path, action=action, content_hash=content_hash):
        if not candidate.exists():
            return candidate
    raise RuntimeError("unreachable")


def conflict_target_candidates(target_path: Path, *, action: str, content_hash: str):
    stem = target_path.stem
    suffix = target_path.suffix
    action_slug = _SLUG_RE.sub("_", action.strip().lower()).strip("_") or "move"
    base_hash = hash8(content_hash) if content_hash else action_slug
    yield target_path.with_name(f"{stem}__{action_slug}_{base_hash}{suffix}")
    counter = 2
    while True:
        yield target_path.with_name(f"{stem}__{action_slug}_{base_hash}_{counter}{suffix}")
        counter += 1


def _validation_report_suffix(record: Any, source_name: str) -> str:
    name = str(source_name or "").strip()
    if name.endswith(".files_validation_report.json"):
        return ".files_validation_report.json"
    if name.endswith(".vision_validation_report.json"):
        return ".vision_validation_report.json"
    profile = str(getattr(record, "interpreter_profile", "") or "").strip()
    if profile == "file":
        return ".files_validation_report.json"
    return ".vision_validation_report.json"


def _budget_segment(value: str) -> str:
    candidate = str(value or "").strip() or "document"
    if len(candidate) <= _MAX_PATH_SEGMENT_LENGTH:
        return candidate
    stem, suffixes = path_budget.split_name_suffixes(candidate)
    digest = hashlib.sha1(candidate.encode("utf-8")).hexdigest()[:8]
    head_budget = max(_MAX_PATH_SEGMENT_LENGTH - len(suffixes) - len(digest) - 1, 8)
    return f"{stem[:head_budget]}.{digest}{suffixes}"
