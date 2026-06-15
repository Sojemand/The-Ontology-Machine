"""Named action literals for the orchestrator contract surface."""

from __future__ import annotations

from typing import Literal

RUN_ACTION = "run"
RESET_ACTION = "reset"
RESET_PIPELINE_LOGS_ACTION = "reset_pipeline_logs"
EMBEDDINGS_ACTION = "embeddings"
ACTIVATE_CORPUS_CONTEXT_ACTION = "activate_corpus_context"
INSPECT_SOURCE_DOCUMENT_SAMPLE_ACTION = "inspect_source_document_sample"
KERNEL_LLM_RUNTIME_PROFILE_ACTION = "kernel_llm_runtime_profile"
KERNEL_LLM_GENERATE_ACTION = "kernel_llm_generate"
HEALTHCHECK_ACTION = "healthcheck"
CREATE_ARTIFACT_TREE_ACTION = "create_artifact_tree"
VALIDATE_ARTIFACT_TREE_ACTION = "validate_artifact_tree"
CREATE_PIPELINE_BATCH_MANIFEST_ACTION = "create_pipeline_batch_manifest"
FINALIZE_PIPELINE_BATCH_MANIFEST_ACTION = "finalize_pipeline_batch_manifest"

ActionName = Literal[
    "run",
    "reset",
    "reset_pipeline_logs",
    "embeddings",
    "activate_corpus_context",
    "inspect_source_document_sample",
    "kernel_llm_runtime_profile",
    "kernel_llm_generate",
    "healthcheck",
    "create_artifact_tree",
    "validate_artifact_tree",
    "create_pipeline_batch_manifest",
    "finalize_pipeline_batch_manifest",
]

WORKER_ACTIONS = (RUN_ACTION, RESET_ACTION, RESET_PIPELINE_LOGS_ACTION, EMBEDDINGS_ACTION)
SUPPORTED_ACTIONS = (
    RUN_ACTION,
    RESET_ACTION,
    RESET_PIPELINE_LOGS_ACTION,
    EMBEDDINGS_ACTION,
    ACTIVATE_CORPUS_CONTEXT_ACTION,
    INSPECT_SOURCE_DOCUMENT_SAMPLE_ACTION,
    KERNEL_LLM_RUNTIME_PROFILE_ACTION,
    KERNEL_LLM_GENERATE_ACTION,
    HEALTHCHECK_ACTION,
    CREATE_ARTIFACT_TREE_ACTION,
    VALIDATE_ARTIFACT_TREE_ACTION,
    CREATE_PIPELINE_BATCH_MANIFEST_ACTION,
    FINALIZE_PIPELINE_BATCH_MANIFEST_ACTION,
)
