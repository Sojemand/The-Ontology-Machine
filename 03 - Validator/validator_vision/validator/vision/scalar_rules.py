"""Scalar field rules for structured/free-text checks."""
from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from ...models.config import MatchConfig
from ...models.results import CheckResult, Issue
from ...models.types import PreparedFreeText, StructuredDocument
from .free_text_policy import matches_free_text
from .validation import is_checkable_value, status_for_issues


def _check_scalar_targets(
    *,
    check_name: str,
    level: str,
    free_text: PreparedFreeText,
    targets: Iterable[tuple[str, Any, str]],
    cfg: MatchConfig,
) -> CheckResult:
    issues: list[Issue] = []
    checked = 0
    valid = 0
    for field_path, value, message in targets:
        checked += 1
        if matches_free_text(value, free_text, cfg):
            valid += 1
            continue
        issues.append(
            Issue(
                check=check_name,
                level=level,
                field=field_path,
                extracted_value=value,
                raw_value=None,
                source_ref=None,
                message=message,
            )
        )
    return CheckResult(
        name=check_name,
        status=status_for_issues(issues),
        issues=issues,
        checked=checked,
        valid=valid,
    )


def _context_targets(document: StructuredDocument, cfg: MatchConfig) -> Iterable[tuple[str, Any, str]]:
    for field_name in cfg.context_fields:
        if field_name not in document.context:
            continue
        value = document.context.get(field_name)
        if not is_checkable_value(value, cfg):
            continue
        yield (
            f"context.{field_name}",
            value,
            f"Wert fuer context.{field_name} konnte im content.free_text nicht gefunden werden.",
        )


def _content_field_targets(document: StructuredDocument, cfg: MatchConfig) -> Iterable[tuple[str, Any, str]]:
    for field_name, value in document.fields.items():
        if field_name in cfg.skip_content_fields or str(field_name).startswith("_"):
            continue
        if not is_checkable_value(value, cfg):
            continue
        yield (
            f"content.fields.{field_name}",
            value,
            f"Wert fuer content.fields.{field_name} konnte im content.free_text nicht gefunden werden.",
        )


def check_context_scalars(document: StructuredDocument, cfg: MatchConfig) -> CheckResult:
    return _check_scalar_targets(
        check_name="context_scalars",
        level=cfg.scalar_level,
        free_text=document.free_text,
        targets=_context_targets(document, cfg),
        cfg=cfg,
    )


def check_content_fields(document: StructuredDocument, cfg: MatchConfig) -> CheckResult:
    return _check_scalar_targets(
        check_name="content_fields",
        level=cfg.scalar_level,
        free_text=document.free_text,
        targets=_content_field_targets(document, cfg),
        cfg=cfg,
    )


__all__ = ["check_content_fields", "check_context_scalars"]
