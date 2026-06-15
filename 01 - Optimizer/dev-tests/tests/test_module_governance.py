from __future__ import annotations

from pathlib import Path


def _module_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _contract_root() -> Path:
    return _module_root() / "ingestion_layer_vision" / "orchestrator_contract"


def _tests_root() -> Path:
    return _module_root() / "dev-tests" / "tests"


def test_orchestrator_contract_files_and_tests_stay_under_200_loc() -> None:
    tracked = list(_contract_root().glob("*.py")) + list(_tests_root().glob("test_orchestrator*.py"))
    tracked.extend([_tests_root() / "orchestrator_contract_support.py", _tests_root() / "test_module_governance.py"])

    for file_path in tracked:
        assert len(file_path.read_text(encoding="utf-8").splitlines()) <= 200, file_path.name


def test_orchestrator_contract_surface_and_tests_stay_flat() -> None:
    for file_path in _contract_root().rglob("*.py"):
        assert len(file_path.relative_to(_contract_root()).parts) == 1, file_path
    for file_path in _tests_root().rglob("test_orchestrator*.py"):
        assert len(file_path.relative_to(_tests_root()).parts) == 1, file_path
    assert len((_tests_root() / "orchestrator_contract_support.py").relative_to(_tests_root()).parts) == 1


def test_legacy_signature_shims_and_directories_path_stay_removed() -> None:
    legacy_dirs = [
        "edit_contract",
        "ruleset",
        "signature",
        "signature_candidates_vision",
        "signature_content",
        "signature_context",
        "signature_entity_domain",
        "signature_semantic",
        "signature_semantic_block_domain",
        "signature_semantic_indices",
        "signature_semantic_parties",
        "signature_semantic_prompt",
        "signature_semantic_prompt_vision",
        "signature_semantic_tables",
        "signature_semantic_table_domain",
        "signature_semantic_text_domain",
        "signature_structure",
        "signature_structure_vision",
        "signature_vision_common",
    ]
    for relative_name in legacy_dirs:
        assert not (_module_root() / "ingestion_layer_file" / relative_name).exists(), relative_name

    forbidden_patterns = [
        "from .." + "signature",
        "from ingestion_layer_file." + "signature",
        "import ingestion_layer_file." + "signature",
        "directories" + ".json",
    ]
    scanned_suffixes = {".py", ".md"}
    scan_roots = [
        _module_root() / "ingestion_layer_file",
        _tests_root(),
        _module_root() / "README.md",
    ]
    for root in scan_roots:
        file_paths = [root] if root.is_file() else list(root.rglob("*"))
        for file_path in file_paths:
            if not file_path.is_file() or file_path.suffix not in scanned_suffixes:
                continue
            text = file_path.read_text(encoding="utf-8")
            for pattern in forbidden_patterns:
                assert pattern not in text, f"{pattern} in {file_path.relative_to(_module_root())}"
