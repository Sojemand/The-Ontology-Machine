from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

from semantic_control_kernel.adapters.invocation import AdapterInvocation, OwnerBoundary, invoke_owner_contract
from semantic_control_kernel.repository import atomic_json as atomic_module

MODULE_ROOT = Path(__file__).resolve().parents[2]
FAKE_OWNER_ROOT = MODULE_ROOT / "dev-tests" / "fixtures" / "adapters"


def test_adapter_owner_response_is_staged_then_atomically_published(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state_root = tmp_path / "state"
    replace_calls: list[tuple[Path, Path]] = []
    original_replace = os.replace

    def capture_replace(src, dst):
        replace_calls.append((Path(src), Path(dst)))
        return original_replace(src, dst)

    monkeypatch.setattr(atomic_module.os, "replace", capture_replace)

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
                "corpus_db_path": str(tmp_path / "Corpus" / "corpus.db"),
                "mode": "success",
                "target_identity_proof": {"database_path_hash": "database_hash_123"},
            },
            target_identity={"database_path_hash": "database_hash_123"},
        )
    )

    raw_response = state_root / "adapter_calls" / result.adapter_call_id / "owner_response.raw.json"
    assert raw_response.exists()
    assert not list((state_root / ".tmp").glob(f".{result.adapter_call_id}.owner_response.raw.json.tmp"))
    assert any(dst == raw_response and src.parent == state_root / ".tmp" for src, dst in replace_calls)
