"""Reset confirmation validation for owner-local Corpus administration."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

RESET_CONFIRMATION_VERSION = "reset_active_corpus_db_confirmation_v1"


def load_reset_confirmation(path_value: str | Path, *, expected_db_path: Path) -> dict[str, Any]:
    path = Path(path_value).expanduser().resolve()
    if not path.exists():
        raise ValueError(f"Confirmation-Artefakt fehlt: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Confirmation-Artefakt muss ein JSON-Objekt sein.")
    if str(payload.get("artifact_version") or "").strip() != RESET_CONFIRMATION_VERSION:
        raise ValueError("Confirmation-Artefakt hat eine ungueltige Version.")
    if str(payload.get("requested_action") or "").strip() != "reset_active_corpus_db":
        raise ValueError("Confirmation-Artefakt passt nicht zu reset_active_corpus_db.")
    if payload.get("confirmed") is not True:
        raise ValueError("Reset erfordert confirmed=true.")
    confirmed_path = Path(str(payload.get("corpus_db_path") or "")).expanduser().resolve()
    if confirmed_path != expected_db_path:
        raise ValueError("Confirmation-Artefakt bestaetigt eine andere Corpus DB.")
    return {
        "artifact_path": str(path),
        "confirmed": True,
        "corpus_db_path": str(confirmed_path),
        "reason": str(payload.get("reason") or "").strip(),
    }
