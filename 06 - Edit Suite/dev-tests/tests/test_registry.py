from __future__ import annotations

import json
from pathlib import Path

from edit_suite.registry import discover_registry
from edit_suite.registry import policy
from edit_suite.registry import workflow

PIPELINE_ROOT = Path(__file__).resolve().parents[3]


def _module_dir(root: Path, name: str) -> Path:
    path = root / name
    path.mkdir(parents=True, exist_ok=True)
    return path


def test_registry_classifies_placeholder_manifest_contract_and_runtime_states(scratch_dir: Path) -> None:
    _module_dir(scratch_dir, "01 - Optimizer")
    missing_manifest = _module_dir(scratch_dir, "02 - Interpreter")
    (missing_manifest / "README.md").write_text("placeholder", encoding="utf-8")
    module = _module_dir(scratch_dir, "03 - Validator")
    (module / "runtime" / "python").mkdir(parents=True)
    (module / "runtime" / "python" / "python.exe").write_text("", encoding="utf-8")
    (module / "module-manifest.json").write_text(json.dumps({"module_key": "validator", "display_name": "Validator"}), encoding="utf-8")
    broken = _module_dir(scratch_dir, "04 - Normalizer")
    (broken / "module-manifest.json").write_text(json.dumps({"module_key": "normalizer", "display_name": "Normalizer"}), encoding="utf-8")
    (broken / "normalizer_vision" / "edit_contract").mkdir(parents=True)
    ready = _module_dir(scratch_dir, "05 - Corpus Builder")
    (ready / "module-manifest.json").write_text(json.dumps({"module_key": "corpus_builder", "display_name": "Corpus Builder"}), encoding="utf-8")
    contract = ready / "corpus_builder" / "edit_contract"
    contract.mkdir(parents=True)
    for name in ("__init__", "__main__", "describe_surfaces", "read_surface", "validate_surface", "write_surface"):
        (contract / f"{name}.py").write_text("# marker\n", encoding="utf-8")

    snapshot = discover_registry(scratch_dir)
    states = {entry.slot_name: entry for entry in snapshot.entries}
    assert states["01 - Optimizer"].readiness == "placeholder_module"
    assert states["02 - Interpreter"].readiness == "missing_manifest"
    assert states["03 - Validator"].readiness == "missing_edit_contract"
    assert "runtime_unavailable" not in states["03 - Validator"].blockers
    assert states["04 - Normalizer"].readiness == "contract_error"
    assert "runtime_unavailable" in states["04 - Normalizer"].blockers
    assert states["05 - Corpus Builder"].readiness == "ready"


def test_registry_preflight_demotes_bootstrap_failures_to_contract_error(scratch_dir: Path, monkeypatch) -> None:
    ready = _module_dir(scratch_dir, "01 - Optimizer")
    (ready / "runtime" / "python").mkdir(parents=True)
    (ready / "runtime" / "python" / "python.exe").write_text("", encoding="utf-8")
    (ready / "module-manifest.json").write_text(json.dumps({"module_key": "optimizer", "display_name": "Optimizer"}), encoding="utf-8")
    contract = ready / "ingestion_layer_vision" / "edit_contract"
    contract.mkdir(parents=True)
    for name in ("__init__", "__main__", "describe_surfaces", "read_surface", "validate_surface", "write_surface"):
        (contract / f"{name}.py").write_text("# marker\n", encoding="utf-8")

    monkeypatch.setattr(workflow, "probe_contract", lambda module_root, contract_path, state_root: "RuntimeError: boom")

    snapshot = discover_registry(scratch_dir, state_root=scratch_dir / "state")
    entry = {item.slot_name: item for item in snapshot.entries}["01 - Optimizer"]

    assert entry.readiness == "contract_error"
    assert "contract_error" in entry.blockers
    assert entry.diagnostic == "RuntimeError: boom"


def test_registry_prefers_source_contract_over_hidden_staging_copy(scratch_dir: Path) -> None:
    module = _module_dir(scratch_dir, "02 - Interpreter")
    (module / "runtime" / "python").mkdir(parents=True)
    (module / "runtime" / "python" / "python.exe").write_text("", encoding="utf-8")
    (module / "module-manifest.json").write_text(
        json.dumps({"module_key": "interpreter", "display_name": "Interpreter", "launcher_module": "llm_interpreter"}),
        encoding="utf-8",
    )
    source_contract = module / "llm_interpreter" / "edit_contract"
    staging_contract = module / ".tmp-install" / "app" / "llm_interpreter" / "edit_contract"
    for contract in (source_contract, staging_contract):
        contract.mkdir(parents=True)
        for name in ("__init__", "__main__", "describe_surfaces", "read_surface", "validate_surface", "write_surface"):
            (contract / f"{name}.py").write_text("# marker\n", encoding="utf-8")

    snapshot = discover_registry(scratch_dir)
    entry = {item.slot_name: item for item in snapshot.entries}["02 - Interpreter"]

    assert entry.readiness == "ready"
    assert entry.edit_contract_path == str(source_contract)

def test_real_pipeline_marks_interpreter_ready(tmp_path: Path) -> None:
    snapshot = discover_registry(PIPELINE_ROOT, state_root=tmp_path / "state")
    entries = {entry.module_key: entry for entry in snapshot.entries}
    interpreter = entries["interpreter"]
    mcp_server = entries["mcp_server"]

    assert interpreter.readiness == "ready"
    assert interpreter.blockers == ()
    assert interpreter.edit_contract_path.endswith("llm_interpreter\\edit_contract")
    assert mcp_server.readiness == "ready"
    assert mcp_server.blockers == ()
    assert mcp_server.edit_contract_path.endswith("mcp_server\\edit_contract")


def test_registry_ignores_broken_dev_test_temp_subtrees(scratch_dir: Path, monkeypatch) -> None:
    module = _module_dir(scratch_dir, "02 - Interpreter")
    (module / "runtime" / "python").mkdir(parents=True)
    (module / "runtime" / "python" / "python.exe").write_text("", encoding="utf-8")
    (module / "module-manifest.json").write_text(
        json.dumps({"module_key": "interpreter", "display_name": "Interpreter"}),
        encoding="utf-8",
    )
    source_contract = module / "llm_interpreter" / "edit_contract"
    source_contract.mkdir(parents=True)
    for name in ("__init__", "__main__", "describe_surfaces", "read_surface", "validate_surface", "write_surface"):
        (source_contract / f"{name}.py").write_text("# marker\n", encoding="utf-8")
    broken_dev_tests = module / "dev-tests"
    broken_dev_tests.mkdir(parents=True)

    real_scandir = policy.os.scandir

    def fake_scandir(path):
        candidate = Path(path)
        if candidate == broken_dev_tests:
            raise FileNotFoundError("ephemeral dev-test subtree vanished")
        return real_scandir(path)

    monkeypatch.setattr(policy.os, "scandir", fake_scandir)

    snapshot = discover_registry(scratch_dir)
    entry = {item.slot_name: item for item in snapshot.entries}["02 - Interpreter"]

    assert entry.readiness == "ready"
    assert entry.edit_contract_path == str(source_contract)


def test_registry_does_not_treat_runtime_candidate_directory_as_available(scratch_dir: Path) -> None:
    module = _module_dir(scratch_dir, "02 - Interpreter")
    (module / "runtime" / "python" / "python.exe").mkdir(parents=True)
    (module / "module-manifest.json").write_text(
        json.dumps({"module_key": "interpreter", "display_name": "Interpreter"}),
        encoding="utf-8",
    )

    snapshot = discover_registry(scratch_dir)
    entry = {item.slot_name: item for item in snapshot.entries}["02 - Interpreter"]

    assert entry.runtime_available is False
    assert "runtime_unavailable" in entry.blockers


def test_registry_reports_malformed_manifest_distinctly(scratch_dir: Path) -> None:
    module = _module_dir(scratch_dir, "03 - Validator")
    (module / "runtime" / "python").mkdir(parents=True)
    (module / "runtime" / "python" / "python.exe").write_text("", encoding="utf-8")
    (module / "module-manifest.json").write_text("{not json", encoding="utf-8")

    snapshot = discover_registry(scratch_dir)
    entry = {item.slot_name: item for item in snapshot.entries}["03 - Validator"]

    assert entry.manifest_present is True
    assert entry.readiness == "manifest_error"
    assert "manifest_error" in entry.blockers
    assert entry.diagnostic

