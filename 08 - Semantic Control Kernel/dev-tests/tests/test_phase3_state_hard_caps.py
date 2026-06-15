from __future__ import annotations

import json
from pathlib import Path

from semantic_control_kernel.repository.hard_cap import (
    DEBUG_LLM_RUN_DIR_HARD_CAP,
    MIRROR_EVENT_HARD_CAP,
    PROGRESS_FILES_PER_WORKFLOW_HARD_CAP,
    PROGRESS_WORKFLOW_DIR_HARD_CAP,
    RAW_ADAPTER_CALL_DIR_HARD_CAP,
    RECEIPT_OPERATION_HARD_CAP,
    SUPPORT_BUNDLE_HARD_CAP,
    TRACE_WORKFLOW_DIR_HARD_CAP,
    WORKFLOW_HISTORY_HARD_CAP,
    KernelStateHardCapService,
)
from semantic_control_kernel.repository.paths import StatePaths, utc_iso
from semantic_control_kernel.repository.receipt_store import ReceiptStore
from semantic_control_kernel.repository.run_store import WorkflowRunStore
from semantic_control_kernel.repository.support_bundles import SupportBundleStore
from semantic_control_kernel.repository.trace_store import TRACE_LINKS_PER_WORKFLOW_HARD_CAP, TraceLinkStore
from semantic_control_kernel.types.receipts import OperationReceipt

MODULE_ROOT = Path(__file__).resolve().parents[2]
FIXTURES = MODULE_ROOT / "dev-tests" / "fixtures" / "contracts"


def _fixture(schema_version: str) -> dict:
    return json.loads((FIXTURES / f"{schema_version.replace('.', '__')}.valid.json").read_text(encoding="utf-8"))


def test_support_bundle_store_caps_bundle_count_and_updates_index(tmp_path: Path) -> None:
    paths = StatePaths.from_state_root(tmp_path / "state")
    run = WorkflowRunStore(paths).create_run(
        "pipeline_run",
        {"target_hash": "cap_bundle_target"},
        "cap_bundle_test",
    )
    store = SupportBundleStore(paths)

    created_ids: list[str] = []
    for index in range(SUPPORT_BUNDLE_HARD_CAP + 3):
        bundle_id = f"spt_cap_{index:04d}"
        created_ids.append(bundle_id)
        store.write_support_bundle(
            category="support_only_unrecoverable",
            workflow_run_id=run.workflow_run_id,
            recovery_event_id=f"rev_cap_{index:04d}",
            summary=f"support bundle {index}",
            workflow_tool=run.workflow_tool,
            support_bundle_id=bundle_id,
        )

    manifests = store.list_bundle_manifests()
    index_payload = json.loads(paths.support_index_path.read_text(encoding="utf-8"))

    assert len(manifests) == SUPPORT_BUNDLE_HARD_CAP
    assert len(index_payload["support_bundle_refs"]) == SUPPORT_BUNDLE_HARD_CAP
    assert created_ids[0] not in {manifest["support_bundle_id"] for manifest in manifests}
    assert created_ids[-1] in {manifest["support_bundle_id"] for manifest in manifests}


def test_trace_link_store_caps_links_per_workflow(tmp_path: Path) -> None:
    paths = StatePaths.from_state_root(tmp_path / "state")
    store = TraceLinkStore(paths)
    store.create_trace_context(
        workflow_run_id="wr_trace_cap",
        workflow_tool="pipeline_run",
        started_by="trace_cap_test",
        root_target_identity_ref={"target_hash": "trace_cap_target"},
    )

    for index in range(TRACE_LINKS_PER_WORKFLOW_HARD_CAP + 5):
        store.append_link(
            workflow_run_id="wr_trace_cap",
            object_kind="progress_event",
            object_id=f"obj_{index:04d}",
            object_ref=f"events/progress/{index:04d}.json",
        )

    links = store.list_links_for_workflow("wr_trace_cap")

    assert len(links) == TRACE_LINKS_PER_WORKFLOW_HARD_CAP
    assert links[0]["object_id"] == "obj_0005"
    assert links[-1]["object_id"] == f"obj_{TRACE_LINKS_PER_WORKFLOW_HARD_CAP + 4:04d}"


def test_global_hard_cap_service_prunes_workflow_history_progress_and_raw_adapter_calls(tmp_path: Path) -> None:
    paths = StatePaths.from_state_root(tmp_path / "state")
    service = KernelStateHardCapService(paths)

    for index in range(WORKFLOW_HISTORY_HARD_CAP + 4):
        history_path = paths.workflow_runs_history_dir / f"wr_hist_{index:04d}.json"
        history_path.write_text("{}", encoding="utf-8")

    big_progress_dir = paths.events_progress_dir / "wr_progress_big"
    big_progress_dir.mkdir(parents=True, exist_ok=True)
    for index in range(PROGRESS_FILES_PER_WORKFLOW_HARD_CAP + 7):
        (big_progress_dir / f"{index:06d}.json").write_text("{}", encoding="utf-8")
    for index in range(PROGRESS_WORKFLOW_DIR_HARD_CAP + 4):
        progress_dir = paths.events_progress_dir / f"wr_progress_{index:04d}"
        progress_dir.mkdir(parents=True, exist_ok=True)
        (progress_dir / "000001.json").write_text("{}", encoding="utf-8")

    for index in range(RAW_ADAPTER_CALL_DIR_HARD_CAP + 4):
        call_dir = paths.adapter_calls_dir / f"adc_cap_{index:04d}"
        call_dir.mkdir(parents=True, exist_ok=True)
        (call_dir / "request.json").write_text("{}", encoding="utf-8")

    for index in range(TRACE_WORKFLOW_DIR_HARD_CAP + 4):
        trace_dir = paths.debug_traces_dir / f"wr_trace_{index:04d}"
        trace_dir.mkdir(parents=True, exist_ok=True)
        (trace_dir / "trace_context.json").write_text("{}", encoding="utf-8")

    for index in range(DEBUG_LLM_RUN_DIR_HARD_CAP + 4):
        llm_dir = paths.debug_llm_attempts_dir / f"analysis_{index:04d}"
        llm_dir.mkdir(parents=True, exist_ok=True)
        (llm_dir / "000001_attempt.json").write_text("{}", encoding="utf-8")

    service.prune_all()

    assert len(list(paths.workflow_runs_history_dir.glob("*.json"))) == WORKFLOW_HISTORY_HARD_CAP
    assert len([path for path in paths.events_progress_dir.iterdir() if path.is_dir()]) == PROGRESS_WORKFLOW_DIR_HARD_CAP
    assert len(list(big_progress_dir.glob("*.json"))) == PROGRESS_FILES_PER_WORKFLOW_HARD_CAP
    assert len([path for path in paths.adapter_calls_dir.iterdir() if path.is_dir()]) == RAW_ADAPTER_CALL_DIR_HARD_CAP
    assert len([path for path in paths.debug_traces_dir.iterdir() if path.is_dir()]) == TRACE_WORKFLOW_DIR_HARD_CAP
    assert len([path for path in paths.debug_llm_attempts_dir.iterdir() if path.is_dir()]) == DEBUG_LLM_RUN_DIR_HARD_CAP


def test_receipt_cap_preserves_receipts_referenced_by_support_bundles(tmp_path: Path) -> None:
    paths = StatePaths.from_state_root(tmp_path / "state")
    run = WorkflowRunStore(paths).create_run(
        "pipeline_run",
        {"target_hash": "receipt_cap_target"},
        "receipt_cap_test",
    )
    support_store = SupportBundleStore(paths)
    support_store.write_support_bundle(
        category="support_only_unrecoverable",
        workflow_run_id=run.workflow_run_id,
        recovery_event_id="rev_receipt_cap",
        summary="bundle protects one operation receipt",
        workflow_tool=run.workflow_tool,
        support_bundle_id="spt_receipt_cap_keep",
        related_receipt_refs=[{"operation_receipt_id": "opr_keep"}],
    )

    receipt_store = ReceiptStore(paths)
    fixture = _fixture("kernel.operation_receipt.v1")
    total = RECEIPT_OPERATION_HARD_CAP + 5
    for index in range(total):
        payload = dict(fixture)
        payload["operation_receipt_id"] = "opr_keep" if index == 0 else f"opr_{index:04d}"
        payload["workflow_run_id"] = f"wr_receipt_{index:04d}"
        payload["target_identity_after"] = {"target_hash": f"target_{index:04d}"}
        payload["created_at"] = utc_iso()
        receipt_store.append_operation_receipt(OperationReceipt.from_dict(payload))

    receipt_paths = sorted(paths.receipts_operations_dir.glob("*.json"))

    assert len(receipt_paths) == RECEIPT_OPERATION_HARD_CAP
    assert (paths.receipts_operations_dir / "opr_keep.json").exists()
    assert not (paths.receipts_operations_dir / "opr_0001.json").exists()
    assert (paths.receipts_operations_dir / f"opr_{total - 1:04d}.json").exists()
