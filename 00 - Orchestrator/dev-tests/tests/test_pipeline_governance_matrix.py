from __future__ import annotations

import json
import os
from pathlib import Path


PIPELINE_ROOT = Path(__file__).resolve().parents[3]
ORCHESTRATOR_ROOT = PIPELINE_ROOT / "00 - Orchestrator"
MODULE_DIRS = {
    "optimizer": PIPELINE_ROOT / "01 - Optimizer",
    "interpreter": PIPELINE_ROOT / "02 - Interpreter",
    "validator": PIPELINE_ROOT / "03 - Validator",
    "normalizer": PIPELINE_ROOT / "04 - Normalizer",
    "corpus_builder": PIPELINE_ROOT / "05 - Corpus Builder",
}
EXPECTED_STAGE_NAMES = [
    "Intake",
    "Runtime Semantics",
    "Optimizer",
    "Request Enrichment",
    "Interpreter",
    "Validator",
    "Normalizer",
    "Corpus Builder",
    "Embeddings",
]
OPERATION_TIMEOUT_ACTIONS = {
    "classify_document",
    "extract_document",
    "interpret_document",
    "validate_document",
    "normalize_document",
    "load_document",
    "activate_semantic_release",
    "generate_embeddings",
}


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def test_execution_policy_stage_order_matches_current_pipeline_contract() -> None:
    policy = _read_json(ORCHESTRATOR_ROOT / "config" / "execution_policy.json")

    assert policy["pipeline_stage_names"] == EXPECTED_STAGE_NAMES
    assert "Request Enrichment" in policy["pipeline_stage_names"]
    assert policy["global_required_modules"] == ["validator", "normalizer", "corpus_builder"]


def test_orchestrator_required_actions_are_owned_by_module_manifests() -> None:
    policy = _read_json(ORCHESTRATOR_ROOT / "config" / "execution_policy.json")

    for module_key, module_policy in policy["modules"].items():
        module_root = MODULE_DIRS[module_key]
        manifest = _read_json(module_root / "module-manifest.json")
        manifest_actions = set(manifest["actions"])
        required_actions = set(module_policy["required_actions"])

        assert manifest["module_key"] == module_key
        assert manifest["contract_module"]
        assert required_actions <= manifest_actions
        assert module_policy["stage_role"] in EXPECTED_STAGE_NAMES

        for action in required_actions & OPERATION_TIMEOUT_ACTIONS:
            assert action in policy["operation_timeouts_seconds"]


def test_pipeline_owner_modules_have_contract_runtime_docs_and_dev_tests() -> None:
    for module_root in MODULE_DIRS.values():
        manifest = _read_json(module_root / "module-manifest.json")
        contract_path = module_root / Path(*str(manifest["contract_module"]).split(".")) / "__init__.py"

        assert contract_path.exists(), f"Contract entry point missing: {contract_path}"
        assert (module_root / "runtime" / "runtime-manifest.json").exists()
        assert (module_root / "dev-tests" / "suite.json").exists()
        assert (module_root / "README.md").exists()


def test_public_non_mcp_actions_are_test_visible_in_owner_suites() -> None:
    for module_root in MODULE_DIRS.values():
        manifest = _read_json(module_root / "module-manifest.json")
        test_files = list(_iter_owner_test_files(module_root / "dev-tests"))
        test_text = "\n".join(path.read_text(encoding="utf-8", errors="ignore") for path in test_files)

        for action in manifest["actions"]:
            assert action in test_text, f"{manifest['module_key']} action lacks owner-suite evidence: {action}"


def _iter_owner_test_files(root: Path):
    for dirpath, dirnames, filenames in os.walk(root, topdown=True, onerror=lambda _exc: None):
        dirnames[:] = [name for name in dirnames if not name.startswith(".pytest-tmp-")]
        for filename in filenames:
            if filename.endswith(".py") and (filename.startswith("test_") or filename.endswith("_cases.py")):
                yield Path(dirpath) / filename
