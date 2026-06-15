from __future__ import annotations

import json
import os
from pathlib import Path

from semantic_control_kernel.bootstrap import runtime_report

MODULE_ROOT = Path(__file__).resolve().parents[2]
PIPELINE_ROOT = MODULE_ROOT.parent


def runtime_sys_path(*prefixes: str) -> list[str]:
    cleaned: list[str] = list(prefixes)
    pipeline_root = PIPELINE_ROOT.resolve()
    sibling_roots = {
        child.resolve()
        for child in pipeline_root.iterdir()
        if child.is_dir() and child.resolve() != MODULE_ROOT.resolve()
    }
    for raw_entry in os.sys.path:
        if not raw_entry:
            continue
        try:
            entry = Path(raw_entry).resolve()
        except OSError:
            cleaned.append(raw_entry)
            continue
        if entry == pipeline_root:
            continue
        if any(entry == sibling or runtime_report._is_relative_to(entry, sibling) for sibling in sibling_roots):
            continue
        cleaned.append(raw_entry)
    return cleaned


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def fixture_module_root(tmp_path: Path, *, runtime_python: bool) -> Path:
    root = tmp_path / "08 - Semantic Control Kernel"
    (root / "semantic_control_kernel").mkdir(parents=True)
    (root / "semantic_control_kernel" / "__init__.py").write_text("", encoding="utf-8")
    (root / "semantic_control_kernel" / "orchestrator_contract.py").write_text("", encoding="utf-8")
    (root / "state").mkdir()
    write_json(
        root / "module-manifest.json",
        {
            "module_key": "semantic_control_kernel",
            "status": "agent_surface_shell",
            "contract_version": 1,
            "runtime_dir": "runtime/python",
            "launcher_module": "semantic_control_kernel",
            "contract_module": "semantic_control_kernel.orchestrator_contract",
            "actions": [f"tool_{index:02d}" for index in range(runtime_report.REQUIRED_ACTION_COUNT)],
        },
    )
    write_json(
        root / "runtime" / "runtime-manifest.json",
        {
            "module_key": "semantic_control_kernel",
            "status": "agent_surface_shell",
            "contract_version": 1,
            "runtime_kind": "python",
            "runtime_path": "runtime/python",
            "python_version": "3.11",
            "build_status": "buildable",
            "normal_operation_requires_host_python": False,
            "runtime_builder": "root_tools_build_runtimes",
            "runtime_check_module": "semantic_control_kernel.bootstrap.runtime_report",
        },
    )
    if runtime_python:
        runtime_python_path = root / "runtime" / "python" / "python.exe"
        runtime_python_path.parent.mkdir(parents=True, exist_ok=True)
        runtime_python_path.write_text("", encoding="utf-8")
    return root


def complete_runtime_layout(root: Path) -> None:
    runtime_root = root / "runtime" / "python"
    runtime_root.mkdir(parents=True, exist_ok=True)
    (runtime_root / "python.exe").write_text("", encoding="utf-8")
    (runtime_root / "Lib" / "encodings").mkdir(parents=True, exist_ok=True)
    (runtime_root / "Lib" / "os.py").write_text("", encoding="utf-8")
    (runtime_root / "Lib" / "encodings" / "__init__.py").write_text("", encoding="utf-8")
    (runtime_root / "Lib" / "site-packages").mkdir(parents=True, exist_ok=True)


def runtime_env() -> dict[str, str]:
    runtime_root = MODULE_ROOT / "runtime" / "python"
    return {
        **os.environ,
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONNOUSERSITE": "1",
        "PYTHONHOME": str(runtime_root),
        "PYTHONPATH": "",
    }
