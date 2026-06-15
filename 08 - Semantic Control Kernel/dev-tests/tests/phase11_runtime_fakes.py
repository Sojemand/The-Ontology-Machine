from __future__ import annotations

from pathlib import Path

from semantic_control_kernel.workflows.pipeline_run.run import PipelineRunRuntime

from phase11_adapter_fakes import FakeBatchAdapter, FakeCorpusAdapter, FakeOrchestratorAdapter


def runtime_for(
    tmp_path: Path,
    *,
    batch_adapter: FakeBatchAdapter | None = None,
    orchestrator_adapter: FakeOrchestratorAdapter | None = None,
    corpus_adapter: FakeCorpusAdapter | None = None,
) -> PipelineRunRuntime:
    return PipelineRunRuntime(
        state_root=tmp_path / "state",
        batch_adapter=batch_adapter or FakeBatchAdapter(),
        orchestrator_adapter=orchestrator_adapter or FakeOrchestratorAdapter(),
        corpus_adapter=corpus_adapter or FakeCorpusAdapter(),
    )
