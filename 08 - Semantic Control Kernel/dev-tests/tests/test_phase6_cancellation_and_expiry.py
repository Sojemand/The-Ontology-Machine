from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from semantic_control_kernel.repository.event_store import MirrorEventStore
from semantic_control_kernel.repository.interaction_store import InteractionRequestStore
from semantic_control_kernel.repository.paths import StatePaths
from semantic_control_kernel.repository.run_store import WorkflowRunStore
from semantic_control_kernel.services.kernel_mirror_event_service import KernelMirrorEventService
from semantic_control_kernel.services.user_interaction_service import KernelUserInteractionService
from semantic_control_kernel.testing.fakes.fake_client_frontend_sink import FakeClientFrontendSink
from semantic_control_kernel.types.enums import InteractionResponseStatus
from semantic_control_kernel.types.events import UserInteractionResponse
from semantic_control_kernel.validation.contract_validation import KernelContractError


TARGET = {"target_hash": "tgt_phase6", "artifact_root_path_hash": "art_phase6"}
SNAPSHOT = {"state_snapshot_id": "ss_phase6"}


def _service(tmp_path: Path):
    paths = StatePaths.from_state_root(tmp_path / "state")
    service = KernelUserInteractionService(
        interaction_store=InteractionRequestStore(paths),
        mirror_event_service=KernelMirrorEventService(MirrorEventStore(paths)),
        event_sink=FakeClientFrontendSink(),
    )
    return service, paths


def _open_request(service: KernelUserInteractionService, interaction_function: str = "name_database"):
    target_identity = dict(TARGET)
    if interaction_function == "use_custom_database_path":
        target_identity["database_path_hash"] = "db_phase6"
    if interaction_function == "choose_artifact_root_folder":
        target_identity["artifact_root_path_hash"] = TARGET["artifact_root_path_hash"]
    return service.request_interaction(
        interaction_function=interaction_function,
        workflow_run_id="wr_phase6",
        function_or_route="phase6_route",
        target_identity=target_identity,
        state_snapshot_identity=SNAPSHOT,
        user_visible_title="Phase 6 Dialog",
        user_visible_summary="Phase 6 dialog summary.",
    ).request


def _response(request, status: str, **updates) -> UserInteractionResponse:
    payload = {
        "host_surface_identity": "client_frontend_http_pipeline_session",
        "interaction_request_id": request.payload["interaction_request_id"],
        "interaction_response_id": f"irs_{status}_{request.payload['interaction_request_id']}",
        "response_status": status,
        "schema_version": UserInteractionResponse.SCHEMA_VERSION,
        "state_snapshot_identity": request.payload["state_snapshot_identity"],
        "submitted_at": "2026-05-05T00:00:00Z",
        "target_identity": request.payload["target_identity"],
    }
    payload.update(updates)
    return UserInteractionResponse.from_dict(payload)


@pytest.mark.parametrize(
    "status,reason",
    [
        (InteractionResponseStatus.CLOSED.value, "user_closed_dialog"),
        (InteractionResponseStatus.CANCELLED.value, "user_cancelled"),
        (InteractionResponseStatus.EXPIRED.value, "timeout"),
        (InteractionResponseStatus.SUPERSEDED.value, "superseded_workflow_run"),
        (InteractionResponseStatus.REJECTED_STALE.value, "target_identity_changed"),
    ],
)
def test_terminal_responses_move_to_history_without_consuming_values(tmp_path: Path, status: str, reason: str) -> None:
    service, paths = _service(tmp_path)
    request = _open_request(service)

    result = service.submit_response(_response(request, status, cancellation_reason=reason))
    history = json.loads((paths.pending_interactions_history_dir / f"{request.payload['interaction_request_id']}.json").read_text(encoding="utf-8"))

    assert result.accepted is True
    assert result.consumed_value is False
    assert history["status"] == status
    assert not (paths.pending_interactions_active_dir / f"{request.payload['interaction_request_id']}.json").exists()


def test_expired_submitted_response_emits_recovery_state_and_consumes_no_value(tmp_path: Path) -> None:
    service, paths = _service(tmp_path)
    request = _open_request(service, "use_custom_database_path")
    expires_at = datetime.fromisoformat(request.payload["expiration_policy"]["expires_at"].replace("Z", "+00:00"))

    result = service.submit_response(
        _response(request, InteractionResponseStatus.SUBMITTED.value, path_value="C:/tmp/database.db"),
        now_utc=expires_at + timedelta(seconds=1),
    )
    history = json.loads((paths.pending_interactions_history_dir / f"{request.payload['interaction_request_id']}.json").read_text(encoding="utf-8"))

    assert result.accepted is False
    assert result.consumed_value is False
    assert result.recovery_state == "expired_pending_interaction"
    assert history["status"] == "expired"
    assert history["stale_response_refs"][0]["recovery_state"] == "expired_pending_interaction"


def test_changed_target_response_is_rejected_stale_and_value_is_not_consumed(tmp_path: Path) -> None:
    service, paths = _service(tmp_path)
    request = _open_request(service, "use_custom_database_path")
    stale_response = _response(
        request,
        InteractionResponseStatus.SUBMITTED.value,
        path_value="C:/tmp/database.db",
        target_identity={"target_hash": "different"},
    )

    result = service.submit_response(stale_response, now_utc=datetime.now(timezone.utc))
    history = json.loads((paths.pending_interactions_history_dir / f"{request.payload['interaction_request_id']}.json").read_text(encoding="utf-8"))

    assert result.accepted is False
    assert result.consumed_value is False
    assert result.recovery_state == "target_identity_changed"
    assert history["status"] == "rejected_stale"
    assert history["stale_response_refs"][0]["interaction_response_id"] == stale_response.payload["interaction_response_id"]


def test_submitted_response_for_completed_workflow_is_superseded_and_not_consumed(tmp_path: Path) -> None:
    paths = StatePaths.from_state_root(tmp_path / "state")
    run_store = WorkflowRunStore(paths)
    run = run_store.create_run("phase6_route", {"target_hash": "tgt_phase6", "database_path_hash": "db_phase6"}, "phase6_test")
    service = KernelUserInteractionService(
        interaction_store=InteractionRequestStore(paths),
        mirror_event_service=KernelMirrorEventService(MirrorEventStore(paths)),
        event_sink=FakeClientFrontendSink(),
        workflow_run_store=run_store,
    )
    request = service.request_interaction(
        interaction_function="use_custom_database_path",
        workflow_run_id=run.workflow_run_id,
        function_or_route="phase6_route",
        target_identity={"target_hash": "tgt_phase6", "database_path_hash": "db_phase6"},
        state_snapshot_identity=SNAPSHOT,
        user_visible_title="Phase 6 Dialog",
        user_visible_summary="Phase 6 dialog summary.",
    ).request
    run_store.mark_run_completed(run.workflow_run_id, "op_phase6_complete")

    result = service.submit_response(
        _response(
            request,
            InteractionResponseStatus.SUBMITTED.value,
            path_value="C:/tmp/database.db",
        )
    )
    history = json.loads((paths.pending_interactions_history_dir / f"{request.payload['interaction_request_id']}.json").read_text(encoding="utf-8"))

    assert result.accepted is False
    assert result.consumed_value is False
    assert result.terminal_status == "superseded"
    assert result.recovery_state == "superseded_workflow_run"
    assert history["status"] == "superseded"
    assert history["stale_response_refs"][0]["recovery_state"] == "superseded_workflow_run"


def test_submitted_response_must_match_the_request_value_mapping(tmp_path: Path) -> None:
    service, paths = _service(tmp_path)
    request = _open_request(service, "choose_artifact_root_folder")
    active_path = paths.pending_interactions_active_dir / f"{request.payload['interaction_request_id']}.json"

    with pytest.raises(KernelContractError):
        service.submit_response(
            _response(
                request,
                InteractionResponseStatus.SUBMITTED.value,
                choice_id="current_active_database",
            )
        )

    assert active_path.exists()
