from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class RebuildWorkflowRuntime:
    state_root: str | Path
    corpus_adapter: Any
    semantic_release_adapter: Any
    embedding_adapter: Any
    interaction_port: Any | None = None


__all__ = ["RebuildWorkflowRuntime"]
