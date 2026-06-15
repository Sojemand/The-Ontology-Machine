"""Runtime and filesystem adapters for Office export."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Iterable

from ...paths import resolve_layout
from .types import OfficeExportWorkspace, OfficeRuntimeResolution


def create_workspace(source: Path) -> OfficeExportWorkspace:
    temp_api = _surface_module().tempfile
    work_dir = Path(temp_api.mkdtemp(prefix="file-optimizer-office-"))
    profile_dir = Path(temp_api.mkdtemp(prefix="file-optimizer-lo-profile-"))
    target_handle = temp_api.NamedTemporaryFile(
        prefix="file-optimizer-office-",
        suffix=".pdf",
        delete=False,
    )
    target_handle.close()
    return OfficeExportWorkspace(
        source=source,
        work_dir=work_dir,
        profile_dir=profile_dir,
        target_pdf=Path(target_handle.name),
        staged_source=work_dir / source.name,
    )


def stage_source(workspace: OfficeExportWorkspace) -> None:
    _surface_module().shutil.copy2(workspace.source, workspace.staged_source)


def run_soffice_export(
    runtime: OfficeRuntimeResolution,
    workspace: OfficeExportWorkspace,
    *,
    timeout: int = 120,
) -> subprocess.CompletedProcess[str]:
    return _surface_module().subprocess.run(
        [
            str(runtime.soffice),
            "--headless",
            "--nologo",
            "--nolockcheck",
            "--nodefault",
            "--norestore",
            f"-env:UserInstallation={workspace.profile_url}",
            "--convert-to",
            "pdf",
            "--outdir",
            str(workspace.work_dir),
            str(workspace.staged_source),
        ],
        capture_output=True,
        timeout=timeout,
        check=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        **soffice_subprocess_kwargs(),
    )


def publish_exported_pdf(workspace: OfficeExportWorkspace) -> Path:
    _surface_module().shutil.copy2(workspace.exported_pdf, workspace.target_pdf)
    return workspace.target_pdf


def cleanup_workspace(workspace: OfficeExportWorkspace) -> None:
    _surface_module().shutil.rmtree(workspace.work_dir, ignore_errors=True)
    _surface_module().shutil.rmtree(workspace.profile_dir, ignore_errors=True)


def resolve_soffice_exe() -> OfficeRuntimeResolution:
    bundled = _surface_module()._bundled_soffice_exe()
    if bundled.exists():
        return OfficeRuntimeResolution(soffice=bundled, source="bundled")
    raise FileNotFoundError(_missing_soffice_message([bundled]))


def bundled_soffice_exe() -> Path:
    return resolve_layout().libreoffice_dir / "program" / "soffice.exe"


def host_soffice_candidates() -> Iterable[Path]:
    return ()


def _missing_soffice_message(paths: list[Path]) -> str:
    unique_paths: list[str] = []
    seen: set[str] = set()
    for path in paths:
        key = str(path).lower()
        if key in seen:
            continue
        seen.add(key)
        unique_paths.append(str(path))
    return (
        "LibreOffice fehlt. Erwartet unter runtime/libreoffice. "
        "Geprueft: " + "; ".join(unique_paths)
    )


def soffice_subprocess_kwargs(process_api=None) -> dict[str, object]:
    if sys.platform != "win32":
        return {}
    api = process_api or _surface_module().subprocess
    kwargs: dict[str, object] = {}
    startupinfo_factory = getattr(api, "STARTUPINFO", None)
    if startupinfo_factory is not None:
        startupinfo = startupinfo_factory()
        startupinfo.dwFlags |= getattr(api, "STARTF_USESHOWWINDOW", 0)
        startupinfo.wShowWindow = getattr(api, "SW_HIDE", 0)
        kwargs["startupinfo"] = startupinfo
    creationflags = getattr(api, "CREATE_NO_WINDOW", 0)
    if creationflags:
        kwargs["creationflags"] = creationflags
    return kwargs


def _surface_module():
    return sys.modules[__package__]
