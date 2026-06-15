from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def test_build_tool_writes_local_python_path_file(tmp_path: Path):
    module = _load_module(Path(__file__).resolve().parents[2] / "tools" / "build-runtime.py", "test_build_runtime")
    target = tmp_path / "portable-python"
    target.mkdir()
    (target / "python311.dll").write_bytes(b"")
    (target / "DLLs").mkdir()
    (target / "Lib" / "site-packages").mkdir(parents=True)

    module._write_python_path_file(target)

    content = (target / "python311._pth").read_text(encoding="utf-8").splitlines()
    assert content[-1] == "import site"
    assert r"Lib\site-packages" in content


def test_build_tool_runtime_manifest_tracks_headless_surfaces():
    module = _load_module(Path(__file__).resolve().parents[2] / "tools" / "build-runtime.py", "test_build_runtime_manifest")
    payload = module._runtime_manifest_payload("normalizer_vision")
    assert payload["python_version"] == "3.11"
    assert "vision_pipeline_shared/__init__.py" in payload["required_files"]
    assert "vision_pipeline_shared/semantic_identity.py" in payload["required_files"]
    assert "normalizer_vision/shared_identity.py" in payload["required_files"]
    assert "normalizer_vision/main/__init__.py" in payload["required_files"]
    assert "normalizer_vision/orchestrator_contract/__init__.py" in payload["required_files"]
    assert "normalizer_vision/orchestrator_contract/value_parsing.py" in payload["required_files"]
    assert "normalizer_vision/orchestrator_contract/workflow.py" in payload["required_files"]
    assert "normalizer_vision/semantic_release/shared_identity.py" in payload["required_files"]
    assert "normalizer_vision/source_authoring/minimal_custom_release.py" in payload["required_files"]
    assert "check-runtime.bat" in payload["required_files"]
    assert "run.bat" not in payload["required_files"]
    assert "runtime/python/Lib/tkinter/__init__.py" not in payload["required_files"]


def test_headless_runtime_finalize_prunes_tk_payload(tmp_path: Path):
    module = _load_module(Path(__file__).resolve().parents[2] / "tools" / "build_runtime_env.py", "test_build_runtime_env")
    runtime_root = tmp_path / "runtime"
    (runtime_root / "tcl").mkdir(parents=True)
    (runtime_root / "Lib" / "tkinter").mkdir(parents=True)
    (runtime_root / "DLLs").mkdir()
    (runtime_root / "DLLs" / "_tkinter.pyd").write_bytes(b"")

    module.finalize_runtime_layout(runtime_root)

    assert not (runtime_root / "tcl").exists()
    assert not (runtime_root / "Lib" / "tkinter").exists()
    assert not (runtime_root / "DLLs" / "_tkinter.pyd").exists()


def test_validator_helpers_parse_lockfiles_and_wheels(tmp_path: Path):
    module = _load_module(Path(__file__).resolve().parent.parent / "tools" / "validate_package.py", "test_validate_package")
    lockfile = tmp_path / "requirements.lock.txt"
    lockfile.write_text("pytest==9.0.2\nPygments==2.19.2\n", encoding="utf-8")
    wheelhouse = tmp_path / "wheelhouse"
    wheelhouse.mkdir()
    (wheelhouse / "pytest-9.0.2-py3-none-any.whl").write_bytes(b"")
    (wheelhouse / "pygments-2.19.2-py3-none-any.whl").write_bytes(b"")
    assert module.parse_lockfile(lockfile) == {"pytest": "9.0.2", "pygments": "2.19.2"}
    assert module.parse_wheelhouse(wheelhouse) == {"pytest": "9.0.2", "pygments": "2.19.2"}
