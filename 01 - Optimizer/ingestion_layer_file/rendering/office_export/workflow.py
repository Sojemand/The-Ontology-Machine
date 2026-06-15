"""Workflow surface for Office document export."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from . import adapter, validation
from .types import OfficeExportStageError, OfficeRuntimeResolution, OfficeExportWorkspace


def export_office_document_to_pdf(source_path: str | Path) -> str:
    source = validation.validate_source(source_path)
    runtime = _coerce_runtime_resolution(_surface_module()._resolve_soffice_exe())
    workspace = adapter.create_workspace(source)
    try:
        _stage_source(workspace)
        result = _run_export(runtime, workspace)
        detail = (result.stderr or result.stdout or "").strip()
        validation.ensure_exported_pdf(workspace, detail)
        return str(adapter.publish_exported_pdf(workspace))
    finally:
        adapter.cleanup_workspace(workspace)


def _stage_source(workspace: OfficeExportWorkspace) -> None:
    try:
        adapter.stage_source(workspace)
    except Exception as exc:
        raise OfficeExportStageError("adapter.stage_source", str(exc)) from exc


def _run_export(
    runtime: OfficeRuntimeResolution,
    workspace: OfficeExportWorkspace,
) -> subprocess.CompletedProcess[str]:
    try:
        return adapter.run_soffice_export(runtime, workspace)
    except subprocess.TimeoutExpired as exc:
        raise OfficeExportStageError(
            "adapter.export",
            f"LibreOffice-Export Timeout fuer {workspace.source.name} (120s)",
        ) from exc
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or exc.stdout or "").strip()
        raise OfficeExportStageError(
            "adapter.export",
            f"LibreOffice-Export fehlgeschlagen fuer {workspace.source.name}: {detail[:300]}",
        ) from exc


def _coerce_runtime_resolution(runtime: tuple[Path, str] | OfficeRuntimeResolution) -> OfficeRuntimeResolution:
    if isinstance(runtime, OfficeRuntimeResolution):
        return runtime
    soffice, source = runtime
    return OfficeRuntimeResolution(soffice=Path(soffice), source=str(source))


def _surface_module():
    return sys.modules[__package__]
