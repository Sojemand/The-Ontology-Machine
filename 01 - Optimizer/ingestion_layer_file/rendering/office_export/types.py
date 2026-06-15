"""Typed contracts for the Office export workflow."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

OFFICE_EXTS = {".doc", ".docx", ".odt", ".rtf"}


@dataclass(frozen=True)
class OfficeRuntimeResolution:
    soffice: Path
    source: str


@dataclass(frozen=True)
class OfficeExportWorkspace:
    source: Path
    work_dir: Path
    profile_dir: Path
    target_pdf: Path
    staged_source: Path

    @property
    def exported_pdf(self) -> Path:
        return self.work_dir / f"{self.staged_source.stem}.pdf"

    @property
    def profile_url(self) -> str:
        return self.profile_dir.as_uri()


class OfficeExportStageError(RuntimeError):
    """Stage-labelled Office export failure."""

    def __init__(self, stage: str, detail: str) -> None:
        self.stage = stage
        self.detail = detail.strip() or "unknown error"
        super().__init__(f"{stage}: {self.detail}")
