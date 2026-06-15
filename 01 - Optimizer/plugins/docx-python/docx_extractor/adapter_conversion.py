from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

from ingestion_layer_file.paths import resolve_layout

from .types import PreparedSource, WordStageError


def prepare_source(source: Path, config: dict[str, object]) -> PreparedSource:
    suffix = source.suffix.lower()
    if suffix != ".doc":
        return PreparedSource(source=source, original_suffix=suffix)

    tmp_dir = Path(tempfile.mkdtemp(prefix="docx_convert_"))
    profile_dir = Path(tempfile.mkdtemp(prefix="lo_profile_"))
    try:
        soffice = _resolve_soffice(config)
        timeout = int(config.get("libreoffice_timeout_seconds", 60) or 60)
        subprocess.run(
            [
                soffice,
                "--headless",
                f"-env:UserInstallation={profile_dir.as_uri()}",
                "--convert-to",
                "docx",
                "--outdir",
                str(tmp_dir),
                str(source),
            ],
            capture_output=True,
            check=True,
            timeout=timeout,
            text=True,
            encoding="utf-8",
            errors="replace",
            **_libreoffice_subprocess_kwargs(),
        )
        converted = tmp_dir / f"{source.stem}.docx"
        if not converted.exists():
            raise WordStageError("adapter.convert", f"LibreOffice erzeugte keine Ausgabedatei fuer {source.name}")
        return PreparedSource(source=converted, original_suffix=suffix, cleanup_dirs=(tmp_dir, profile_dir))
    except subprocess.TimeoutExpired as exc:
        cleanup_dirs((tmp_dir, profile_dir))
        raise WordStageError("adapter.convert", f"LibreOffice-Konvertierung Timeout fuer {source.name} ({exc.timeout}s)") from exc
    except subprocess.CalledProcessError as exc:
        cleanup_dirs((tmp_dir, profile_dir))
        detail = (exc.stderr or exc.stdout or "").strip()
        raise WordStageError("adapter.convert", f"LibreOffice Exit-Code {exc.returncode} fuer {source.name}: {detail[:300]}") from exc
    except WordStageError:
        cleanup_dirs((tmp_dir, profile_dir))
        raise
    except OSError as exc:
        cleanup_dirs((tmp_dir, profile_dir))
        raise WordStageError("adapter.convert", f"LibreOffice-Aufruf fehlgeschlagen: {exc}") from exc


def cleanup_prepared_source(prepared: PreparedSource | None) -> None:
    if prepared is not None:
        cleanup_dirs(prepared.cleanup_dirs)


def cleanup_dirs(paths: tuple[Path, ...] | list[Path]) -> None:
    for path in paths:
        shutil.rmtree(path, ignore_errors=True)


def _resolve_soffice(config: dict[str, object]) -> str:
    configured = str(config.get("libreoffice_path", "") or "").strip()
    if configured:
        configured_path = Path(configured).expanduser()
        if configured_path.exists():
            return str(configured_path)
        raise WordStageError("adapter.convert", f"Konfigurierte LibreOffice-Runtime nicht gefunden: {configured_path}")
    program_dir = resolve_layout().libreoffice_dir / "program"
    bundled = program_dir / ("soffice.com" if sys.platform == "win32" else "soffice")
    if sys.platform == "win32" and not bundled.exists():
        bundled = program_dir / "soffice.exe"
    if bundled.exists():
        return str(bundled)
    raise WordStageError(
        "adapter.convert",
        f"LibreOffice nicht gefunden. Erwartet gebuendelt unter {bundled} oder explizit per libreoffice_path.",
    )


def _libreoffice_subprocess_kwargs() -> dict[str, object]:
    if sys.platform != "win32":
        return {}
    kwargs: dict[str, object] = {}
    startupinfo_factory = getattr(subprocess, "STARTUPINFO", None)
    if startupinfo_factory is not None:
        startupinfo = startupinfo_factory()
        startupinfo.dwFlags |= getattr(subprocess, "STARTF_USESHOWWINDOW", 0)
        startupinfo.wShowWindow = getattr(subprocess, "SW_HIDE", 0)
        kwargs["startupinfo"] = startupinfo
    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    if creationflags:
        kwargs["creationflags"] = creationflags
    return kwargs


__all__ = ["cleanup_prepared_source", "prepare_source"]
