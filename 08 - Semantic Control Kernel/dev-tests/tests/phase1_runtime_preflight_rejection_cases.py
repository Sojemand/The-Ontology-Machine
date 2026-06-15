from __future__ import annotations

import json
import os
from pathlib import Path

from phase1_runtime_preflight_support import (
    MODULE_ROOT,
    PIPELINE_ROOT,
    complete_runtime_layout,
    fixture_module_root,
    runtime_sys_path,
    write_json,
)
from semantic_control_kernel.bootstrap import runtime_report


def test_runtime_report_rejects_sibling_sys_path_leakage() -> None:
    report = runtime_report.build_report(
        MODULE_ROOT,
        strict=True,
        sys_path=[*os.sys.path, str(PIPELINE_ROOT / "00 - Orchestrator")],
        cwd=MODULE_ROOT,
    )

    assert report["ok"] is False
    assert report["error"]["code"] == "sibling_path_leak"


def test_runtime_report_rejects_invalid_package_import_path() -> None:
    report = runtime_report.build_report(
        MODULE_ROOT,
        strict=True,
        sys_path=[str(PIPELINE_ROOT)],
        cwd=MODULE_ROOT,
    )

    assert report["ok"] is False
    assert report["error"]["code"] == "package_import_path_invalid"


def test_runtime_report_rejects_invalid_working_directory() -> None:
    report = runtime_report.build_report(
        MODULE_ROOT,
        strict=True,
        sys_path=runtime_sys_path(str(MODULE_ROOT)),
        cwd=PIPELINE_ROOT,
    )

    assert report["ok"] is False
    assert report["error"]["code"] == "working_directory_invalid"


def test_runtime_report_rejects_bad_runtime_layout_fixture(tmp_path: Path) -> None:
    root = fixture_module_root(tmp_path, runtime_python=True)

    report = runtime_report.build_report(root, strict=True, sys_path=[str(root), *os.sys.path], cwd=root)

    assert report["ok"] is False
    assert report["error"]["code"] == "runtime_layout_invalid"


def test_runtime_report_rejects_manifest_action_count_drift(tmp_path: Path) -> None:
    root = fixture_module_root(tmp_path, runtime_python=True)
    complete_runtime_layout(root)
    manifest_path = root / "module-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["actions"] = ["tool_00"]
    write_json(manifest_path, manifest)

    report = runtime_report.build_report(root, strict=True, sys_path=[str(root)], cwd=root)

    assert report["ok"] is False
    assert report["error"]["code"] == "manifest_invalid"
    module_manifest_check = next(check for check in report["checks"] if check["name"] == "module_manifest")
    assert module_manifest_check["ok"] is False


def test_contract_import_check_rejects_sibling_module_imports(tmp_path: Path) -> None:
    root = fixture_module_root(tmp_path, runtime_python=False)
    (root / "runtime").mkdir(exist_ok=True)
    (root / "semantic_control_kernel" / "orchestrator_contract.py").write_text(
        "import semantic_control_kernel.sibling\n",
        encoding="utf-8",
    )
    (root / "semantic_control_kernel" / "sibling.py").write_text("", encoding="utf-8")

    ok, message = runtime_report._contract_import_check(root, [str(root)])

    assert ok is False
    assert "imported sibling modules" in message
    assert "semantic_control_kernel.sibling" in message


def test_contract_import_check_rejects_file_side_effects(tmp_path: Path) -> None:
    root = fixture_module_root(tmp_path, runtime_python=False)
    (root / "runtime").mkdir(exist_ok=True)
    (root / "semantic_control_kernel" / "orchestrator_contract.py").write_text(
        "from pathlib import Path\n"
        "Path(__file__).resolve().parents[1].joinpath('state', 'import-created.json').write_text('{}')\n",
        encoding="utf-8",
    )

    ok, message = runtime_report._contract_import_check(root, [str(root)])

    assert ok is False
    assert "created or removed state, runtime, log or support files" in message
