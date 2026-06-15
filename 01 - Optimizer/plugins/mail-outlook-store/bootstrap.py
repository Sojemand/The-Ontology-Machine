from __future__ import annotations

"""Build-time helper for the bundled mail-outlook-store runtime."""

import argparse
from datetime import datetime, timezone
import json
import os
import shutil
import ssl
import sys
import time
from pathlib import Path
import tempfile
from typing import Any
import urllib.request
import zipfile

PLUGIN_DIR = Path(__file__).resolve().parent
if str(PLUGIN_DIR) not in sys.path:
    sys.path.insert(0, str(PLUGIN_DIR))
PIPELINE_TOOLS_DIR = Path(__file__).resolve().parents[3] / "tools"
if str(PIPELINE_TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(PIPELINE_TOOLS_DIR))

from bootstrap_download import download_wheelhouse_impl  # noqa: E402
from bootstrap_cli import main_impl  # noqa: E402
from bootstrap_paths import (  # noqa: E402
    BOOTSTRAP_VERSION,
    EMBEDDED_PYTHON_VERSION,
    PluginPaths,
    resolve_paths,
)
from portable_runtime import archive_wheelhouse as archive_wheelhouse_dir, materialize_wheelhouse, wheelhouse_archive_path  # noqa: E402


def bootstrap(
    plugin_dir: Path,
    runtime_dir: Path,
    *,
    base_python: Path | None = None,
    offline: bool = False,
    refresh_wheelhouse: bool = False,
    archive_wheelhouse: bool = False,
) -> dict[str, Any]:
    del base_python
    paths = resolve_paths(plugin_dir)
    paths.runtime_root.mkdir(parents=True, exist_ok=True)
    artifacts = download_wheelhouse(paths, offline=offline, refresh=refresh_wheelhouse)
    install_into_runtime(paths, runtime_dir, offline=offline, artifacts=artifacts)
    archive_path = _archive_ref(plugin_dir, paths, archive_wheelhouse)
    payload = {
        "bootstrap_version": BOOTSTRAP_VERSION,
        "runtime_layout": "embedded-cpython",
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "runtime_dir": _relative_to_plugin(plugin_dir, runtime_dir),
        "python_dir": _relative_to_plugin(plugin_dir, runtime_dir),
        "wheelhouse_dir": _relative_to_plugin(plugin_dir, paths.wheelhouse_dir),
        "wheelhouse_archive": archive_path,
        "vendor_dir": _relative_to_plugin(plugin_dir, paths.vendor_dir),
        "embedded_python_version": EMBEDDED_PYTHON_VERSION,
        "vendored_wheels": [artifact["filename"] for artifact in artifacts["wheel_assets"]],
        "base_python": "",
    }
    _atomic_text_write(paths.install_state_path, json.dumps(payload, ensure_ascii=False, indent=2))
    return payload


def download_wheelhouse(
    paths: PluginPaths,
    *,
    base_python: Path | None = None,
    offline: bool,
    refresh: bool,
) -> dict[str, Any]:
    del base_python
    return download_wheelhouse_impl(
        paths,
        offline=offline,
        refresh=refresh,
        materialize_wheelhouse=materialize_wheelhouse,
        wheelhouse_archive_path=wheelhouse_archive_path,
        download_file=_download_file,
    )


def install_into_runtime(
    paths: PluginPaths,
    runtime_dir: Path,
    *,
    offline: bool,
    artifacts: dict[str, Any] | None = None,
) -> None:
    del offline
    if sys.platform != "win32":
        raise RuntimeError("mail-outlook-store bootstrap ist nur fuer Windows implementiert.")
    artifacts = artifacts or download_wheelhouse(paths, offline=False, refresh=False)
    runtime_dir.parent.mkdir(parents=True, exist_ok=True)
    shutil.rmtree(runtime_dir, ignore_errors=True)
    shutil.rmtree(paths.vendor_dir, ignore_errors=True)
    runtime_dir.mkdir(parents=True, exist_ok=True)
    paths.vendor_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(artifacts["embedded_python"]["path"]) as archive:
        archive.extractall(runtime_dir)
    for wheel_asset in artifacts["wheel_assets"]:
        with zipfile.ZipFile(wheel_asset["path"]) as archive:
            archive.extractall(paths.vendor_dir)
    if not (runtime_dir / "python.exe").exists():
        raise FileNotFoundError(f"Embedded Python wurde nicht korrekt materialisiert: {runtime_dir}")


def _archive_ref(plugin_dir: Path, paths: PluginPaths, archive_wheelhouse: bool) -> str:
    archive_path = wheelhouse_archive_path(paths.wheelhouse_dir)
    if archive_wheelhouse:
        archived = archive_wheelhouse_dir(paths.wheelhouse_dir, prune=True)
        return _relative_to_plugin(plugin_dir, archive_path) if archived else ""
    return _relative_to_plugin(plugin_dir, archive_path) if archive_path.exists() else ""


def _download_file(url: str, destination: Path, ctx) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(url, context=ctx, timeout=180) as response:
        _atomic_bytes_write(destination, response.read())


def _relative_to_plugin(plugin_dir: Path, path: Path | None) -> str:
    if path is None:
        return ""
    try:
        return str(path.relative_to(plugin_dir)).replace("\\", "/")
    except ValueError:
        return str(path)


def _atomic_text_write(path: Path, text: str) -> None:
    _atomic_bytes_write(path, text.encode("utf-8"))


def _atomic_bytes_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = -1
    tmp_path: Path | None = None
    try:
        fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
        tmp_path = Path(tmp_name)
        with os.fdopen(fd, "wb") as handle:
            fd = -1
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        _replace_with_retry(tmp_path, path)
    except Exception:
        if fd != -1:
            os.close(fd)
        if tmp_path is not None:
            try:
                tmp_path.unlink(missing_ok=True)
            except OSError:
                pass
        raise


def _replace_with_retry(src: Path, dst: Path, attempts: int = 8) -> None:
    last_error: OSError | None = None
    for attempt in range(attempts):
        try:
            os.replace(src, dst)
            return
        except PermissionError as exc:
            last_error = exc
            if attempt == attempts - 1:
                break
            time.sleep(0.01 * (attempt + 1))
    if last_error is not None:
        raise last_error


def _default_runtime_dir(plugin_dir: Path) -> Path:
    return plugin_dir / "runtime" / "python"


def main() -> int:
    return main_impl(
        default_plugin_dir=PLUGIN_DIR,
        resolve_paths=resolve_paths,
        default_runtime_dir=_default_runtime_dir,
        download_wheelhouse=download_wheelhouse,
        install_into_runtime=install_into_runtime,
        bootstrap=bootstrap,
    )


if __name__ == "__main__":
    raise SystemExit(main())
