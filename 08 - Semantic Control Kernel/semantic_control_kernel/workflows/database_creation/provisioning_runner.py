from __future__ import annotations

from semantic_control_kernel.types.database_creation import DatabaseCreationBlocker
from semantic_control_kernel.workflows.database_creation.shared_steps import CreationStateRepository, DatabaseCreationExecution
from semantic_control_kernel.workflows.database_creation.step_support import stop_step


def run_or_block(
    runtime,
    repository: CreationStateRepository,
    execution: DatabaseCreationExecution,
    step,
    final_state: str | None = None,
) -> None:
    blocker: DatabaseCreationBlocker | None = step(runtime, repository, execution)
    if blocker is not None:
        stop_step(repository, execution, blocker, final_state=final_state)
