from __future__ import annotations

import sys
from pathlib import Path

PIPELINE_ROOT = Path(__file__).resolve().parents[3]
KERNEL_ROOT = PIPELINE_ROOT / "08 - Semantic Control Kernel"
if str(KERNEL_ROOT) not in sys.path:
    sys.path.insert(0, str(KERNEL_ROOT))

from semantic_control_kernel.repository.event_store import MirrorEventStore  # noqa: E402
from semantic_control_kernel.repository.interaction_store import InteractionRequestStore  # noqa: E402
from semantic_control_kernel.repository.paths import StatePaths  # noqa: E402
from semantic_control_kernel.repository.run_store import WorkflowRunStore  # noqa: E402
from semantic_control_kernel.services.kernel_mirror_event_service import KernelMirrorEventService  # noqa: E402
from semantic_control_kernel.services.user_interaction_service import KernelUserInteractionService  # noqa: E402
from semantic_control_kernel.testing.fakes.fake_client_frontend_sink import FakeClientFrontendSink  # noqa: E402

TARGET = {"target_hash": "host_bridge_target", "artifact_root_path_hash": "art_host_bridge"}
SNAPSHOT = {"state_snapshot_id": "ss_host_bridge"}


def service(tmp_path: Path):
    paths = StatePaths.from_state_root(tmp_path / "state")
    paths.ensure_layout()
    sink = FakeClientFrontendSink()
    user_service = KernelUserInteractionService(
        interaction_store=InteractionRequestStore(paths),
        mirror_event_service=KernelMirrorEventService(MirrorEventStore(paths)),
        event_sink=sink,
        workflow_run_store=WorkflowRunStore(paths),
    )
    run = user_service.workflow_run_store.create_run("manual_pipeline_run", TARGET, "phase14_test")
    dispatch = user_service.request_interaction(
        interaction_function="name_database",
        workflow_run_id=run.workflow_run_id,
        function_or_route="create_empty_database",
        target_identity=TARGET,
        state_snapshot_identity=SNAPSHOT,
        user_visible_title="Name Database",
        user_visible_summary="Choose the database name.",
    )
    return paths, dispatch


def submit_request(interaction_request_id: str, *, text_value: str = "My DB") -> dict[str, object]:
    from semantic_control_kernel.repository.paths import utc_iso

    return {
        "schema_version": "semantic_control_kernel.interaction_response_submit.v1",
        "interaction_request_id": interaction_request_id,
        "response": {
            "schema_version": "kernel.user_interaction_response.v1",
            "interaction_response_id": "resp_submit",
            "interaction_request_id": interaction_request_id,
            "response_status": "submitted",
            "target_identity": TARGET,
            "state_snapshot_identity": SNAPSHOT,
            "host_surface_identity": "test_frontend",
            "submitted_at": utc_iso(),
            "text_value": text_value,
        },
        "target_identity": TARGET,
        "state_snapshot_identity": SNAPSHOT,
        "host_surface_identity": "test_frontend",
        "client_request_id": "req_submit",
    }
