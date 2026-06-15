from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from orchestrator.bootstrap import (
    ModuleRegistryError,
    StartupPrerequisiteError,
    ensure_startup_prerequisites,
    load_module_registry,
    resolve_module_runtime,
)


def _write_runtime(module_root: Path) -> None:
    runtime_dir = module_root / "runtime" / "python"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    python_name = "python.exe" if os.name == "nt" else "python"
    (runtime_dir / python_name).write_text("", encoding="utf-8")


def _write_manifest(
    module_root: Path,
    *,
    module_key: str = "interpreter",
    contract_version: int = 1,
    actions: list[str] | None = None,
) -> None:
    manifest = {
        "module_key": module_key,
        "display_name": module_key,
        "contract_version": contract_version,
        "runtime_dir": "runtime/python",
        "contract_module": "demo.contract",
        "actions": actions or ["interpret_document", "healthcheck"],
        "external_dependencies": [],
    }
    (module_root / "module-manifest.json").write_text(
        json.dumps(manifest),
        encoding="utf-8",
    )


def _write_registry(tmp_path: Path, module_root: Path, *, module_key: str = "interpreter") -> Path:
    registry_path = tmp_path / "module-registry.json"
    registry_path.write_text(
        json.dumps(
            {
                "registry_version": 1,
                "modules": {
                    module_key: {"path": str(module_root)},
                },
            }
        ),
        encoding="utf-8",
    )
    return registry_path


def test_load_module_registry_rejects_missing_manifest(tmp_path: Path) -> None:
    module_root = tmp_path / "interpreter"
    module_root.mkdir(parents=True, exist_ok=True)
    _write_runtime(module_root)
    registry_path = _write_registry(tmp_path, module_root)

    with pytest.raises(ModuleRegistryError, match="module-manifest.json is missing"):
        load_module_registry(registry_path)


def test_load_module_registry_rejects_missing_runtime(tmp_path: Path) -> None:
    module_root = tmp_path / "interpreter"
    module_root.mkdir(parents=True, exist_ok=True)
    _write_manifest(module_root)
    registry_path = _write_registry(tmp_path, module_root)

    with pytest.raises(ModuleRegistryError, match="Runtime directory is missing"):
        load_module_registry(registry_path)


def test_load_module_registry_rejects_wrong_contract_version(tmp_path: Path) -> None:
    module_root = tmp_path / "interpreter"
    module_root.mkdir(parents=True, exist_ok=True)
    _write_runtime(module_root)
    _write_manifest(module_root, contract_version=99)
    registry_path = _write_registry(tmp_path, module_root)

    with pytest.raises(ModuleRegistryError, match="Unsupported contract_version"):
        load_module_registry(registry_path)


def test_load_module_registry_rejects_runtime_dir_traversal(tmp_path: Path) -> None:
    module_root = tmp_path / "interpreter"
    module_root.mkdir(parents=True, exist_ok=True)
    _write_runtime(module_root)
    _write_manifest(module_root)
    manifest_path = module_root / "module-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["runtime_dir"] = "../outside"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    registry_path = _write_registry(tmp_path, module_root)

    with pytest.raises(ModuleRegistryError, match="runtime_dir is invalid|runtime_dir is outside"):
        load_module_registry(registry_path)


def test_load_module_registry_accepts_valid_relative_runtime_dir(tmp_path: Path) -> None:
    module_root = tmp_path / "interpreter"
    runtime_dir = module_root / "runtime" / "custom"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    python_name = "python.exe" if os.name == "nt" else "python"
    (runtime_dir / python_name).write_text("", encoding="utf-8")
    _write_manifest(module_root)
    manifest_path = module_root / "module-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["runtime_dir"] = "runtime/custom"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    registry_path = _write_registry(tmp_path, module_root)

    spec = load_module_registry(registry_path)["interpreter"]

    assert spec.runtime_dir == runtime_dir.resolve()


def test_resolve_module_runtime_rejects_missing_required_action(tmp_path: Path) -> None:
    module_root = tmp_path / "interpreter"
    module_root.mkdir(parents=True, exist_ok=True)
    _write_runtime(module_root)
    _write_manifest(module_root, actions=["interpret_document"])
    registry_path = _write_registry(tmp_path, module_root)

    with pytest.raises(ModuleRegistryError, match="does not support actions: healthcheck"):
        resolve_module_runtime(
            "interpreter",
            registry_path=registry_path,
            required_actions=("healthcheck",),
        )


def test_ensure_startup_prerequisites_wraps_registry_errors(tmp_path: Path) -> None:
    registry_path = tmp_path / "module-registry.json"
    registry_path.write_text(
        json.dumps(
            {
                "registry_version": 1,
                "modules": {
                    "interpreter": {"path": "../missing-module"},
                },
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(StartupPrerequisiteError, match="neighboring vision modules"):
        ensure_startup_prerequisites(registry_path=registry_path)


def test_ensure_startup_prerequisites_reports_missing_customtkinter(tmp_path: Path, monkeypatch) -> None:
    module_root = tmp_path / "interpreter"
    module_root.mkdir(parents=True, exist_ok=True)
    _write_runtime(module_root)
    _write_manifest(module_root)
    registry_path = _write_registry(tmp_path, module_root)

    def fake_import_module(name: str):  # noqa: ANN001
        if name == "customtkinter":
            raise ModuleNotFoundError("No module named 'customtkinter'", name="customtkinter")
        return object()

    monkeypatch.setattr("orchestrator.bootstrap.adapter.require_python_module", fake_import_module)

    with pytest.raises(StartupPrerequisiteError, match="customtkinter is missing"):
        ensure_startup_prerequisites(registry_path=registry_path)
