"""Result text formatting for owner action responses."""
from __future__ import annotations

import json


def result_text(app, surface_id: str) -> str:
    state = app._operation_results.get(surface_id)
    if not isinstance(state, dict):
        return ""
    response = state.get("response") if isinstance(state.get("response"), dict) else {}
    lines = _headline_lines(state, response)
    lines.extend(_hint_lines(response))
    artifacts = response.get("artifacts")
    if isinstance(artifacts, list):
        lines.extend(artifact_lines(artifacts))
    lines.extend(merge_flow_lines(state))
    summary = _summary_payload(response)
    if summary:
        lines.append(json.dumps(summary, indent=2, ensure_ascii=False))
    return "\n".join(lines)


def artifact_lines(items: list[dict]) -> list[str]:
    lines = []
    for item in items:
        if not isinstance(item, dict):
            continue
        label = str(item.get("label") or "").strip()
        value = str(item.get("value") or "").strip()
        if label and value:
            lines.append(f"{label}: {value}")
    return lines


def merge_flow_artifacts(merge_flow: dict) -> list[dict]:
    artifact_paths = merge_flow.get("artifact_paths")
    if not isinstance(artifact_paths, dict):
        return []
    labels = {
        "snapshot_risk_confirmation_artifact_path": "Snapshot Confirmation",
        "collision_resolution_artifact_path": "Collision Resolution",
    }
    return [
        {"label": labels.get(key, key), "value": str(value)}
        for key, value in artifact_paths.items()
        if str(value).strip()
    ]


def merge_flow_lines(state: dict) -> list[str]:
    merge_flow = state.get("merge_flow") if isinstance(state, dict) else None
    if not isinstance(merge_flow, dict):
        return []
    lines = artifact_lines(merge_flow_artifacts(merge_flow))
    interaction = pending_interaction_from_flow(merge_flow)
    if isinstance(interaction, dict):
        headline = str(interaction.get("headline") or "").strip()
        if headline:
            lines.append(headline)
        summary_lines = interaction.get("summary_lines")
        if isinstance(summary_lines, list):
            lines.extend(str(item) for item in summary_lines if str(item).strip())
    return lines


def pending_interaction_from_flow(merge_flow: dict) -> dict | None:
    pending = merge_flow.get("pending_interactions")
    if not isinstance(pending, list):
        return None
    index = int(merge_flow.get("pending_index") or 0)
    if 0 <= index < len(pending) and isinstance(pending[index], dict):
        return pending[index]
    return None


def _headline_lines(state: dict, response: dict) -> list[str]:
    label = str(state.get("label") or "Action")
    lines = [f"{label}: {str(response.get('status') or 'unknown').casefold()}"]
    headline = str(response.get("headline") or "")
    if headline:
        lines.append(headline)
    summary_lines = response.get("summary_lines")
    if isinstance(summary_lines, list):
        lines.extend(str(item) for item in summary_lines if str(item).strip())
    if response.get("output_path"):
        lines.append(str(response["output_path"]))
    message = str(response.get("reason") or response.get("message") or "")
    if message:
        lines.append(message)
    return lines


def _hint_lines(response: dict) -> list[str]:
    lines: list[str] = []
    for key, label in (
        ("required_fields", "Required fields"),
        ("allowed_values", "Allowed values"),
        ("references_existing_codes", "Existing refs"),
        ("validation_risks", "Validation risks"),
    ):
        values = response.get(key)
        if isinstance(values, list) and values:
            lines.append(f"{label}: {', '.join(str(item) for item in values if str(item).strip())}")
    for key, label in (("compile_effect", "Compile"), ("prompt_effect", "Prompt"), ("corpus_effect", "Corpus")):
        value = str(response.get(key) or "").strip()
        if value:
            lines.append(f"{label}: {value}")
    return lines


def _summary_payload(response: dict) -> dict:
    hidden = {
        "status",
        "headline",
        "summary_lines",
        "artifacts",
        "detail",
        "review_payload",
        "output_path",
        "reason",
        "message",
        "required_fields",
        "allowed_values",
        "references_existing_codes",
        "validation_risks",
        "compile_effect",
        "prompt_effect",
        "corpus_effect",
    }
    return {key: value for key, value in response.items() if key not in hidden}
