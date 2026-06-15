"""Refresh helpers for the Semantic Release editor surface."""

from __future__ import annotations

from .taxonomy_release_model import _release
from .text_widgets import set_readonly_text


def _refresh_candidates(frame) -> None:
    candidates = [item for item in frame._draft.get("release_candidates", []) if isinstance(item, dict)]
    labels = {}
    values = []
    for item in candidates:
        label = f"{item.get('release_id') or 'release'} @ {item.get('release_version') or '-'} | {item.get('relative_path') or item.get('path')}"
        labels[label] = str(item.get("path") or "")
        values.append(label)
    if not values:
        values = ["No release found"]
        labels = {"No release found": ""}
    frame._candidate_labels = labels
    frame._candidate_menu.configure(values=values)
    selected_path = str(frame._draft.get("selected_release_path") or "")
    selected_label = next((label for label, path in labels.items() if path == selected_path), values[0])
    frame._candidate_var.set(selected_label)


def _refresh_summary(frame) -> None:
    release = _release(frame)
    verification = frame._draft.get("verification") if isinstance(frame._draft.get("verification"), dict) else {}
    lines = [
        f"Release: {release.get('release_id') or '(none)'} @ {release.get('release_version') or '-'}",
        f"Projections: {len(release.get('projections') or [])}",
        f"Fingerprint: {release.get('fingerprint') or '-'}",
        f"Verify: {verification.get('status') or 'not_loaded'}",
    ]
    set_readonly_text(frame._summary, "\n".join(lines), min_lines=4, max_lines=6)


def _refresh_verify(frame) -> None:
    verification = frame._draft.get("verification") if isinstance(frame._draft.get("verification"), dict) else {}
    lines = [f"Status: {verification.get('status') or 'not_loaded'}"]
    for key in ("release_fingerprint", "master_taxonomy_release_id", "projection_count", "working_release_path"):
        if verification.get(key) not in (None, "", []):
            lines.append(f"{key}: {verification[key]}")
    decision = verification.get("db_decision") if isinstance(verification.get("db_decision"), dict) else {}
    if decision:
        lines.append(f"DB recommendation: {decision.get('recommended_action') or decision.get('status')}")
        if decision.get("summary"):
            lines.append(str(decision["summary"]))
    issues = [str(item) for item in verification.get("issues", []) if str(item)]
    warnings = [str(item) for item in verification.get("warnings", []) if str(item)]
    if issues:
        lines.append("")
        lines.append("Issues:")
        lines.extend(f"- {item}" for item in issues)
    if warnings:
        lines.append("")
        lines.append("Warnings:")
        lines.extend(f"- {item}" for item in warnings)
    set_readonly_text(frame._verify_text, "\n".join(lines), min_lines=10, max_lines=18)
