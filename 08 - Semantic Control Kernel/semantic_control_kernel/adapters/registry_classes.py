from __future__ import annotations

from types import MappingProxyType

from semantic_control_kernel.adapters.corpus import CorpusAdapter
from semantic_control_kernel.adapters.embedding import EmbeddingAdapter
from semantic_control_kernel.adapters.interpreter import InterpreterAdapter
from semantic_control_kernel.adapters.merge import MergeAdapter
from semantic_control_kernel.adapters.normalizer import NormalizerAdapter
from semantic_control_kernel.adapters.optimizer import OptimizerAdapter
from semantic_control_kernel.adapters.orchestrator import OrchestratorAdapter
from semantic_control_kernel.adapters.pipeline_batch import PipelineBatchAdapter
from semantic_control_kernel.adapters.semantic_release import SemanticReleaseAdapter
from semantic_control_kernel.adapters.validator import ValidatorAdapter
from semantic_control_kernel.adapters.workspace import WorkspaceAdapter


ADAPTER_CLASS_MAP = MappingProxyType(
    {
        "WorkspaceAdapter": WorkspaceAdapter,
        "OrchestratorAdapter": OrchestratorAdapter,
        "CorpusAdapter": CorpusAdapter,
        "SemanticReleaseAdapter": SemanticReleaseAdapter,
        "PipelineBatchAdapter": PipelineBatchAdapter,
        "MergeAdapter": MergeAdapter,
        "EmbeddingAdapter": EmbeddingAdapter,
        "OptimizerAdapter": OptimizerAdapter,
        "InterpreterAdapter": InterpreterAdapter,
        "ValidatorAdapter": ValidatorAdapter,
        "NormalizerAdapter": NormalizerAdapter,
    }
)


__all__ = ["ADAPTER_CLASS_MAP"]
