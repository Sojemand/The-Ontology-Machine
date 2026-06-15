from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from .semantic_release_test_support import build_release_variant


PROJECT_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_ROOT = PROJECT_ROOT / "dev-tests" / "tests" / "fixtures" / "regression" / "vision_invoice"
COPYTREE_IGNORE = shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo")


def _copy_module(tmp_path: Path) -> Path:
    module_root = tmp_path / "corpus_builder_module"
    shutil.copytree(PROJECT_ROOT / "corpus_builder", module_root / "corpus_builder", ignore=COPYTREE_IGNORE)
    shutil.copytree(PROJECT_ROOT / "config", module_root / "config", ignore=COPYTREE_IGNORE)
    shutil.copytree(PROJECT_ROOT / "vision_pipeline_shared", module_root / "vision_pipeline_shared", ignore=COPYTREE_IGNORE)
    shutil.copy2(PROJECT_ROOT / "module-manifest.json", module_root / "module-manifest.json")
    return module_root


def _invoke_contract(module_root: Path, *, contract_module: str, payload: dict) -> dict:
    request_path = module_root / "request.json"
    response_path = module_root / "response.json"
    request_path.write_text(json.dumps(payload), encoding="utf-8")
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            contract_module,
            "--request",
            str(request_path),
            "--response",
            str(response_path),
        ],
        cwd=module_root,
        capture_output=True,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr or completed.stdout
    return json.loads(response_path.read_text(encoding="utf-8"))


def _write_active_release(module_root: Path) -> None:
    state_dir = module_root / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    payload = build_release_variant(project_root=PROJECT_ROOT)
    (state_dir / "semantic_release.active.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _write_debug_inputs(tmp_path: Path) -> tuple[Path, Path, Path]:
    vision_structured = json.loads((FIXTURE_ROOT / "invoice.structured.json").read_text(encoding="utf-8"))
    vision_normalized = json.loads((FIXTURE_ROOT / "invoice.structured.normalized.json").read_text(encoding="utf-8"))
    vision_validation_report = json.loads((FIXTURE_ROOT / "invoice.vision_validation_report.json").read_text(encoding="utf-8"))

    pipeline_root = tmp_path / "pipeline"
    normalized_dir = pipeline_root / "normalized" / "finance"
    structured_dir = pipeline_root / "structured" / "finance"
    validation_dir = pipeline_root / "validation" / "finance"
    for folder in (normalized_dir, structured_dir, validation_dir):
        folder.mkdir(parents=True, exist_ok=True)
    normalized_path = normalized_dir / "invoice.pdf.structured.normalized.json"
    normalized_path.write_text(json.dumps(vision_normalized, indent=2), encoding="utf-8")
    (structured_dir / "invoice.pdf.structured.json").write_text(json.dumps(vision_structured, indent=2), encoding="utf-8")
    (validation_dir / "invoice.pdf.vision_validation_report.json").write_text(json.dumps(vision_validation_report, indent=2), encoding="utf-8")
    return pipeline_root, normalized_dir, normalized_path


def test_standalone_copy_supports_corpus_builder_public_contracts(tmp_path: Path) -> None:
    module_root = _copy_module(tmp_path)
    _write_active_release(module_root)
    pipeline_root, normalized_dir, normalized_path = _write_debug_inputs(tmp_path)

    healthcheck = _invoke_contract(
        module_root,
        contract_module="corpus_builder.orchestrator_contract",
        payload={
            "action": "healthcheck",
            "scope": "pipeline_run",
            "runtime_settings": {"model": "text-embedding-3-small"},
        },
    )
    scan = _invoke_contract(
        module_root,
        contract_module="corpus_builder.orchestrator_contract",
        payload={
            "action": "scan_debug_input",
            "mode": "scan",
            "session_root": str(tmp_path / "scan-session"),
            "input_root": str(pipeline_root),
        },
    )
    debug = _invoke_contract(
        module_root,
        contract_module="corpus_builder.orchestrator_contract",
        payload={
            "action": "debug_run",
            "mode": "single",
            "session_root": str(tmp_path / "debug-session"),
            "output_root": str(tmp_path / "debug-session" / "outputs"),
            "input_root": str(normalized_dir),
            "source_path": str(normalized_path),
        },
    )

    assert healthcheck["status"] == "ok"
    assert scan["status"] == "ok"
    assert (tmp_path / "scan-session" / "outputs" / "preview_report.json").exists()
    assert debug["status"] == "ok"
    assert (tmp_path / "debug-session" / "outputs" / "corpus.db").exists()
    assert (tmp_path / "debug-session" / "outputs" / "load_report.json").exists()


def test_standalone_copy_supports_corpus_builder_edit_contract_bundle_actions(tmp_path: Path) -> None:
    module_root = _copy_module(tmp_path)

    described = _invoke_contract(
        module_root,
        contract_module="corpus_builder.edit_contract",
        payload={"action": "describe_surfaces"},
    )
    bundled = _invoke_contract(
        module_root,
        contract_module="corpus_builder.edit_contract",
        payload={"action": "read_bundle"},
    )

    assert described["status"] == "ok"
    assert bundled["status"] == "ok"
    assert [item["surface_id"] for item in bundled["surfaces"]] == [item["surface_id"] for item in described["surfaces"]]
    assert all(isinstance(item.get("value"), dict) for item in bundled["surfaces"])
