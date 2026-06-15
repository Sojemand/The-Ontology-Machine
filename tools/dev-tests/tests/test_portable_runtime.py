from __future__ import annotations

import importlib.util
from pathlib import Path
import sys


TOOLS_ROOT = Path(__file__).resolve().parents[2]


def _load_tool_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, str(path))
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def test_archive_and_materialize_wheelhouse_roundtrip(tmp_path):
    portable_runtime = _load_tool_module("portable_runtime_roundtrip", TOOLS_ROOT / "portable_runtime.py")
    wheelhouse = tmp_path / "runtime" / "wheelhouse"
    wheelhouse.mkdir(parents=True)
    (wheelhouse / "demo.whl").write_text("wheel", encoding="utf-8")

    archive_path = portable_runtime.archive_wheelhouse(wheelhouse, prune=True)

    assert archive_path == portable_runtime.wheelhouse_archive_path(wheelhouse)
    assert archive_path.exists()
    assert not wheelhouse.exists()

    portable_runtime.materialize_wheelhouse(wheelhouse)

    assert (wheelhouse / "demo.whl").exists()


def test_runtime_problems_detect_legacy_and_missing_stdlib(tmp_path):
    portable_runtime = _load_tool_module("portable_runtime_problems", TOOLS_ROOT / "portable_runtime.py")
    runtime_dir = tmp_path / "runtime" / "python"
    runtime_dir.mkdir(parents=True)
    (runtime_dir / "python.exe").write_text("", encoding="utf-8")
    (runtime_dir / "pyvenv.cfg").write_text("home = C:/Python311\n", encoding="utf-8")

    problems = portable_runtime.runtime_problems(runtime_dir)

    assert any("legacy venv marker" in problem for problem in problems)
    assert any("stdlib missing" in problem for problem in problems)
