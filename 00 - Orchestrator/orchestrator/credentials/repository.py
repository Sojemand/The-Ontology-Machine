"""Repository stage for non-sensitive orchestrator credential state."""

from __future__ import annotations

import logging
from pathlib import Path

from ..state.adapter import atomic_json_write, load_json_object
from .types import CredentialsState
from .validation import validate_credentials_state, validate_serialized_state

logger = logging.getLogger(__name__)


def credentials_state_path(state_dir: Path) -> Path:
    return Path(state_dir) / "credentials_state.json"


def load_credentials_state(state_dir: Path) -> CredentialsState:
    path = credentials_state_path(state_dir)
    payload = load_json_object(
        path,
        read_error="Could not load credentials state: %s",
        invalid_format="Credentials-State hat ungueltiges Format: %s",
    )
    if payload is None:
        return CredentialsState()
    try:
        state = CredentialsState.from_dict(payload)
        validate_credentials_state(state)
        return state
    except Exception:
        logger.warning("Credentials state could not be deserialized: %s", path, exc_info=True)
        return CredentialsState()


def save_credentials_state(state_dir: Path, state: CredentialsState) -> None:
    validate_credentials_state(state)
    payload = state.to_dict()
    validate_serialized_state(payload)
    atomic_json_write(credentials_state_path(state_dir), payload)
