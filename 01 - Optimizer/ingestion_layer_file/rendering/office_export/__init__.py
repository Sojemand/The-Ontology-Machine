"""Stable surface for Office document export.

surface -> workflow -> validation/adapter -> types
"""
from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Iterable

from . import adapter
from .types import OFFICE_EXTS, OfficeExportStageError
from .workflow import export_office_document_to_pdf

__all__ = [
    "OFFICE_EXTS",
    "OfficeExportStageError",
    "_bundled_soffice_exe",
    "_host_soffice_candidates",
    "_resolve_soffice_exe",
    "_soffice_subprocess_kwargs",
    "export_office_document_to_pdf",
]


def _resolve_soffice_exe() -> tuple[Path, str]:
    runtime = adapter.resolve_soffice_exe()
    return runtime.soffice, runtime.source


def _bundled_soffice_exe() -> Path:
    return adapter.bundled_soffice_exe()


def _host_soffice_candidates() -> Iterable[Path]:
    return adapter.host_soffice_candidates()


def _soffice_subprocess_kwargs(process_api=None) -> dict[str, object]:
    return adapter.soffice_subprocess_kwargs(process_api)
