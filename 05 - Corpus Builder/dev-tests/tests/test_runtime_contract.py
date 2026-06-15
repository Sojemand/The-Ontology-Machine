from __future__ import annotations

import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_runtime_contract_keeps_launcher_and_contract_surface_aligned() -> None:
    manifest = json.loads((PROJECT_ROOT / "module-manifest.json").read_text(encoding="utf-8"))
    assert manifest["launcher_module"] == "corpus_builder"
    assert manifest["contract_module"] == "corpus_builder.orchestrator_contract"
    assert manifest["runtime_dir"] == "runtime/python"


def test_build_runtime_wrapper_targets_module_local_runtime_build() -> None:
    build_runtime = (PROJECT_ROOT / "build-runtime.bat").read_text(encoding="utf-8")
    assert '--module "05 - Corpus Builder"' in build_runtime
    assert "--offline" in build_runtime
    assert "build-runtimes.bat" in build_runtime


def test_check_runtime_wrapper_uses_bundled_runtime_report() -> None:
    script = (PROJECT_ROOT / "check-runtime.bat").read_text(encoding="utf-8")
    assert "runtime\\python" in script
    assert "corpus_builder.context.runtime_report" in script
    assert 'set "PYTHONHOME=%RUNTIME_DIR%"' in script
    assert 'set "PYTHONPATH="' in script


def test_runtime_manifest_tracks_headless_payload_and_hook() -> None:
    manifest = json.loads((PROJECT_ROOT / "runtime" / "runtime-manifest.json").read_text(encoding="utf-8"))
    assert not (PROJECT_ROOT / "run.bat").exists()
    assert (PROJECT_ROOT / "tools" / "build-runtime.py").exists()
    assert "check-runtime.bat" in manifest["required_files"]
    assert "vision_pipeline_shared/__init__.py" in manifest["required_files"]
    assert "vision_pipeline_shared/semantic_identity.py" in manifest["required_files"]
    assert "corpus_builder/context/runtime_report.py" in manifest["required_files"]
    assert "corpus_builder/orchestrator_contract/__init__.py" in manifest["required_files"]
    assert "corpus_builder/orchestrator_contract/__main__.py" in manifest["required_files"]
    assert "corpus_builder/orchestrator_contract/action_names.py" in manifest["required_files"]
    assert "corpus_builder/orchestrator_contract/workflow_dispatch.py" in manifest["required_files"]
    assert "corpus_builder/orchestrator_contract/workflow.py" in manifest["required_files"]
    assert "corpus_builder/orchestrator_contract/workflow_suite.py" in manifest["required_files"]
    assert "corpus_builder/orchestrator_contract/workflow_suite_phase19.py" in manifest["required_files"]
    assert "corpus_builder/models/source_identity.py" in manifest["required_files"]
    assert "corpus_builder/services/corpus_context.py" in manifest["required_files"]
    assert "corpus_builder/services/corpus_admin.py" in manifest["required_files"]
    assert "corpus_builder/semantic_release/shared_identity.py" in manifest["required_files"]
    assert "config/search_policy.json" in manifest["required_files"]
    assert "run.bat" not in manifest["required_files"]
    assert "runtime/python/Lib/tkinter/__init__.py" not in manifest["required_files"]
    assert "runtime/python/Lib/site-packages/customtkinter/__init__.py" not in manifest["required_files"]


def test_module_manifest_describes_optional_orchestrator_owned_embeddings_capability() -> None:
    manifest = json.loads((PROJECT_ROOT / "module-manifest.json").read_text(encoding="utf-8"))
    dependency_names = [entry["name"] for entry in manifest["external_dependencies"]]
    assert dependency_names == ["embedding_provider"]
    assert manifest["external_dependencies"][0]["required"] is False
