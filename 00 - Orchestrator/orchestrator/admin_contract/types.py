"""Admin contract constants for orchestrator-owned runtime state."""

from __future__ import annotations

INSPECT_RUNTIME_ACTION = "inspect_runtime"
MANAGE_RUNTIME_SETTINGS_ACTION = "manage_runtime_settings"
MANAGE_CREDENTIALS_ACTION = "manage_credentials"
REVEAL_SECRET_ACTION = "reveal_secret"

SUPPORTED_ACTIONS = (
    INSPECT_RUNTIME_ACTION,
    MANAGE_RUNTIME_SETTINGS_ACTION,
    MANAGE_CREDENTIALS_ACTION,
    REVEAL_SECRET_ACTION,
)

RUNTIME_OPERATIONS = ("read", "write", "reset")
CREDENTIAL_OPERATIONS = ("inspect", "set_api_key", "delete_api_key")
CREDENTIAL_TARGETS = ("llm_shared", "optimizer_ocr", "embeddings")

__all__ = [
    "CREDENTIAL_OPERATIONS",
    "CREDENTIAL_TARGETS",
    "INSPECT_RUNTIME_ACTION",
    "MANAGE_CREDENTIALS_ACTION",
    "MANAGE_RUNTIME_SETTINGS_ACTION",
    "REVEAL_SECRET_ACTION",
    "RUNTIME_OPERATIONS",
    "SUPPORTED_ACTIONS",
]
