from __future__ import annotations

import json
import shutil
import ssl
import sys
from pathlib import Path
from typing import Any, Callable
import urllib.request

from bootstrap_paths import (
    EMBEDDED_PYTHON_FILENAME,
    EMBEDDED_PYTHON_URL,
    EMBEDDED_PYTHON_VERSION,
    VENDORED_WHEELS,
    PluginPaths,
)


def download_wheelhouse_impl(
    paths: PluginPaths,
    *,
    offline: bool,
    refresh: bool,
    materialize_wheelhouse: Callable[[Path], None],
    wheelhouse_archive_path: Callable[[Path], Path],
    download_file: Callable[[str, Path, ssl.SSLContext], None],
) -> dict[str, Any]:
    if sys.platform != "win32":
        raise RuntimeError("mail-outlook-store bootstrap ist nur fuer Windows implementiert.")
    if refresh:
        shutil.rmtree(paths.wheelhouse_dir, ignore_errors=True)
        wheelhouse_archive_path(paths.wheelhouse_dir).unlink(missing_ok=True)
    materialize_wheelhouse(paths.wheelhouse_dir)
    paths.wheelhouse_dir.mkdir(parents=True, exist_ok=True)
    ctx = _ssl_context()
    embedded_archive_path = paths.wheelhouse_dir / EMBEDDED_PYTHON_FILENAME
    if not embedded_archive_path.exists():
        if offline:
            raise FileNotFoundError(f"Offline-Build angefordert, aber {embedded_archive_path.name} fehlt in {paths.wheelhouse_dir}")
        download_file(EMBEDDED_PYTHON_URL, embedded_archive_path, ctx)
    wheel_assets = [_materialize_wheel(paths, wheel_spec, offline, ctx, download_file) for wheel_spec in VENDORED_WHEELS]
    return {
        "embedded_python": {
            "version": EMBEDDED_PYTHON_VERSION,
            "filename": EMBEDDED_PYTHON_FILENAME,
            "path": str(embedded_archive_path),
            "url": EMBEDDED_PYTHON_URL,
        },
        "wheel_assets": wheel_assets,
    }


def _materialize_wheel(
    paths: PluginPaths,
    wheel_spec: dict[str, str],
    offline: bool,
    ctx: ssl.SSLContext,
    download_file: Callable[[str, Path, ssl.SSLContext], None],
) -> dict[str, str]:
    wheel_filename = str(wheel_spec["filename"])
    wheel_path = paths.wheelhouse_dir / wheel_filename
    if not wheel_path.exists():
        if offline:
            raise FileNotFoundError(f"Offline-Build angefordert, aber {wheel_filename} fehlt in {paths.wheelhouse_dir}")
        release_payload = _read_json(f"https://pypi.org/pypi/{wheel_spec['project']}/{wheel_spec['version']}/json", ctx)
        download_file(_resolve_wheel_url(release_payload, wheel_filename), wheel_path, ctx)
    return {
        "project": str(wheel_spec["project"]),
        "version": str(wheel_spec["version"]),
        "filename": wheel_filename,
        "path": str(wheel_path),
    }


def _ssl_context() -> ssl.SSLContext:
    try:
        import certifi  # type: ignore

        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        return ssl.create_default_context()


def _read_json(url: str, ctx: ssl.SSLContext) -> dict[str, Any]:
    with urllib.request.urlopen(url, context=ctx, timeout=60) as response:
        return json.load(response)


def _resolve_wheel_url(payload: dict[str, Any], expected_filename: str) -> str:
    for entry in payload.get("urls", []):
        if entry.get("filename") == expected_filename:
            return str(entry["url"])
    raise FileNotFoundError(f"Wheel {expected_filename} ist im angegebenen Release nicht verfuegbar.")
