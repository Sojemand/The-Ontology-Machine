from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from runtime_build_tooling_support import TOOLS_ROOT, load_tool_module


def test_build_runtime_default_targets_cover_pipeline_modules() -> None:
    module = load_tool_module("test_build_runtimes", TOOLS_ROOT / "build-runtimes.py")

    targets = module._resolve_targets(None)

    assert [target.root.name for target in targets] == list(module.DEFAULT_MODULE_DIRS)


def test_runtime_base_python_resolver_requires_python311_x64(monkeypatch, tmp_path: Path) -> None:
    module = load_tool_module("test_build_runtimes_python311_resolver", TOOLS_ROOT / "build-runtimes.py")
    py314 = tmp_path / "Python314" / "python.exe"
    py311 = tmp_path / "Python311" / "python.exe"
    py314.parent.mkdir()
    py311.parent.mkdir()
    py314.write_text("", encoding="utf-8")
    py311.write_text("", encoding="utf-8")

    monkeypatch.setattr(module.sys, "platform", "win32")
    monkeypatch.setattr(module, "_runtime_python_candidates", lambda _requested: [py314, py311])
    monkeypatch.setattr(
        module,
        "query_python_layout",
        lambda candidate: SimpleNamespace(
            python_exe=candidate,
            platform="win32",
            version_info=(3, 11, 9) if candidate == py311 else (3, 14, 0),
        ),
    )
    monkeypatch.setattr(module, "_python_bits", lambda _python_exe: 64)

    assert module._resolve_runtime_base_python(None) == py311


def test_runtime_base_python_resolver_rejects_explicit_non_311(monkeypatch, tmp_path: Path) -> None:
    module = load_tool_module("test_build_runtimes_rejects_python314", TOOLS_ROOT / "build-runtimes.py")
    py314 = tmp_path / "Python314" / "python.exe"
    py314.parent.mkdir()
    py314.write_text("", encoding="utf-8")

    monkeypatch.setattr(module.sys, "platform", "win32")
    monkeypatch.setattr(
        module,
        "query_python_layout",
        lambda candidate: SimpleNamespace(python_exe=candidate, platform="win32", version_info=(3, 14, 0), version_text="3.14.0"),
    )
    monkeypatch.setattr(module, "_python_bits", lambda _python_exe: 64)

    with pytest.raises(RuntimeError, match="nicht CPython 3.11 x64"):
        module._resolve_runtime_base_python(str(py314))
