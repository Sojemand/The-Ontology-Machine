"""File-profile validation workflow for raw-backed numeric claims."""
from __future__ import annotations

from pathlib import Path

from ...models.config import ValidatorConfig
from ...models.results import CheckResult
from ...models.types import StructuredDocument
from ..numeric_claims import check_numeric_claims
from ..raw_index import load_raw_payload


def run_file_checks(
    document: StructuredDocument,
    config: ValidatorConfig,
    *,
    raw_path: Path | None,
) -> list[CheckResult]:
    if raw_path is None:
        raise ValueError("File-Profil benoetigt Raw-Evidence fuer die numerische Validierung.")
    raw_payload = load_raw_payload(raw_path)
    return [
        check_numeric_claims(
            document,
            raw_payload,
            config.match,
            raw_path=str(raw_path),
        )
    ]


__all__ = ["run_file_checks"]
