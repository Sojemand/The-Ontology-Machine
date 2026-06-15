from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

from semantic_control_kernel.workflows.database_creation.shared_steps import (
    CreationStateRepository,
    EmptyInteractionPort,
)


@dataclass
class DatabaseCreationRuntime:
    state_root: str | Path
    workspace_adapter: Any
    corpus_adapter: Any
    semantic_release_adapter: Any
    interaction_port: Any = field(default_factory=EmptyInteractionPort)
    llm_port: Any | None = None
    blueprint_ref: str = "default_blueprint"
    runtime_settings: Mapping[str, Any] = field(default_factory=dict)
    repository: CreationStateRepository | None = None

    def state_repository(self) -> CreationStateRepository:
        if self.repository is None:
            self.repository = CreationStateRepository(self.state_root)
        return self.repository
