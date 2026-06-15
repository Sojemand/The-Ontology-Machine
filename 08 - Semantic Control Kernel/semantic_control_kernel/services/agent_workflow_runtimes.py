from __future__ import annotations

from pathlib import Path

from semantic_control_kernel.adapters.corpus import CorpusAdapter
from semantic_control_kernel.adapters.embedding import EmbeddingAdapter
from semantic_control_kernel.adapters.merge import MergeAdapter
from semantic_control_kernel.adapters.orchestrator import OrchestratorAdapter
from semantic_control_kernel.adapters.pipeline_batch import PipelineBatchAdapter
from semantic_control_kernel.adapters.semantic_release import SemanticReleaseAdapter
from semantic_control_kernel.adapters.workspace import WorkspaceAdapter
from semantic_control_kernel.repository.paths import StatePaths
from semantic_control_kernel.workflows.database_creation import DatabaseCreationRuntime
from semantic_control_kernel.workflows.database_creation.interaction_port import DatabaseCreationInteractionPort
from semantic_control_kernel.workflows.llm_calls.host_port import KernelLLMPort
from semantic_control_kernel.workflows.merge.entry import MergeWorkflowRuntime
from semantic_control_kernel.workflows.merge.interaction_port import MergeInteractionPort
from semantic_control_kernel.workflows.pipeline_run import PipelineRunRuntime
from semantic_control_kernel.workflows.rebuild.entry import RebuildWorkflowRuntime
from semantic_control_kernel.workflows.rebuild.interaction_port import RebuildInteractionPort


def database_creation_runtime(state_paths: StatePaths) -> DatabaseCreationRuntime:
    pipeline_root = pipeline_root_for(state_paths)
    llm_port = KernelLLMPort(state_root=state_paths.state_root, pipeline_root=pipeline_root)
    return DatabaseCreationRuntime(
        state_root=state_paths.state_root,
        workspace_adapter=WorkspaceAdapter(state_root=state_paths.state_root, pipeline_root=pipeline_root),
        corpus_adapter=CorpusAdapter(state_root=state_paths.state_root, pipeline_root=pipeline_root),
        semantic_release_adapter=SemanticReleaseAdapter(
            state_root=state_paths.state_root,
            pipeline_root=pipeline_root,
        ),
        interaction_port=DatabaseCreationInteractionPort(
            state_paths,
            orchestrator_adapter=OrchestratorAdapter(state_root=state_paths.state_root, pipeline_root=pipeline_root),
        ),
        llm_port=llm_port,
    )


def pipeline_runtime(state_paths: StatePaths) -> PipelineRunRuntime:
    pipeline_root = pipeline_root_for(state_paths)
    return PipelineRunRuntime(
        state_root=state_paths.state_root,
        batch_adapter=PipelineBatchAdapter(state_root=state_paths.state_root, pipeline_root=pipeline_root),
        orchestrator_adapter=OrchestratorAdapter(state_root=state_paths.state_root, pipeline_root=pipeline_root),
        corpus_adapter=CorpusAdapter(state_root=state_paths.state_root, pipeline_root=pipeline_root),
    )


def merge_runtime(state_paths: StatePaths) -> MergeWorkflowRuntime:
    pipeline_root = pipeline_root_for(state_paths)
    return MergeWorkflowRuntime(
        state_root=state_paths.state_root,
        workspace_adapter=WorkspaceAdapter(state_root=state_paths.state_root, pipeline_root=pipeline_root),
        corpus_adapter=CorpusAdapter(state_root=state_paths.state_root, pipeline_root=pipeline_root),
        semantic_release_adapter=SemanticReleaseAdapter(state_root=state_paths.state_root, pipeline_root=pipeline_root),
        merge_adapter=MergeAdapter(state_root=state_paths.state_root, pipeline_root=pipeline_root),
        interaction_port=MergeInteractionPort(state_paths),
    )


def rebuild_runtime(state_paths: StatePaths) -> RebuildWorkflowRuntime:
    pipeline_root = pipeline_root_for(state_paths)
    semantic_release_adapter = SemanticReleaseAdapter(state_root=state_paths.state_root, pipeline_root=pipeline_root)
    return RebuildWorkflowRuntime(
        state_root=state_paths.state_root,
        corpus_adapter=CorpusAdapter(state_root=state_paths.state_root, pipeline_root=pipeline_root),
        semantic_release_adapter=semantic_release_adapter,
        embedding_adapter=EmbeddingAdapter(state_root=state_paths.state_root, pipeline_root=pipeline_root),
        interaction_port=RebuildInteractionPort(
            state_paths,
            semantic_release_adapter=semantic_release_adapter,
        ),
    )


def pipeline_root_for(state_paths: StatePaths) -> Path:
    return state_paths.module_root.parent
