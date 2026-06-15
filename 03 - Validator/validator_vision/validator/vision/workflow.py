"""Vision-profile validation workflow rules."""
from __future__ import annotations

from ...models.config import ValidatorConfig
from ...models.results import CheckResult
from ...models.types import StructuredDocument
from .row_rules import check_rows
from .scalar_rules import check_content_fields, check_context_scalars
from .validation import check_free_text_presence


def run_vision_checks(
    document: StructuredDocument,
    config: ValidatorConfig,
) -> list[CheckResult]:
    check_results: list[CheckResult] = []
    if config.checks.free_text:
        check_results.append(check_free_text_presence(document, config.match))

    if not document.free_text.is_present:
        return check_results

    if config.checks.context_scalars:
        check_results.append(check_context_scalars(document, config.match))
    if config.checks.content_fields:
        check_results.append(check_content_fields(document, config.match))
    if config.checks.rows:
        check_results.append(check_rows(document, config.match))
    return check_results


__all__ = ["run_vision_checks"]
