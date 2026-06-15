"""Validation entrypoints for Interpreter edit surfaces."""

from __future__ import annotations

from ..prompts.bundle import normalize_prompt_bundle_payload
from . import env_repository
from .types import (
    DEBUG_CAPABILITIES_SURFACE_ID,
    EXECUTION_LIMITS_SURFACE_ID,
    OUTPUT_CONTRACT_PREVIEW_SURFACE_ID,
    PROMPT_BUNDLE_SURFACE_ID,
    RUNTIME_POLICY_ENV_SURFACE_ID,
)


def validate_surface(surface_id: str, value: dict) -> dict:
    if surface_id == RUNTIME_POLICY_ENV_SURFACE_ID:
        return env_repository.validate_runtime_policy(value)
    if surface_id == EXECUTION_LIMITS_SURFACE_ID:
        return env_repository.validate_execution_limits(value)
    if surface_id == PROMPT_BUNDLE_SURFACE_ID:
        return normalize_prompt_bundle_payload(value)
    if surface_id in {OUTPUT_CONTRACT_PREVIEW_SURFACE_ID, DEBUG_CAPABILITIES_SURFACE_ID}:
        raise ValueError(f"{surface_id} ist read-only.")
    raise ValueError(f"Unbekannte Surface: {surface_id}")
