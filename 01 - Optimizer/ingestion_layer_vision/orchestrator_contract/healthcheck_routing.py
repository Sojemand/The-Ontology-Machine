"""Healthcheck routing helpers for the merged optimizer contract."""
from __future__ import annotations

from ingestion_layer_file.orchestrator_contract.types import HEALTHCHECK_DEPENDENCIES as FILE_DEPENDENCIES

VISION_DEPENDENCIES = frozenset(
    {
        "pdf-pdfplumber",
        "optimizer_ocr",
    }
)


def split_payloads(payload: dict) -> tuple[dict | None, dict | None] | None:
    raw_dependencies = payload.get("required_dependencies")
    if not isinstance(raw_dependencies, list):
        return None
    file_dependencies: list[str] = []
    vision_dependencies: list[str] = []
    for item in raw_dependencies:
        name = str(item).strip()
        if not name:
            continue
        if name in FILE_DEPENDENCIES and name not in file_dependencies:
            file_dependencies.append(name)
        elif name in VISION_DEPENDENCIES and name not in vision_dependencies:
            vision_dependencies.append(name)
    return _payload_or_none(payload, "file", file_dependencies), _payload_or_none(
        payload,
        "vision",
        vision_dependencies,
    )


def merge_responses(*responses: dict) -> dict:
    dependencies = []
    messages = []
    healthy = True
    for response in responses:
        if response.get("healthy") is not True or response.get("status") != "ok":
            healthy = False
        dependencies.extend(response.get("dependencies", []) if isinstance(response.get("dependencies"), list) else [])
        message = str(response.get("message") or response.get("error") or "").strip()
        if message and message not in messages:
            messages.append(message)
    return {
        "status": "ok" if healthy else "error",
        "healthy": healthy,
        "message": "" if healthy else "; ".join(messages),
        "dependencies": dependencies,
    }


def _payload_or_none(payload: dict, profile: str, dependencies: list[str]) -> dict | None:
    if not dependencies:
        return None
    return {**payload, "optimizer_profile": profile, "required_dependencies": dependencies}
