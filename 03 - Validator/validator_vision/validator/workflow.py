"""Workflow stage for validator orchestration."""
from __future__ import annotations

import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from ..models.config import ValidatorConfig
from ..models.profiles import FILE_PROFILE, TABLE_PROFILE, require_supported_profile
from ..models.results import ValidationReport
from ..models.types import StructuredDocument
from . import adapter, repository, reporting
from .file.workflow import run_file_checks
from .table.workflow import run_table_checks
from .targets import ValidationTarget
from .vision.workflow import run_vision_checks

VALIDATOR_VERSION = "1.3.1"


class DocumentValidator:
    def __init__(self, config: ValidatorConfig) -> None:
        self.config = config

    def validate(
        self,
        structured_path: Path,
        report_path: Path,
        *,
        raw_path: Path | None = None,
        document: StructuredDocument | None = None,
    ) -> ValidationReport:
        started = time.perf_counter()
        structured_path = adapter.normalize_path(structured_path)
        report_path = adapter.normalize_path(report_path)
        if document is None:
            document = adapter.load_structured_document(structured_path)
        profile = require_supported_profile(document.interpreter_profile)
        if profile == FILE_PROFILE:
            check_results = run_file_checks(document, self.config, raw_path=raw_path)
        elif profile == TABLE_PROFILE:
            check_results = run_table_checks(document, self.config, raw_path=raw_path)
        else:
            check_results = run_vision_checks(document, self.config)
        report = reporting.build_validation_report(
            document=document,
            check_results=check_results,
            config=self.config,
            validator_version=VALIDATOR_VERSION,
            validated_at=datetime.now(timezone.utc).isoformat(),
            processing_time_ms=_processing_time_ms(started),
        )
        repository.write_report(
            report_path=report_path,
            report=report,
        )
        return report

    def validate_batch(
        self,
        targets: Iterable[ValidationTarget],
    ) -> list[ValidationReport]:
        return [
            self.validate(
                target.structured_path,
                target.report_path,
                raw_path=target.raw_path,
                document=target.document,
            )
            for target in targets
        ]


def _processing_time_ms(started: float) -> int:
    return int((time.perf_counter() - started) * 1000)
