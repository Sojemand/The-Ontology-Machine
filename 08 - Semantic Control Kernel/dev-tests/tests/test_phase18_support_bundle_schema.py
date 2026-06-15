from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import pytest

from semantic_control_kernel.repository.paths import StatePaths
from semantic_control_kernel.repository.recovery_events import RecoveryEventStore
from semantic_control_kernel.repository.run_store import WorkflowRunStore
from semantic_control_kernel.repository.support_bundles import SupportBundleStore
from semantic_control_kernel.surface.recovery_tools import RecoveryToolSurface
from semantic_control_kernel.validation.recovery_validation import validate_support_bundle_ref


DRIFT_PREFLIGHT = {"status": "drift_preflight: clear", "details": []}


@dataclass
class _AuthResult:
    allowed: bool
    reason: str
    recovery_event: dict[str, object]
    recovery_option: dict[str, object]


class _AuthorizationStub:
    def __init__(self, support_bundle_ref: dict[str, object]) -> None:
        self._support_bundle_ref = support_bundle_ref

    def authorize(self, **_: object) -> _AuthResult:
        return _AuthResult(
            allowed=True,
            reason="",
            recovery_event={"support_bundle_ref": self._support_bundle_ref},
            recovery_option={},
        )


def test_drift_preflight_recorded_for_phase18() -> None:
    assert DRIFT_PREFLIGHT["status"] == "drift_preflight: clear"


def test_support_bundle_manifest_files_index_and_open_surface(tmp_path: Path) -> None:
    paths = StatePaths.from_state_root(tmp_path / "state")
    run = WorkflowRunStore(paths).create_run(
        "pipeline_run",
        {"target_hash": "target_phase18"},
        "phase18_test",
    )
    store = SupportBundleStore(paths)
    ref = store.write_support_bundle(
        category="support_only_unrecoverable",
        workflow_run_id=run.workflow_run_id,
        recovery_event_id="rev_phase18",
        summary="Operator-safe support bundle for schema verification.",
        workflow_tool=run.workflow_tool,
        included_refs=["events/progress/sample.json"],
        created_by="phase18_test",
    )

    bundle_id = ref.payload["support_bundle_id"]
    bundle_dir = paths.support_bundles_dir / bundle_id
    manifest_path = bundle_dir / "support_bundle_manifest.json"
    included_refs_path = bundle_dir / "included_refs.json"
    trace_links_path = bundle_dir / "trace_links.json"
    redaction_report_path = bundle_dir / "redaction_report.json"
    persisted_redaction_report_path = paths.debug_redaction_reports_dir / f"{bundle_id}.json"

    assert manifest_path.is_file()
    assert (bundle_dir / "safe_summary.md").is_file()
    assert included_refs_path.is_file()
    assert trace_links_path.is_file()
    assert redaction_report_path.is_file()
    assert persisted_redaction_report_path.is_file()

    manifest = store.get_manifest(bundle_id)
    assert manifest["schema_version"] == "repository.support_bundle_manifest.v1"
    assert manifest["trace_id"].startswith("trc_")
    assert manifest["safe_summary"] == "Operator-safe support bundle for schema verification."
    assert manifest["redaction_report_ref"] == f"debug/redaction_reports/{bundle_id}.json"

    index_payload = json.loads(paths.support_index_path.read_text(encoding="utf-8"))
    assert [item["support_bundle_id"] for item in index_payload["support_bundle_refs"]] == [bundle_id]

    surface = RecoveryToolSurface(
        authorization=_AuthorizationStub(ref.to_dict()),
        recovery_store=RecoveryEventStore(paths),
        support_bundle_store=store,
    )
    output = surface.call(
        "kernel_open_support_bundle",
        {
            "schema_version": "kernel.phase18.tool_contract.v1",
            "mirror_event_id": "mev_phase18",
            "recovery_event_id": "rev_phase18",
            "recovery_id": "rcv_phase18",
            "support_bundle_id": bundle_id,
            "tool_call_nonce": "nonce_phase18",
        },
    )
    assert output["support_bundle_ref"]["support_bundle_id"] == bundle_id
    validate_support_bundle_ref(output["support_bundle_ref"])
    assert output["safe_summary"] == manifest["safe_summary"]
    assert output["support_bundle_ref"]["support_bundle_path"].endswith("support_bundle_manifest.json")
    assert output["manifest_ref"].endswith("support_bundle_manifest.json")
    assert output["included_refs_ref"].endswith("included_refs.json")
    assert output["redaction_report_ref"].endswith("redaction_report.json")

    with pytest.raises(Exception):
        store.write_support_bundle(
            category="support_only_unrecoverable",
            workflow_run_id=run.workflow_run_id,
            recovery_event_id="rev_phase18",
            summary="duplicate",
            workflow_tool=run.workflow_tool,
            support_bundle_id=bundle_id,
        )


def test_support_bundle_rejects_raw_or_escaping_included_refs(tmp_path: Path) -> None:
    paths = StatePaths.from_state_root(tmp_path / "state")
    run = WorkflowRunStore(paths).create_run(
        "pipeline_run",
        {"target_hash": "phase18_ref_guard"},
        "phase18_ref_guard",
    )
    store = SupportBundleStore(paths)

    state_ref = paths.state_root / "events" / "progress" / "safe.json"
    ref = store.write_support_bundle(
        category="support_only_unrecoverable",
        workflow_run_id=run.workflow_run_id,
        recovery_event_id="rev_ref_guard",
        summary="Ref guard accepts module-state refs.",
        workflow_tool=run.workflow_tool,
        included_refs=[str(state_ref), {"prompt_snapshot_ref": "sa/ana/a/1/prompt.json"}],
    )
    manifest = store.get_manifest(ref.payload["support_bundle_id"])
    assert manifest["included_refs"][0] == "events/progress/safe.json"
    assert manifest["included_refs"][1]["prompt_snapshot_ref"].endswith("prompt.json")

    unsafe_refs = [
        "C:\\Users\\Norma\\Desktop\\raw_provider_response.json",
        "../outside-state.json",
        {"raw_provider_response": {"output_text": "full raw provider output"}},
        {"prompt": "full prompt body"},
        {"diagnostic_ref": "sk-test-included-ref-secret"},
    ]
    for unsafe_ref in unsafe_refs:
        with pytest.raises(ValueError):
            store.write_support_bundle(
                category="support_only_unrecoverable",
                workflow_run_id=run.workflow_run_id,
                recovery_event_id="rev_ref_guard",
                summary="Ref guard rejects unsafe included refs.",
                workflow_tool=run.workflow_tool,
                included_refs=[unsafe_ref],
            )
