"""Readable workflow metadata text for owner-provided action cards."""
from __future__ import annotations


def details_text(action_link: dict) -> str:
    lines: list[str] = []
    workflow = _workflow_text(action_link)
    if workflow:
        lines.append(workflow)
    for key, label in (
        ("compile_effect", "Compile"),
        ("prompt_effect", "Prompt"),
        ("corpus_effect", "Corpus"),
    ):
        value = str(action_link.get(key) or "").strip()
        if value:
            lines.append(f"{label}: {value}")
    risks = [str(item).strip() for item in action_link.get("validation_risks", ()) if str(item).strip()]
    if risks:
        lines.append(f"Validation risks: {' | '.join(risks)}")
    return "\n".join(lines)


def _workflow_text(action_link: dict) -> str:
    stage = str(action_link.get("workflow_stage") or "").strip()
    order = action_link.get("workflow_order")
    if stage and order not in (None, ""):
        return f"Workflow: {order} - {stage}"
    if stage:
        return f"Workflow: {stage}"
    if order not in (None, ""):
        return f"Workflow: {order}"
    return ""
