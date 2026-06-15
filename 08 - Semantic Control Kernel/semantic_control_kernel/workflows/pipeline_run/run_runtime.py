from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from semantic_control_kernel.adapters.corpus import CorpusAdapter
from semantic_control_kernel.adapters.orchestrator import OrchestratorAdapter
from semantic_control_kernel.adapters.pipeline_batch import PipelineBatchAdapter


@dataclass
class PipelineRunRuntime:
    state_root: str | Path
    batch_adapter: Any | None = None
    orchestrator_adapter: Any | None = None
    corpus_adapter: Any | None = None

    def __post_init__(self) -> None:
        root = Path(self.state_root)
        if self.batch_adapter is None:
            self.batch_adapter = PipelineBatchAdapter(state_root=root)
        if self.orchestrator_adapter is None:
            self.orchestrator_adapter = OrchestratorAdapter(state_root=root)
        if self.corpus_adapter is None:
            self.corpus_adapter = CorpusAdapter(state_root=root)
