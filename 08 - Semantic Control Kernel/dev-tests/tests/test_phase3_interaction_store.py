from __future__ import annotations

import json
from pathlib import Path

import pytest

from semantic_control_kernel.repository.errors import DuplicateStateObjectError
from semantic_control_kernel.repository.interaction_store import InteractionRequestStore
from semantic_control_kernel.repository.paths import StatePaths
from semantic_control_kernel.types.events import UserInteractionRequest


MODULE_ROOT = Path(__file__).resolve().parents[2]
FIXTURES = MODULE_ROOT / "dev-tests" / "fixtures" / "contracts"


def _request(request_id: str) -> UserInteractionRequest:
    payload = json.loads((FIXTURES / "kernel__user_interaction_request__v1.valid.json").read_text(encoding="utf-8"))
    payload["interaction_request_id"] = request_id
    return UserInteractionRequest.from_dict(payload)


def test_interaction_store_moves_terminal_states_to_history(tmp_path: Path) -> None:
    paths = StatePaths.from_state_root(tmp_path / "state")
    store = InteractionRequestStore(paths)
    transitions = {
        "submitted": lambda request_id: store.submit_interaction(request_id, f"irs_{request_id}"),
        "cancelled": lambda request_id: store.cancel_interaction(request_id, "user cancelled"),
        "closed": lambda request_id: store.close_interaction(request_id, "closed"),
        "expired": lambda request_id: store.expire_interaction(request_id, "expired"),
        "superseded": lambda request_id: store.supersede_interaction(request_id, "wr_new"),
        "rejected_stale": lambda request_id: store.reject_stale_interaction(request_id, "stale"),
    }

    for status, transition in transitions.items():
        request_id = f"irq_{status}"
        store.put_pending_interaction(_request(request_id))
        transition(request_id)
        history_payload = json.loads((paths.pending_interactions_history_dir / f"{request_id}.json").read_text(encoding="utf-8"))
        assert history_payload["status"] == status
        assert not (paths.pending_interactions_active_dir / f"{request_id}.json").exists()


def test_interaction_store_rejects_duplicate_active_request_ids(tmp_path: Path) -> None:
    store = InteractionRequestStore(StatePaths.from_state_root(tmp_path / "state"))
    request = _request("irq_duplicate")
    store.put_pending_interaction(request)

    with pytest.raises(DuplicateStateObjectError):
        store.put_pending_interaction(request)


def test_stale_response_refs_remain_queryable_without_mutating_resume_state(tmp_path: Path) -> None:
    paths = StatePaths.from_state_root(tmp_path / "state")
    store = InteractionRequestStore(paths)
    store.put_pending_interaction(_request("irq_stale"))
    store.reject_stale_interaction("irq_stale", "snapshot mismatch")
    store.record_stale_response_ref("irq_stale", {"state_path": "support/stale_response.json"})

    history_payload = json.loads((paths.pending_interactions_history_dir / "irq_stale.json").read_text(encoding="utf-8"))

    assert history_payload["status"] == "rejected_stale"
    assert history_payload["stale_response_refs"] == [{"state_path": "support/stale_response.json"}]
    assert not list(paths.resume_dir.glob("*.json"))
