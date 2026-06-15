"""Shared action names for orchestrator worker flows."""

from __future__ import annotations

from ..orchestrator_contract.types import EMBEDDINGS_ACTION, RESET_ACTION, RESET_PIPELINE_LOGS_ACTION, RUN_ACTION

ACTIVATE_RELEASE_ACTION = "activate_release"
CREATE_DATABASE_ACTION = "create_database"

__all__ = [
    "ACTIVATE_RELEASE_ACTION",
    "CREATE_DATABASE_ACTION",
    "EMBEDDINGS_ACTION",
    "RESET_ACTION",
    "RESET_PIPELINE_LOGS_ACTION",
    "RUN_ACTION",
]
