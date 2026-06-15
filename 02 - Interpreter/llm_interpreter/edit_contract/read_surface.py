"""Read operations for Interpreter edit surfaces."""

from __future__ import annotations

from . import env_repository, prompt_repository, repository
from .types import (
    DEBUG_CAPABILITIES_SURFACE_ID,
    EXECUTION_LIMITS_SURFACE_ID,
    OUTPUT_CONTRACT_PREVIEW_SURFACE_ID,
    PROMPT_BUNDLE_SURFACE_ID,
    RUNTIME_POLICY_ENV_SURFACE_ID,
)


def read_surface(surface_id: str, *, paths, module_root) -> dict:
    if surface_id == RUNTIME_POLICY_ENV_SURFACE_ID:
        return env_repository.read_runtime_policy(paths)
    if surface_id == EXECUTION_LIMITS_SURFACE_ID:
        return env_repository.read_execution_limits(paths)
    if surface_id == PROMPT_BUNDLE_SURFACE_ID:
        return prompt_repository.read_prompt_bundle(paths)
    if surface_id == OUTPUT_CONTRACT_PREVIEW_SURFACE_ID:
        return prompt_repository.read_output_contract_preview()
    if surface_id == DEBUG_CAPABILITIES_SURFACE_ID:
        return repository.read_debug_capabilities(module_root)
    raise ValueError(f"Unbekannte Surface: {surface_id}")
