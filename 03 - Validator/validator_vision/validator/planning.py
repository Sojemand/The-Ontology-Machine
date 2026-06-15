"""Planning helpers for exact validator report targets."""
from __future__ import annotations

from pathlib import Path

from ..models.types import StructuredDocument
from ..models.profiles import FILE_PROFILE, TABLE_PROFILE, require_supported_profile
from ..models.report_io import report_name
from . import adapter
from .raw_index import build_raw_index, resolve_raw_path
from .targets import ValidationTarget


def build_validation_target(
    structured_path: Path | str,
    report_path: Path | str,
    *,
    raw_path: Path | str | None = None,
    raw_root: Path | str | None = None,
    document: StructuredDocument | None = None,
) -> ValidationTarget:
    structured_file = adapter.normalize_path(structured_path)
    target_file = adapter.normalize_path(report_path)
    if document is None:
        document = adapter.load_structured_document(structured_file)
    profile = require_supported_profile(document.interpreter_profile)
    resolved_raw_path = None
    if profile in {FILE_PROFILE, TABLE_PROFILE} and (raw_path is not None or raw_root is not None):
        resolved_raw_path = resolve_raw_path(document, raw_path=raw_path, raw_root=raw_root)
    elif raw_path is not None:
        resolved_raw_path = adapter.normalize_path(raw_path)
    return ValidationTarget(
        structured_path=structured_file,
        report_path=target_file,
        raw_path=resolved_raw_path,
        document=document,
    )


def plan_batch_targets(
    structured_dir: Path | str,
    report_root: Path | str,
    *,
    raw_root: Path | str | None = None,
) -> list[ValidationTarget]:
    structured_root = adapter.normalize_path(structured_dir)
    target_root = adapter.normalize_path(report_root)
    raw_index = None
    targets: list[ValidationTarget] = []
    for structured_path in adapter.discover_structured_documents(structured_root):
        document = adapter.load_structured_document(structured_path)
        profile = require_supported_profile(document.interpreter_profile)
        relative_parent = structured_path.parent.relative_to(structured_root)
        resolved_raw_path = None
        if profile in {FILE_PROFILE, TABLE_PROFILE} and raw_root is not None:
            if raw_index is None:
                raw_index = build_raw_index(raw_root)
            resolved_raw_path = resolve_raw_path(document, raw_root=raw_root, raw_index=raw_index)
        targets.append(
            ValidationTarget(
                structured_path=structured_path,
                report_path=target_root / relative_parent / report_name(structured_path, profile),
                raw_path=resolved_raw_path,
                document=document,
            )
        )
    return targets


__all__ = ["build_validation_target", "plan_batch_targets"]
