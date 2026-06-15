from __future__ import annotations

from pathlib import Path

from test_phase11_fakes import ok_result
from semantic_control_kernel.repository.interaction_store import InteractionRequestStore
from semantic_control_kernel.repository.paths import StatePaths
from semantic_control_kernel.surface.client_frontend_bridge import submit_user_interaction_response
from semantic_control_kernel.types.events import UserInteractionResponse

MODULE_ROOT = Path(__file__).resolve().parents[2]

def _state_paths(tmp_path: Path) -> StatePaths:
    return StatePaths(module_root=MODULE_ROOT, state_root=(tmp_path / "state").resolve())

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
        "submitted_at": "2026-05-31T12:00:00Z",
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

class AgentManualCorpusAdapter:
    def read_active_semantic_release(self, request_payload=None):
        return ok_result(
            "read_active_semantic_release",
            {
                "release": {
                    "release_id": "semantic_release.custom",
                    "release_version": "v1",
                    "fingerprint": "sha256:release001",
                    "taxonomy": {
                        "taxonomy_id": "taxonomy.custom",
                        "taxonomy_version": "v1",
                        "taxonomy_fingerprint": "sha256:taxonomy001",
                    },
                    "projections": [
                        {
                            "projection_id": "projection.custom",
                            "projection_fingerprint": "sha256:projection001",
                        }
                    ],
                },
                "release_id": "semantic_release.custom",
                "release_version": "v1",
                "fingerprint": "sha256:release001",
                "active_snapshot": {"snapshot_id": "snapshot_manual_agent"},
                "status": {"database_id": "db:manual_agent"},
            },
        )
