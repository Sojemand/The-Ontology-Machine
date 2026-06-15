"""Hard invariants for the Office export workflow."""
from __future__ import annotations

import sys
from pathlib import Path

from .types import OfficeExportStageError, OfficeExportWorkspace


def validate_source(source_path: str | Path) -> Path:
    source = Path(source_path)
    suffix = source.suffix.lower() or "<ohne Endung>"
    if suffix not in _surface_module().OFFICE_EXTS:
        raise ValueError(f"validation.source: Office-Export nicht unterstuetzt fuer {suffix}")
    if not source.is_file():
        raise FileNotFoundError(f"validation.source: Quelldatei fehlt: {source}")
    return source


def ensure_exported_pdf(workspace: OfficeExportWorkspace, detail: str) -> None:
    if workspace.exported_pdf.exists():
        return
    raise OfficeExportStageError(
        "workflow.verify_pdf",
        f"LibreOffice erzeugte keine PDF-Datei fuer {workspace.source.name}: {detail[:300]}",
    )


def _surface_module():
    return sys.modules[__package__]
