from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
MODULE_MANIFEST = PROJECT_ROOT / "module-manifest.json"
RUNTIME_MANIFEST = PROJECT_ROOT / "runtime" / "runtime-manifest.json"
RUNTIME_ROOT = PROJECT_ROOT / "runtime" / "python"
HEADLESS_RUNTIME_PATHS = (
    Path("tcl"),
    Path("DLLs") / "tcl86t.dll",
    Path("DLLs") / "tk86t.dll",
    Path("DLLs") / "_tkinter.pyd",
    Path("Lib") / "tkinter",
    Path("Lib") / "idlelib",
    Path("Lib") / "turtledemo",
)


def _launcher_package_name() -> str:
    package_name = str(json.loads(MODULE_MANIFEST.read_text(encoding="utf-8")).get("launcher_module") or "").strip()
    if not package_name:
        raise ValueError(f"launcher_module fehlt in {MODULE_MANIFEST}")
    return package_name


def _remove_path(target: Path) -> None:
    if target.is_dir():
        shutil.rmtree(target, ignore_errors=True)
        return
    target.unlink(missing_ok=True)


def _finalize_runtime_layout(runtime_root: Path) -> None:
    if not runtime_root.exists():
        return
    for relative_path in HEADLESS_RUNTIME_PATHS:
        _remove_path(runtime_root / relative_path)


def _runtime_manifest_payload(package_name: str) -> dict[str, object]:
    return {
        "python_version": "3.11",
        "runtime_candidates": {
            "python": [
                "runtime/python/python.exe",
                "runtime/python/Scripts/python.exe",
                "runtime/python/bin/python",
            ]
        },
        "required_files": [
            "runtime/python/python.exe",
            "runtime/python/pythonw.exe",
            "runtime/python/python3.dll",
            "runtime/python/python311.dll",
            "runtime/python/vcruntime140.dll",
            "runtime/python/vcruntime140_1.dll",
            "runtime/python/Lib/encodings/__init__.py",
            "runtime/requirements.lock.txt",
            "vision_pipeline_shared/__init__.py",
            "vision_pipeline_shared/semantic_identity.py",
            f"{package_name}/__main__.py",
            f"{package_name}/context/runtime_report.py",
            f"{package_name}/edit_contract/__init__.py",
            f"{package_name}/edit_contract/__main__.py",
            f"{package_name}/edit_contract/config_repository.py",
            f"{package_name}/edit_contract/describe_surfaces.py",
            f"{package_name}/edit_contract/operations.py",
            f"{package_name}/edit_contract/read_surface.py",
            f"{package_name}/edit_contract/repository.py",
            f"{package_name}/edit_contract/summary.py",
            f"{package_name}/edit_contract/summary_cards.py",
            f"{package_name}/edit_contract/types.py",
            f"{package_name}/edit_contract/validate_surface.py",
            f"{package_name}/edit_contract/validation.py",
            f"{package_name}/edit_contract/workflow.py",
            f"{package_name}/edit_contract/write_surface.py",
            f"{package_name}/main/__init__.py",
            f"{package_name}/models/source_identity.py",
            f"{package_name}/orchestrator_contract/__init__.py",
            f"{package_name}/orchestrator_contract/__main__.py",
            f"{package_name}/orchestrator_contract/adapter.py",
            f"{package_name}/orchestrator_contract/action_names.py",
            f"{package_name}/orchestrator_contract/debug_preview.py",
            f"{package_name}/orchestrator_contract/debug_workflow.py",
            f"{package_name}/orchestrator_contract/result_envelope.py",
            f"{package_name}/orchestrator_contract/types.py",
            f"{package_name}/orchestrator_contract/validation.py",
            f"{package_name}/orchestrator_contract/validation_debug.py",
            f"{package_name}/orchestrator_contract/validation_keys.py",
            f"{package_name}/orchestrator_contract/validation_owner_commands.py",
            f"{package_name}/orchestrator_contract/validation_owner_envelope.py",
            f"{package_name}/orchestrator_contract/validation_standard_commands.py",
            f"{package_name}/orchestrator_contract/validation_suite.py",
            f"{package_name}/orchestrator_contract/workflow_core.py",
            f"{package_name}/orchestrator_contract/workflow_dispatch.py",
            f"{package_name}/orchestrator_contract/workflow.py",
            f"{package_name}/orchestrator_contract/workflow_healthcheck.py",
            f"{package_name}/orchestrator_contract/workflow_suite.py",
            f"{package_name}/orchestrator_contract/workflow_suite_corpus.py",
            f"{package_name}/orchestrator_contract/workflow_suite_ontology.py",
            f"{package_name}/orchestrator_contract/workflow_suite_phase19.py",
            f"{package_name}/orchestrator_contract/workflow_suite_rebuild.py",
            f"{package_name}/orchestrator_contract/workflow_suite_semantic.py",
            f"{package_name}/services/corpus_context.py",
            f"{package_name}/services/corpus_admin.py",
            f"{package_name}/services/corpus_admin_confirmation.py",
            f"{package_name}/services/corpus_admin_sidecars.py",
            f"{package_name}/services/corpus_admin_sqlite.py",
            f"{package_name}/semantic_release/shared_identity.py",
            "module-manifest.json",
            "config/corpus_config.json",
            "config/search_policy.json",
            "check-runtime.bat",
        ],
    }


def _write_runtime_manifest() -> None:
    _finalize_runtime_layout(RUNTIME_ROOT)
    payload = _runtime_manifest_payload(_launcher_package_name())
    RUNTIME_MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    RUNTIME_MANIFEST.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Finalize the bundled Corpus Builder runtime.")
    parser.add_argument(
        "--write-runtime-manifest",
        action="store_true",
        help="Prune GUI-only runtime artefacts and rewrite runtime/runtime-manifest.json.",
    )
    parser.parse_args(argv)
    _write_runtime_manifest()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
