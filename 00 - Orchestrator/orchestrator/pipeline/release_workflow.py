"""Semantic-release preflight and activation flows for the orchestrator."""

from __future__ import annotations

from .release_activation_confirmation import (
    build_activation_confirmation_prompt,
    build_confirmation_payload,
    write_confirmation_artifact as _write_confirmation_artifact,
)
from .release_activation_flow import (
    activation_preflight,
    ensure_selected_release_is_active,
    execute_release_activation,
    run_release_activation,
)
from .release_activation_messages import (
    build_activation_blocked_message,
    build_selected_release_needs_activation_message,
)

__all__ = [
    "activation_preflight",
    "build_activation_blocked_message",
    "build_activation_confirmation_prompt",
    "build_confirmation_payload",
    "build_selected_release_needs_activation_message",
    "ensure_selected_release_is_active",
    "execute_release_activation",
    "run_release_activation",
]
