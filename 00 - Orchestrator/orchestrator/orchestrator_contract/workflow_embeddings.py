"""Embedding contract action helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..workspace_domain.policy import path_hash

_OWNER_EMBEDDING_OK_STATUSES = {"completed", "disabled", "skipped", "ok"}


def embeddings_action(ui_state_data: dict, *, engine_cls, ui_state_cls, owner_result: bool = False) -> dict:
    ui_state = ui_state_cls.from_dict(ui_state_data)
    database_path = _selected_database_path(ui_state)
    engine = engine_cls()
    try:
        result = engine.run_embeddings(ui_state)
    finally:
        engine.close()
    if result is None:
        if owner_result:
            return _embedding_owner_result(
                database_path=database_path,
                embedding_result="ok",
                count=0,
                reason="",
            )
        return {"status": "ok"}
    if owner_result:
        return _embedding_owner_result(
            database_path=database_path,
            embedding_result=str(result.status or ""),
            count=int(result.count or 0),
            reason=str(result.reason or ""),
        )
    return {
        "status": result.status,
        "count": result.count,
        "reason": str(result.reason or ""),
    }


def _selected_database_path(ui_state: Any) -> Path | None:
    value = str(getattr(ui_state, "selected_corpus_db_path", "") or "").strip()
    if not value:
        return None
    return Path(value).expanduser().resolve(strict=False)


def _embedding_owner_result(
    *,
    database_path: Path | None,
    embedding_result: str,
    count: int,
    reason: str,
) -> dict:
    status = embedding_result.strip().casefold()
    output_refs: dict[str, Any] = {
        "embedding_count": count,
        "embedding_reason": reason,
        "embedding_result": status or "ok",
    }
    target_identity_proof: dict[str, Any] = {}
    if database_path is not None:
        database_path_text = str(database_path)
        database_path_hash = path_hash(database_path)
        output_refs["database_path"] = database_path_text
        output_refs["database_path_hash"] = database_path_hash
        target_identity_proof["database_path"] = database_path_text
        target_identity_proof["database_path_hash"] = database_path_hash
    return {
        "status": "ok" if status in _OWNER_EMBEDDING_OK_STATUSES else status or "error",
        "count": count,
        "reason": reason,
        "output_refs": output_refs,
        "target_identity_proof": target_identity_proof,
    }
