"""Office runtime probes split by healthcheck scope."""
from __future__ import annotations

import configparser
import shutil
import subprocess
import tempfile
from pathlib import Path

from ..office_export import _resolve_soffice_exe, _soffice_subprocess_kwargs

PIPELINE_RUN_SCOPE = "pipeline_run"
_VERSION_SECTION = "Version"


def probe_office_runtime(*, scope: str = "", timeout_seconds: int) -> tuple[bool, str]:
    if scope == PIPELINE_RUN_SCOPE:
        return probe_bundled_runtime()
    return probe_live_runtime(timeout_seconds=timeout_seconds)


def probe_bundled_runtime() -> tuple[bool, str]:
    try:
        soffice, _source = _resolve_soffice_exe()
        return True, read_runtime_detail(soffice)
    except Exception as exc:
        return False, f"LibreOffice-Runtimeprobe fehlgeschlagen: {exc}"


def probe_live_runtime(*, timeout_seconds: int) -> tuple[bool, str]:
    try:
        soffice, _source = _resolve_soffice_exe()
        fallback_detail = read_runtime_detail(soffice)
        result = _run_start_probe(soffice, timeout_seconds=timeout_seconds)
    except Exception as exc:
        return False, f"LibreOffice-Selbsttest fehlgeschlagen: {exc}"
    detail = result.stdout.strip() or result.stderr.strip() or fallback_detail
    return True, detail


def read_runtime_detail(soffice: Path) -> str:
    buildid, vendor = _load_version_metadata(_version_ini_path(soffice))
    return f"LibreOffice runtime bereit (buildid={buildid}, vendor={vendor})"


def _run_start_probe(soffice: Path, *, timeout_seconds: int) -> subprocess.CompletedProcess[str]:
    profile_dir = Path(tempfile.mkdtemp(prefix="file-optimizer-lo-health-"))
    try:
        return subprocess.run(
            [
                str(soffice),
                "--headless",
                "--nologo",
                "--nodefault",
                "--norestore",
                f"-env:UserInstallation={profile_dir.as_uri()}",
                "--terminate_after_init",
            ],
            capture_output=True,
            timeout=timeout_seconds,
            check=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            **_soffice_subprocess_kwargs(subprocess),
        )
    finally:
        shutil.rmtree(profile_dir, ignore_errors=True)


def _load_version_metadata(version_ini_path: Path) -> tuple[str, str]:
    parser = configparser.ConfigParser()
    parser.optionxform = str
    try:
        with version_ini_path.open("r", encoding="utf-8") as handle:
            parser.read_file(handle)
    except OSError as exc:
        raise FileNotFoundError(f"LibreOffice version.ini fehlt: {version_ini_path}") from exc
    except configparser.Error as exc:
        raise ValueError(f"LibreOffice version.ini ist unlesbar: {version_ini_path}") from exc
    if not parser.has_section(_VERSION_SECTION):
        raise ValueError(f"LibreOffice version.ini enthaelt keine [{_VERSION_SECTION}]-Sektion: {version_ini_path}")
    buildid = parser.get(_VERSION_SECTION, "buildid", fallback="").strip()
    vendor = parser.get(_VERSION_SECTION, "Vendor", fallback="").strip()
    if not buildid or not vendor:
        raise ValueError(f"LibreOffice version.ini ist unvollstaendig: {version_ini_path}")
    return buildid, vendor


def _version_ini_path(soffice: Path) -> Path:
    return soffice.with_name("version.ini")
