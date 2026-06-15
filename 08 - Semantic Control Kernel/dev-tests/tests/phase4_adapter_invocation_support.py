from __future__ import annotations

from pathlib import Path
import sys

from semantic_control_kernel.adapters.invocation import AdapterInvocation, OwnerBoundary, invoke_owner_contract
from semantic_control_kernel.repository.paths import StatePaths


MODULE_ROOT = Path(__file__).resolve().parents[2]
FAKE_OWNER_ROOT = MODULE_ROOT / "dev-tests" / "fixtures" / "adapters"


def _invoke(
    tmp_path: Path,
    mode: str,
    *,
    timeout_seconds: float | None = 5.0,
    extra_payload: dict[str, object] | None = None,
):
    state_root = tmp_path / "state"
    boundary = OwnerBoundary(
        owner_module="fake_corpus_builder",
        owner_module_root=FAKE_OWNER_ROOT,
        owner_contract_module="fakes.fake_owner",
        owner_action="create_empty_corpus_db",
        adapter_name="CorpusAdapter",
        method_name="create_empty_database",
        capability_status="implemented_in_pipeline",
        timeout_seconds=timeout_seconds,
        mutating=True,
        required_target_proof_fields=("database_path|database_path_hash",),
        python_executable=Path(sys.executable),
    )
    payload = {
        "corpus_db_path": str(tmp_path / "sibling" / "corpus.db"),
        "mode": mode,
        "target_identity_proof": {"database_path_hash": "database_hash_123"},
    }
    if extra_payload:
        payload.update(extra_payload)
    result = invoke_owner_contract(
        AdapterInvocation(
            state_root=state_root,
            kernel_function="create_empty_database",
            boundary=boundary,
            request_payload=payload,
            target_identity={"database_path_hash": "database_hash_123"},
            state_snapshot_identity={"state_snapshot_id": "ss_test"},
            workflow_run_id="wr_test",
        )
    )
    return result, StatePaths.from_state_root(state_root).adapter_calls_dir / result.adapter_call_id, payload
