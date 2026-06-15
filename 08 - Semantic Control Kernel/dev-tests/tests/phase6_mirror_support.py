from __future__ import annotations

from pathlib import Path

from semantic_control_kernel.domain.recovery.recovery_options import RecoveryOptionService
from semantic_control_kernel.policy.recovery_policy import RecoveryPolicy
from semantic_control_kernel.repository.event_store import MirrorEventStore
from semantic_control_kernel.repository.interaction_store import InteractionRequestStore
from semantic_control_kernel.repository.paths import StatePaths
from semantic_control_kernel.services.kernel_mirror_event_service import KernelMirrorEventService
from semantic_control_kernel.services.user_interaction_service import KernelUserInteractionService
from semantic_control_kernel.testing.fakes.fake_client_frontend_sink import FakeClientFrontendSink
from semantic_control_kernel.types.enums import RecoveryStateClass

TARGET = {
    "target_hash": "tgt_phase6",
    "artifact_root_path_hash": "art_phase6",
    "database_path_hash": "db_phase6",
}
SNAPSHOT = {"state_snapshot_id": "ss_phase6"}


def service(tmp_path: Path):
    paths = StatePaths.from_state_root(tmp_path / "state")
    mirror_store = MirrorEventStore(paths)
    mirror_service = KernelMirrorEventService(mirror_store)
    return (
        KernelUserInteractionService(
            interaction_store=InteractionRequestStore(paths),
            mirror_event_service=mirror_service,
            event_sink=FakeClientFrontendSink(),
        ),
        mirror_service,
        mirror_store,
    )


def recovery_options(tool_name: str = "kernel_open_recovery_dialog"):
    expires_at = RecoveryPolicy().expires_at(RecoveryStateClass.TARGET_IDENTITY_CHANGED.value)
    return (
        RecoveryOptionService().create_options(
            recovery_event_id="rev_phase6",
            recovery_state=RecoveryStateClass.TARGET_IDENTITY_CHANGED.value,
            target_identity=TARGET,
            state_snapshot_identity=SNAPSHOT,
            expires_at=expires_at,
            safe_tools=(tool_name,),
        ),
        expires_at,
    )
