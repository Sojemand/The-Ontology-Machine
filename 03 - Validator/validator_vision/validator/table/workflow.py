"""Table-profile validation workflow for raw-backed spreadsheet outputs."""
from __future__ import annotations

from pathlib import Path

from ...models.config import ValidatorConfig
from ...models.results import CheckResult
from ...models.types import StructuredDocument
from ..numeric_claims import check_numeric_claims
from ..raw_index import load_raw_payload
from ..vision.validation import check_free_text_presence


def run_table_checks(
    document: StructuredDocument,
    config: ValidatorConfig,
    *,
    raw_path: Path | None,
) -> list[CheckResult]:
    if raw_path is None:
        raise ValueError("Table-Profil benoetigt Raw-Evidence fuer die numerische Validierung.")
    raw_payload = load_raw_payload(raw_path)
    check_results: list[CheckResult] = []
    if config.checks.free_text:
        check_results.append(check_free_text_presence(document, config.match))
    check_results.append(
        check_numeric_claims(
            document,
            raw_payload,
            config.match,
            raw_path=str(raw_path),
        )
    )
    return check_results


__all__ = ["run_table_checks"]
