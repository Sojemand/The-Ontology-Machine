from __future__ import annotations

from pathlib import Path

from phase12_merge_entry_support import FakeCorpusAdapter, FakeEmbeddingAdapter, FakeSemanticReleaseAdapter, create_artifact_tree, seed_rebuild_release

from semantic_control_kernel.repository.interaction_store import InteractionRequestStore
from semantic_control_kernel.repository.event_store import ProgressEventStore
from semantic_control_kernel.repository.paths import StatePaths
from semantic_control_kernel.repository.receipt_store import ReceiptStore
from semantic_control_kernel.services.agent_tool_workflow_dispatch import dispatch_permanent_workflow_tool
from semantic_control_kernel.surface.client_frontend_bridge import submit_user_interaction_response
from semantic_control_kernel.types.events import UserInteractionResponse
from semantic_control_kernel.workflows.rebuild.entry import RebuildWorkflowRuntime


MODULE_ROOT = Path(__file__).resolve().parents[2]
_RUNTIME_CAPTURE: dict[str, object] = {}


def _state_paths(tmp_path: Path) -> StatePaths:
    return StatePaths(module_root=MODULE_ROOT, state_root=(tmp_path / "state").resolve())


def _runtime_factory(paths: StatePaths) -> RebuildWorkflowRuntime:
    embedding = FakeEmbeddingAdapter()
    _RUNTIME_CAPTURE["embedding_adapter"] = embedding
    return RebuildWorkflowRuntime(
        state_root=paths.state_root,
        corpus_adapter=FakeCorpusAdapter(),
        semantic_release_adapter=FakeSemanticReleaseAdapter(),
        embedding_adapter=embedding,
    )


def _pending(paths: StatePaths, workflow_run_id: str):
    pending = InteractionRequestStore(paths).list_pending_interactions_for_workflow(workflow_run_id)
    assert len(pending) == 1
    return pending[0]


def _submit(paths: StatePaths, request, response_id: str, **value):
    payload = request.to_dict()
    response = {
        "schema_version": UserInteractionResponse.SCHEMA_VERSION,
        "interaction_response_id": response_id,
        "interaction_request_id": payload["interaction_request_id"],
        "response_status": "submitted",
        "target_identity": dict(payload["target_identity"]),
        "state_snapshot_identity": dict(payload["state_snapshot_identity"]),
        "host_surface_identity": "client_frontend_http_pipeline_session",
        "submitted_at": "2026-05-06T00:00:00Z",
        **value,
    }
    return submit_user_interaction_response(
        {
            "schema_version": "semantic_control_kernel.interaction_response_submit.v1",
            "interaction_request_id": payload["interaction_request_id"],
            "response": response,
            "target_identity": dict(payload["target_identity"]),
            "state_snapshot_identity": dict(payload["state_snapshot_identity"]),
            "host_surface_identity": "client_frontend_http_pipeline_session",
            "client_request_id": f"req_{response_id}",
        },
        state_paths=paths,
        continue_inline=True,
    )


def test_rebuild_agent_flow_collects_inputs_and_completes_with_explain_now(tmp_path: Path, monkeypatch) -> None:
    paths = _state_paths(tmp_path)
    root = tmp_path / "Artifact Tree"
    create_artifact_tree(root)
    seed_rebuild_release(root)
    monkeypatch.setattr(
        "semantic_control_kernel.services.agent_tool_workflow_dispatch._rebuild_runtime",
        _runtime_factory,
    )

    started = dispatch_permanent_workflow_tool("database_rebuild_from_artifacts", state_paths=paths).to_dict()
    assert started["status"] == "ok"
    assert started["effect"] == "workflow_started"
    workflow_run_id = started["workflow_run_id"]
    choose_request = _pending(paths, workflow_run_id)
    assert choose_request.payload["interaction_function"] == "choose_artifact_root_folder"

    chose = _submit(paths, choose_request, "irs_rebuild_choose", path_value=str(root))
    assert chose["continued_workflow_result"]["status"] == "ok"
    name_request = _pending(paths, workflow_run_id)
    assert name_request.payload["interaction_function"] == "name_database"

    named = _submit(paths, name_request, "irs_rebuild_name", text_value="rebuilt")
    continued = named["continued_workflow_result"]
    assert continued["status"] == "ok"
    assert continued["effect"] == "workflow_completed"
    assert continued["final_state"] == "semantic_release_active"
    assert continued["mirror_event"]["agent_explanation_guidance"]["response_mode"] == "explain_now"
    completion = continued["mirror_event"]["technical_detail_ref"]["workflow_completion"]
    assert completion["workflow_family"] == "database_rebuild"
    assert completion["target_database_path"].endswith("rebuilt.db")
    assert _RUNTIME_CAPTURE["embedding_adapter"].calls == ["create_embeddings"]
    progress_events = [event.to_dict() for event in ProgressEventStore(paths).list_progress_events(workflow_run_id)]
    assert ("creating_embeddings", "step_started") in [(event["step_id"], event["status"]) for event in progress_events]


def test_rebuild_agent_overwrite_uses_confirmation_receipt(tmp_path: Path, monkeypatch) -> None:
    paths = _state_paths(tmp_path)
    root = tmp_path / "Artifact Tree"
    create_artifact_tree(root)
    seed_rebuild_release(root)
    target = root / "Corpus" / "existing.db"
    target.write_text("old", encoding="utf-8")
    monkeypatch.setattr(
        "semantic_control_kernel.services.agent_tool_workflow_dispatch._rebuild_runtime",
        _runtime_factory,
    )

    started = dispatch_permanent_workflow_tool("database_rebuild_from_artifacts", state_paths=paths).to_dict()
    workflow_run_id = started["workflow_run_id"]
    _submit(paths, _pending(paths, workflow_run_id), "irs_rebuild_overwrite_choose", path_value=str(root))
    named = _submit(paths, _pending(paths, workflow_run_id), "irs_rebuild_overwrite_name", text_value="existing.db")
    assert named["continued_workflow_result"]["effect"] == "workflow_started"
    confirmation_request = _pending(paths, workflow_run_id)
    assert confirmation_request.payload["interaction_function"] == "user_confirmation"
    assert confirmation_request.payload["risk_class"] == "destructive"
    assert confirmation_request.payload["target_identity"]["release_fingerprint"] == "sha256:tree_release"

    confirmed = _submit(
        paths,
        confirmation_request,
        "irs_rebuild_overwrite_confirm",
        confirmation_decision="confirmed",
    )
    continued = confirmed["continued_workflow_result"]
    assert continued["status"] == "ok"
    assert continued["effect"] == "workflow_completed"
    assert continued["final_state"] == "semantic_release_active"
    assert continued["mirror_event"]["agent_explanation_guidance"]["response_mode"] == "explain_now"
    receipts = ReceiptStore(paths).list_by_target(confirmation_request.payload["target_identity"])
    assert receipts[-1].to_dict()["user_decision"] == "confirmed"
    assert continued["mirror_event"]["technical_detail_ref"]["workflow_completion"]["outcome"]["overwrite_confirmed"] is True


def test_rebuild_agent_warns_when_corpus_contains_different_database(tmp_path: Path, monkeypatch) -> None:
    paths = _state_paths(tmp_path)
    root = tmp_path / "Artifact Tree"
    create_artifact_tree(root)
    seed_rebuild_release(root)
    existing = root / "Corpus" / "corpus.db"
    existing.write_text("old", encoding="utf-8")
    monkeypatch.setattr(
        "semantic_control_kernel.services.agent_tool_workflow_dispatch._rebuild_runtime",
        _runtime_factory,
    )

    started = dispatch_permanent_workflow_tool("database_rebuild_from_artifacts", state_paths=paths).to_dict()
    workflow_run_id = started["workflow_run_id"]
    _submit(paths, _pending(paths, workflow_run_id), "irs_rebuild_existing_other_choose", path_value=str(root))
    named = _submit(paths, _pending(paths, workflow_run_id), "irs_rebuild_existing_other_name", text_value="Artefacts Test")

    assert named["continued_workflow_result"]["effect"] == "workflow_started"
    warning_request = _pending(paths, workflow_run_id)
    assert warning_request.payload["interaction_function"] == "user_confirmation"
    assert warning_request.payload["risk_class"] == "non_destructive"
    assert warning_request.payload["confirmation_request_id"].startswith("rebuild_existing_corpus_db_warning:")
    assert "already contains" in warning_request.payload["user_visible_summary"]
    assert "corpus.db" in warning_request.payload["user_visible_summary"]

    confirmed = _submit(
        paths,
        warning_request,
        "irs_rebuild_existing_other_confirm",
        confirmation_decision="confirmed",
    )

    continued = confirmed["continued_workflow_result"]
    assert continued["status"] == "ok"
    assert continued["effect"] == "workflow_completed"
    completion = continued["mirror_event"]["technical_detail_ref"]["workflow_completion"]
    assert completion["target_database_path"].endswith("Artefacts Test.db")
