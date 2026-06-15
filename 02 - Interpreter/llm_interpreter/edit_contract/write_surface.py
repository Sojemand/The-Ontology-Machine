"""Write operations for Interpreter edit surfaces."""

from __future__ import annotations

from . import env_repository, prompt_repository
from .types import (
    DEBUG_CAPABILITIES_SURFACE_ID,
    EXECUTION_LIMITS_SURFACE_ID,
    OUTPUT_CONTRACT_PREVIEW_SURFACE_ID,
    PROMPT_BUNDLE_SURFACE_ID,
    RUNTIME_POLICY_ENV_SURFACE_ID,
)


def write_surface(surface_id: str, value: dict, *, paths) -> dict:
    if surface_id == RUNTIME_POLICY_ENV_SURFACE_ID:
        return env_repository.write_runtime_policy(paths, value)
    if surface_id == EXECUTION_LIMITS_SURFACE_ID:
        return env_repository.write_execution_limits(paths, value)
    if surface_id == PROMPT_BUNDLE_SURFACE_ID:
        return prompt_repository.write_prompt_bundle(paths, value)
    if surface_id in {OUTPUT_CONTRACT_PREVIEW_SURFACE_ID, DEBUG_CAPABILITIES_SURFACE_ID}:
        raise ValueError(f"{surface_id} ist read-only.")
    raise ValueError(f"Unbekannte Surface: {surface_id}")
