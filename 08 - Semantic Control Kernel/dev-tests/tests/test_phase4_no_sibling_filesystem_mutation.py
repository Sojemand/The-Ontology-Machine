from __future__ import annotations

import sys
from pathlib import Path

from semantic_control_kernel.adapters.invocation import AdapterInvocation, OwnerBoundary, invoke_owner_contract


MODULE_ROOT = Path(__file__).resolve().parents[2]
FAKE_OWNER_ROOT = MODULE_ROOT / "dev-tests" / "fixtures" / "adapters"


def test_adapter_invocation_writes_only_under_kernel_state_root(tmp_path: Path) -> None:
    state_root = tmp_path / "kernel_state"
    sibling_roots = [
        tmp_path / "00 - Orchestrator",
        tmp_path / "04 - Normalizer",
        tmp_path / "05 - Corpus Builder",
    ]
    for root in sibling_roots:
        root.mkdir(parents=True)

    target_database = sibling_roots[-1] / "Corpus" / "corpus.db"
    boundary = OwnerBoundary(
        owner_module="fake_corpus_builder",
        owner_module_root=FAKE_OWNER_ROOT,
        owner_contract_module="fakes.fake_owner",
        owner_action="create_empty_corpus_db",
        adapter_name="CorpusAdapter",
        method_name="create_empty_database",
        capability_status="implemented_in_pipeline",
        timeout_seconds=5,
        mutating=True,
        required_target_proof_fields=("database_path|database_path_hash",),
        python_executable=Path(sys.executable),
    )

    result = invoke_owner_contract(
        AdapterInvocation(
            state_root=state_root,
            kernel_function="create_empty_database",
            boundary=boundary,
            request_payload={
                "corpus_db_path": str(target_database),
                "mode": "success",
                "target_identity_proof": {"database_path_hash": "database_hash_123"},
            },
            target_identity={"database_path_hash": "database_hash_123"},
        )
    )

    assert result.status == "ok"
    assert (state_root / "adapter_calls" / result.adapter_call_id / "request.json").exists()
    for root in sibling_roots:
        assert not any(path.is_file() for path in root.rglob("*"))


def test_owner_target_paths_are_persisted_as_request_data_not_adapter_created_files(tmp_path: Path) -> None:
    state_root = tmp_path / "kernel_state"
    result = invoke_owner_contract(
        AdapterInvocation(
            state_root=state_root,
            kernel_function="create_empty_database",
            boundary=OwnerBoundary(
                owner_module="fake_corpus_builder",
                owner_module_root=FAKE_OWNER_ROOT,
                owner_contract_module="fakes.fake_owner",
                owner_action="create_empty_corpus_db",
                adapter_name="CorpusAdapter",
                method_name="create_empty_database",
                capability_status="implemented_in_pipeline",
                timeout_seconds=5,
                mutating=True,
                required_target_proof_fields=("database_path|database_path_hash",),
                python_executable=Path(sys.executable),
            ),
            request_payload={
                "corpus_db_path": str(tmp_path / "05 - Corpus Builder" / "Corpus" / "corpus.db"),
                "mode": "success",
                "target_identity_proof": {"database_path_hash": "database_hash_123"},
            },
            target_identity={"database_path_hash": "database_hash_123"},
        )
    )

    call_dir = state_root / "adapter_calls" / result.adapter_call_id
    written_files = {path.relative_to(state_root).as_posix() for path in state_root.rglob("*") if path.is_file()}

    assert result.status == "ok"
    expected_adapter_files = {
        f"adapter_calls/{result.adapter_call_id}/diagnostics.json",
        f"adapter_calls/{result.adapter_call_id}/owner_response.raw.json",
        f"adapter_calls/{result.adapter_call_id}/request.json",
        f"adapter_calls/{result.adapter_call_id}/response.json",
        f"adapter_calls/{result.adapter_call_id}/result.json",
        f"adapter_calls/{result.adapter_call_id}/stderr.txt",
        f"adapter_calls/{result.adapter_call_id}/stdout.txt",
    }
    expected_layout_files = {"README.md", "state_root_manifest.json", "support/index.json"}
    assert written_files == expected_adapter_files | expected_layout_files
    assert call_dir.exists()
