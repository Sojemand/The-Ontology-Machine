"""Path-stable surface for orchestrator sibling-module integrations."""

from .registry import (
    default_module_keys,
    healthcheck_timeout_seconds,
    module_entry,
    operation_entry,
    pipeline_stage_names,
    required_actions_by_module,
    stage_name_for_module,
)
from .types import (
    ClassificationStageResult,
    CorpusLoadStageResult,
    EmbeddingStageResult,
    ExternalDependencyStatus,
    ExtractionStageResult,
    InterpretationStageResult,
    ModuleContractError,
    ModuleHealthStatus,
    NormalizationStageResult,
    PipelineModules,
    ReleaseActivationStageResult,
    ValidationStageResult,
)
from .workflow import SubmodulePipelineModules


def __getattr__(name: str):
    dynamic = {
        "DEFAULT_MODULE_KEYS": default_module_keys,
        "HEALTHCHECK_TIMEOUT_SECONDS": healthcheck_timeout_seconds,
        "PIPELINE_STAGE_NAMES": pipeline_stage_names,
    }
    if name in dynamic:
        return dynamic[name]()
    raise AttributeError(name)

__all__ = [
    "ClassificationStageResult",
    "CorpusLoadStageResult",
    "DEFAULT_MODULE_KEYS",
    "EmbeddingStageResult",
    "ExternalDependencyStatus",
    "ExtractionStageResult",
    "HEALTHCHECK_TIMEOUT_SECONDS",
    "InterpretationStageResult",
    "ModuleContractError",
    "ModuleHealthStatus",
    "NormalizationStageResult",
    "PIPELINE_STAGE_NAMES",
    "PipelineModules",
    "ReleaseActivationStageResult",
    "SubmodulePipelineModules",
    "ValidationStageResult",
    "default_module_keys",
    "healthcheck_timeout_seconds",
    "module_entry",
    "operation_entry",
    "pipeline_stage_names",
    "required_actions_by_module",
    "stage_name_for_module",
]
