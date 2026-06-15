"""Windows path-budget helpers for runtime staging and bundle artifacts."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

WINDOWS_PATH_BUDGET = 259

_INVALID_FILENAME_CHARS_RE = re.compile(r'[<>:"/\\|?*\x00-\x1F]+')
_PAGE_STAGE_TAIL_RE = re.compile(r"^(?P<stem>.+?)(?P<tail>\.p\d{3}\.of\d{3})$")
_KNOWN_SUFFIXES = (
    ".error_manifest.json",
    ".run.log",
    ".structured.normalized.json",
    ".vision_validation_report.json",
    ".files_validation_report.json",
    ".structured.json",
    ".raw.json",
    ".json",
)


def runtime_doc_dir(runtime_root: Path, content_hash: str) -> Path:
    return runtime_root / f"d.{hash8(content_hash)}"


def bundle_member_name(bundle_path: Path, prefix: str, source: Path, *, index: int | None = None) -> str:
    preferred = _preferred_name(prefix, source, index=index)
    if _path_length(bundle_path, preferred) <= WINDOWS_PATH_BUDGET:
        return preferred
    safe_name = safe_file_name(source.name)
    stem, suffixes = split_name_suffixes(safe_name)
    lead = _bundle_name_lead(prefix, index=index)
    digest = _short_name_hash(safe_name)
    truncated = stem or "document"
    candidate = f"{lead}{truncated}.{digest}{suffixes}"
    while _path_length(bundle_path, candidate) > WINDOWS_PATH_BUDGET and len(truncated) > 1:
        truncated = truncated[:-1]
        candidate = f"{lead}{truncated}.{digest}{suffixes}"
    return candidate


def budgeted_name(parent: Path, preferred_name: str, *, reserved: int = 0) -> str:
    budget = max(WINDOWS_PATH_BUDGET - max(reserved, 0), 32)
    if _path_length(parent, preferred_name) <= budget:
        return preferred_name
    safe_name = safe_file_name(preferred_name)
    stem, suffixes = split_name_suffixes(safe_name)
    digest = _short_name_hash(safe_name)
    truncated = stem or "document"
    candidate = f"{truncated}.{digest}{suffixes}"
    while _path_length(parent, candidate) > budget and len(truncated) > 1:
        truncated = truncated[:-1]
        candidate = f"{truncated}.{digest}{suffixes}"
    return candidate


def budgeted_name_with_tail(
    parent: Path,
    preferred_stem: str,
    tail: str,
    suffix: str,
    *,
    reserved: int = 0,
) -> str:
    budget = max(WINDOWS_PATH_BUDGET - max(reserved, 0), 32)
    safe_stem = safe_file_name(preferred_stem) or "document"
    safe_tail = str(tail or "").strip()
    safe_suffix = str(suffix or "").strip()
    preferred_name = f"{safe_stem}{safe_tail}{safe_suffix}"
    if _path_length(parent, preferred_name) <= budget:
        return preferred_name
    digest = _short_name_hash(preferred_name)
    truncated = safe_stem
    candidate = f"{truncated}.{digest}{safe_tail}{safe_suffix}"
    while _path_length(parent, candidate) > budget and len(truncated) > 1:
        truncated = truncated[:-1]
        candidate = f"{truncated}.{digest}{safe_tail}{safe_suffix}"
    return candidate


def budgeted_page_name(parent: Path, slug: str, *, suffix: str = "", reserved: int = 0) -> str:
    raw_slug = str(slug or "").strip() or "document"
    match = _PAGE_STAGE_TAIL_RE.match(raw_slug)
    if match is None:
        return budgeted_name(parent, f"{raw_slug}{suffix}", reserved=reserved)
    stem = match.group("stem") or "document"
    tail = match.group("tail") or ""
    return budgeted_name_with_tail(parent, stem, tail, suffix, reserved=reserved)


def budgeted_stage_name(parent: Path, preferred_name: str, *, reserved: int = 0) -> str:
    safe_name = safe_file_name(preferred_name)
    stem, suffixes = split_name_suffixes(safe_name)
    if _PAGE_STAGE_TAIL_RE.match(stem):
        return budgeted_page_name(parent, stem, suffix=suffixes, reserved=reserved)
    return budgeted_name(parent, safe_name, reserved=reserved)


def budgeted_relative_path(root: Path, relative_path: Path, *, reserved: int = 0) -> Path:
    current = root
    raw_parts = list(Path(relative_path).parts)
    parts: list[str] = []
    for index, raw_part in enumerate(raw_parts):
        safe_part = safe_file_name(raw_part)
        part_reserved = reserved if index == len(raw_parts) - 1 else 0
        part = budgeted_name(current, safe_part, reserved=part_reserved)
        parts.append(part)
        current = current / part
    return Path(*parts) if parts else Path()


def safe_file_name(raw_value: str) -> str:
    candidate = _INVALID_FILENAME_CHARS_RE.sub("_", str(raw_value or "").strip()).strip(" .")
    return candidate or "document"


def split_name_suffixes(name: str) -> tuple[str, str]:
    lower_name = name.lower()
    for suffix in _KNOWN_SUFFIXES:
        if lower_name.endswith(suffix):
            return name[: -len(suffix)] or "document", name[-len(suffix) :]
    path = Path(name)
    if path.suffix:
        return path.stem or "document", path.suffix
    return name or "document", ""


def hash8(content_hash: str) -> str:
    cleaned = str(content_hash or "").replace("sha256:", "").strip()
    return (cleaned or "document")[:8]


def _preferred_name(prefix: str, source: Path, *, index: int | None) -> str:
    lead = _bundle_name_lead(prefix, index=index)
    return f"{lead}{safe_file_name(source.name)}"


def _bundle_name_lead(prefix: str, *, index: int | None) -> str:
    return f"{prefix}__" if index is None else f"{prefix}__{index:02d}__"


def _path_length(parent: Path, name: str) -> int:
    return len(str(parent / name))


def _short_name_hash(name: str) -> str:
    return hashlib.sha1(name.encode("utf-8")).hexdigest()[:8]
