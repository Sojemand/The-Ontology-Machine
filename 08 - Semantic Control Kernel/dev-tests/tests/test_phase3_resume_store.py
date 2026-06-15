from __future__ import annotations

import json
from pathlib import Path

import pytest

from semantic_control_kernel.repository.confirmation_store import ConfirmationRequestStore
from semantic_control_kernel.repository.errors import TargetIdentityMismatchError
from semantic_control_kernel.repository.interaction_store import InteractionRequestStore
from semantic_control_kernel.repository.paths import StatePaths
from semantic_control_kernel.repository.resume_store import WorkflowResumeStore
from semantic_control_kernel.types.events import UserInteractionRequest, UserInteractionResponse
from semantic_control_kernel.types.receipts import ConfirmationReceipt, ConfirmationRequest
from semantic_control_kernel.types.state import WorkflowResumeState


MODULE_ROOT = Path(__file__).resolve().parents[2]
FIXTURES = MODULE_ROOT / "dev-tests" / "fixtures" / "contracts"


def _fixture(schema_version: str) -> dict:
    return json.loads((FIXTURES / f"{schema_version.replace('.', '__')}.valid.json").read_text(encoding="utf-8"))


def test_resume_store_persists_and_reloads_workflow_resume_state(tmp_path: Path) -> None:
    store = WorkflowResumeStore(StatePaths.from_state_root(tmp_path / "state"))
    resume = WorkflowResumeState.from_dict(_fixture("kernel.workflow_resume_state.v1"))

    store.put_resume_state(resume)

    assert store.get_resume_state("workflow_run_id_example").to_dict() == resume.to_dict()


def test_pending_confirmation_and_interaction_link_to_resume_state(tmp_path: Path) -> None:
    paths = StatePaths.from_state_root(tmp_path / "state")
    resume_store = WorkflowResumeStore(paths)
    confirmation_store = ConfirmationRequestStore(paths)
    interaction_store = InteractionRequestStore(paths)
    resume_payload = _fixture("kernel.workflow_resume_state.v1")
    resume_payload["pending_confirmation_refs"] = [{"confirmation_request_id": "confirmation_request_id_example"}]
    resume_payload["pending_interaction_refs"] = [{"interaction_request_id": "interaction_request_id_example"}]

    resume_store.put_resume_state(WorkflowResumeState.from_dict(resume_payload))
    confirmation_store.put_pending_request(ConfirmationRequest.from_dict(_fixture("kernel.confirmation_request.v1")))
    interaction_store.put_pending_interaction(UserInteractionRequest.from_dict(_fixture("kernel.user_interaction_request.v1")))

    assert confirmation_store.list_pending_for_workflow("workflow_run_id_example")
    assert interaction_store.list_pending_interactions_for_workflow("workflow_run_id_example")


def test_pending_confirmation_rejects_stale_target_or_snapshot(tmp_path: Path) -> None:
    paths = StatePaths.from_state_root(tmp_path / "state")
    store = ConfirmationRequestStore(paths)
    store.put_pending_request(ConfirmationRequest.from_dict(_fixture("kernel.confirmation_request.v1")))
    stale = _fixture("kernel.confirmation_receipt.v1")
    stale["confirmed_target_identity"]["target_hash"] = "tgt_stale"

    with pytest.raises(TargetIdentityMismatchError):
        store.consume_confirmation_receipt(ConfirmationReceipt.from_dict(stale))


def test_pending_interaction_rejects_stale_target_or_snapshot(tmp_path: Path) -> None:
    paths = StatePaths.from_state_root(tmp_path / "state")
    store = InteractionRequestStore(paths)
    store.put_pending_interaction(UserInteractionRequest.from_dict(_fixture("kernel.user_interaction_request.v1")))
    stale = _fixture("kernel.user_interaction_response.v1")
    stale["state_snapshot_identity"]["state_snapshot_id"] = "ss_stale"

    with pytest.raises(TargetIdentityMismatchError):
        store.submit_interaction_response(UserInteractionResponse.from_dict(stale))


def test_pending_confirmation_and_interaction_can_expire(tmp_path: Path) -> None:
    paths = StatePaths.from_state_root(tmp_path / "state")
    confirmation_store = ConfirmationRequestStore(paths)
    interaction_store = InteractionRequestStore(paths)
    confirmation_store.put_pending_request(ConfirmationRequest.from_dict(_fixture("kernel.confirmation_request.v1")))
    interaction_store.put_pending_interaction(UserInteractionRequest.from_dict(_fixture("kernel.user_interaction_request.v1")))

    confirmation_store.expire_pending_request("confirmation_request_id_example", "timeout")
    interaction_store.expire_interaction("interaction_request_id_example", "timeout")

    assert not list(paths.pending_confirmations_active_dir.glob("*.json"))
    assert not list(paths.pending_interactions_active_dir.glob("*.json"))
