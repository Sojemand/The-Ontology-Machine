from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
import zipfile

import pytest


PLUGIN_DIR = Path(__file__).parent.parent.parent / "plugins" / "mail-outlook-store"


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, str(path))
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def test_bootstrap_writes_install_state_and_vendor_dir(monkeypatch, tmp_path: Path) -> None:
    bootstrap = _load_module("mail_outlook_store_bootstrap", PLUGIN_DIR / "bootstrap.py")
    plugin_dir = tmp_path / "mail-outlook-store"
    plugin_dir.mkdir()
    runtime_dir = plugin_dir / "runtime" / "python"

    monkeypatch.setattr(
        bootstrap,
        "download_wheelhouse",
        lambda _paths, **_kwargs: {
            "embedded_python": {"version": "3.9.13", "filename": "python-3.9.13-embed-amd64.zip", "path": "embed.zip"},
            "wheel_assets": [{"filename": "libpff_python-20211114-cp39-cp39-win_amd64.whl"}],
        },
    )
    monkeypatch.setattr(
        bootstrap,
        "install_into_runtime",
        lambda _paths, runtime_dir_arg, **_kwargs: runtime_dir_arg.mkdir(parents=True, exist_ok=True),
    )

    result = bootstrap.bootstrap(plugin_dir, runtime_dir, refresh_wheelhouse=True)

    install_state_path = plugin_dir / "runtime" / "install_state.json"
    assert install_state_path.exists()
    payload = json.loads(install_state_path.read_text(encoding="utf-8"))
    assert payload["bootstrap_version"] == "1.1.0"
    assert payload["runtime_layout"] == "embedded-cpython"
    assert payload["runtime_dir"] == "runtime/python"
    assert payload["vendor_dir"] == "runtime/vendor"
    assert payload["embedded_python_version"] == "3.9.13"
    assert result["vendored_wheels"] == ["libpff_python-20211114-cp39-cp39-win_amd64.whl"]


def test_install_into_runtime_extracts_embedded_runtime_and_vendor_wheels(tmp_path: Path) -> None:
    bootstrap = _load_module("mail_outlook_store_bootstrap_install", PLUGIN_DIR / "bootstrap.py")
    plugin_dir = tmp_path / "mail-outlook-store"
    plugin_dir.mkdir()
    paths = bootstrap.resolve_paths(plugin_dir)
    runtime_dir = plugin_dir / "runtime" / "python"
    paths.wheelhouse_dir.mkdir(parents=True, exist_ok=True)
    embedded_zip = paths.wheelhouse_dir / "python-3.9.13-embed-amd64.zip"
    libpff_wheel = paths.wheelhouse_dir / "libpff_python-20211114-cp39-cp39-win_amd64.whl"
    pywin32_wheel = paths.wheelhouse_dir / "pywin32-311-cp39-cp39-win_amd64.whl"

    with zipfile.ZipFile(embedded_zip, "w") as archive:
        archive.writestr("python.exe", b"stub")
        archive.writestr("python39.zip", b"stub")
        archive.writestr("python39._pth", "python39.zip\n.\n")
    with zipfile.ZipFile(libpff_wheel, "w") as archive:
        archive.writestr("pypff.pyd", b"stub")
    with zipfile.ZipFile(pywin32_wheel, "w") as archive:
        archive.writestr("win32api.pyd", b"stub")

    artifacts = {
        "embedded_python": {"path": str(embedded_zip)},
        "wheel_assets": [{"path": str(libpff_wheel)}, {"path": str(pywin32_wheel)}],
    }

    bootstrap.install_into_runtime(paths, runtime_dir, offline=True, artifacts=artifacts)

    assert (runtime_dir / "python.exe").exists()
    assert (runtime_dir / "python39.zip").exists()
    assert (runtime_dir / "python39._pth").exists()
    assert (paths.vendor_dir / "pypff.pyd").exists()
    assert (paths.vendor_dir / "win32api.pyd").exists()


def test_bootstrap_atomic_write_preserves_existing_file_when_replace_fails(monkeypatch, tmp_path: Path) -> None:
    bootstrap = _load_module("mail_outlook_store_bootstrap_atomic", PLUGIN_DIR / "bootstrap.py")
    target = tmp_path / "runtime" / "install_state.json"
    target.parent.mkdir(parents=True)
    target.write_text("old", encoding="utf-8")
    monkeypatch.setattr(bootstrap.os, "replace", lambda _src, _dst: (_ for _ in ()).throw(PermissionError("locked")))

    with pytest.raises(PermissionError, match="locked"):
        bootstrap._atomic_text_write(target, "new")

    assert target.read_text(encoding="utf-8") == "old"
    assert list(target.parent.glob("*.tmp")) == []


def test_bootstrap_download_uses_atomic_publication(monkeypatch, tmp_path: Path) -> None:
    bootstrap = _load_module("mail_outlook_store_bootstrap_download", PLUGIN_DIR / "bootstrap.py")
    calls: list[tuple[Path, bytes]] = []

    class _Response:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def read(self) -> bytes:
            return b"payload"

    monkeypatch.setattr(bootstrap.urllib.request, "urlopen", lambda *_args, **_kwargs: _Response())
    monkeypatch.setattr(bootstrap, "_atomic_bytes_write", lambda path, data: calls.append((path, data)))
    target = tmp_path / "wheelhouse" / "artifact.whl"

    bootstrap._download_file("https://example.invalid/artifact.whl", target, bootstrap.ssl.create_default_context())

    assert calls == [(target, b"payload")]


def test_bootstrap_download_preserves_existing_artifact_when_replace_fails(monkeypatch, tmp_path: Path) -> None:
    bootstrap = _load_module("mail_outlook_store_bootstrap_download_locked", PLUGIN_DIR / "bootstrap.py")

    class _Response:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def read(self) -> bytes:
            return b"new-payload"

    monkeypatch.setattr(bootstrap.urllib.request, "urlopen", lambda *_args, **_kwargs: _Response())
    monkeypatch.setattr(bootstrap.os, "replace", lambda _src, _dst: (_ for _ in ()).throw(PermissionError("locked")))
    monkeypatch.setattr(bootstrap.time, "sleep", lambda _seconds: None)
    target = tmp_path / "wheelhouse" / "artifact.whl"
    target.parent.mkdir(parents=True)
    target.write_bytes(b"old-payload")

    with pytest.raises(PermissionError, match="locked"):
        bootstrap._download_file("https://example.invalid/artifact.whl", target, bootstrap.ssl.create_default_context())

    assert target.read_bytes() == b"old-payload"
    assert list(target.parent.glob("*.tmp")) == []
