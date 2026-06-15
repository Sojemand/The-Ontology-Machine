"""Row rules for structured/free-text checks."""
from __future__ import annotations

import math

from ...models.config import MatchConfig
from ...models.results import CheckResult, Issue
from ...models.types import StructuredDocument, StructuredRow
from .free_text_policy import matches_free_text
from .validation import is_checkable_value, status_for_issues

_SEMANTIC_ROW_ANCHOR_KEYS = ("question", "text", "content", "value", "summary")
_ROW_METADATA_KEYS = {"page", "sequence", "confidence"}


def _row_anchor_keys(cfg: MatchConfig) -> tuple[str, ...]:
    keys = list(cfg.row_anchor_keys)
    for key in _SEMANTIC_ROW_ANCHOR_KEYS:
        if key not in keys:
            keys.append(key)
    return tuple(keys)


def _anchor_value(row: StructuredRow, cfg: MatchConfig) -> tuple[str, object] | None:
    for anchor_key in _row_anchor_keys(cfg):
        anchor_value = row.values.get(anchor_key)
        if is_checkable_value(anchor_value, cfg):
            return anchor_key, anchor_value
    return None


def check_rows(document: StructuredDocument, cfg: MatchConfig) -> CheckResult:
    issues: list[Issue] = []
    checked = 0
    valid = 0

    for row in document.rows:
        anchor = _anchor_value(row, cfg)
        if anchor is not None:
            anchor_key, anchor_value = anchor
            checked += 1
            if matches_free_text(anchor_value, document.free_text, cfg):
                valid += 1
            else:
                issues.append(
                    Issue(
                        check="rows",
                        level=cfg.row_level,
                        field=f"content.rows[{row.index}].{anchor_key}",
                        extracted_value=anchor_value,
                        raw_value=None,
                        source_ref=None,
                        message="Zeilenanker konnte im content.free_text nicht gefunden werden.",
                    )
                )

        for key, value in row.values.items():
            if (
                key in cfg.skip_row_fields
                or key in _ROW_METADATA_KEYS
                or str(key).startswith("_")
                or key in _row_anchor_keys(cfg)
            ):
                continue
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                continue
            if not math.isfinite(float(value)):
                continue
            checked += 1
            if matches_free_text(value, document.free_text, cfg):
                valid += 1
                continue
            issues.append(
                Issue(
                    check="rows",
                    level=cfg.row_level,
                    field=f"content.rows[{row.index}].{key}",
                    extracted_value=value,
                    raw_value=None,
                    source_ref=None,
                    message="Zeilenwert konnte im content.free_text nicht gefunden werden.",
                )
            )

    return CheckResult(
        name="rows",
        status=status_for_issues(issues),
        issues=issues,
        checked=checked,
        valid=valid,
    )


__all__ = ["check_rows"]
