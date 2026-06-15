from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import support_monitor
from .support_monitor_storage import append_jsonl, load_jsonl
from .tool_handler_types import ToolFailure
from .tool_handler_validation import _optional_text

_REVIEW_CHECKPOINTS_NAME = "release_review_checkpoints.jsonl"


def record_review_checkpoint(
    artifact_path: Path,
    *,
    workflow_kind: str,
    owner_payload: dict[str, Any],
    result: dict[str, Any],
) -> dict[str, Any]:
    fingerprint = candidate_fingerprint(result)
    checkpoint = {
        "workflow_kind": workflow_kind,
        "artifact_folder": str(artifact_path),
        "owner_action": str(owner_payload.get("action") or ""),
        "input_hash": review_input_hash(owner_payload),
        "candidate_fingerprint": fingerprint,
        "recorded": bool(fingerprint),
    }
    if not fingerprint:
        checkpoint["warning"] = "Owner review response did not include candidate_release_fingerprint; no apply checkpoint was recorded."
        return checkpoint
    record = {**checkpoint, "recorded_at": datetime.now(timezone.utc).isoformat()}
    append_jsonl(review_checkpoints_path(), record)
    return checkpoint


def apply_safety_payload(
    artifact_path: Path,
    workflow_kind: str,
    review_payload: dict[str, Any],
    arguments: dict[str, Any],
) -> dict[str, Any]:
    expected = _optional_text(arguments, "expected_candidate_fingerprint")
    if not expected:
        return {
            "verified_review_checkpoint": False,
            "residual_risk": (
                "No expected_candidate_fingerprint was supplied. MCP confirmed the user intent, "
                "but cannot prove that the applied candidate matches the latest review."
            ),
        }
    checkpoint = matching_review_checkpoint(
        artifact_path,
        workflow_kind=workflow_kind,
        input_hash=review_input_hash(review_payload),
        expected_candidate_fingerprint=expected,
    )
    if checkpoint is None:
        raise ToolFailure(
            "Kein passender Review-Checkpoint fuer expected_candidate_fingerprint gefunden. "
            "Bitte zuerst das passende Review-Tool erneut ausfuehren oder ohne Fingerprint bewusst mit user_confirmed=true anwenden."
        )
    return {
        "verified_review_checkpoint": True,
        "expected_candidate_fingerprint": expected,
        "review_checkpoint_recorded_at": str(checkpoint.get("recorded_at") or ""),
    }


def matching_review_checkpoint(
    artifact_path: Path,
    *,
    workflow_kind: str,
    input_hash: str,
    expected_candidate_fingerprint: str,
) -> dict[str, Any] | None:
    matches = [
        item
        for item in load_review_checkpoints()
        if item.get("workflow_kind") == workflow_kind
        and item.get("artifact_folder") == str(artifact_path)
        and item.get("input_hash") == input_hash
        and item.get("candidate_fingerprint") == expected_candidate_fingerprint
    ]
    return matches[-1] if matches else None


def load_review_checkpoints() -> list[dict[str, Any]]:
    return load_jsonl(review_checkpoints_path())


def review_checkpoints_path() -> Path:
    return support_monitor.state_root() / _REVIEW_CHECKPOINTS_NAME


def candidate_fingerprint(result: dict[str, Any]) -> str:
    return str(result.get("candidate_release_fingerprint") or "").strip()


def review_input_hash(owner_payload: dict[str, Any]) -> str:
    normalized = json.dumps(owner_payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


__all__ = [
    "apply_safety_payload",
    "record_review_checkpoint",
    "review_checkpoints_path",
    "review_input_hash",
]
