"""Support-monitor dashboard for the MCP Server surface."""
from __future__ import annotations

import customtkinter as ctk

from . import theme
from .text_widgets import create_readonly_text


def render(parent, surface, *, app):
    frame = ctk.CTkFrame(parent)
    frame.grid_columnconfigure(0, weight=1)
    value = surface.value if isinstance(surface.value, dict) else {}
    incidents = value.get("recent_incidents") if isinstance(value.get("recent_incidents"), list) else []
    summary = (
        f"Active incidents: {value.get('active_incident_count', 0)} | "
        f"Events: {value.get('event_count', 0)} | "
        f"Dismissed: {value.get('dismissed_count', 0)}"
    )
    create_readonly_text(frame, text=summary, font=theme.font_small(), text_color=theme.COLOR_MUTED, min_lines=1, max_lines=2).grid(
        row=0, column=0, sticky="we"
    )
    state_root = str(value.get("support_state_root") or "").strip()
    if state_root:
        create_readonly_text(frame, text=state_root, font=theme.font_small(), text_color=theme.COLOR_MUTED, min_lines=1, max_lines=2).grid(
            row=1, column=0, pady=(0, theme.PADDING_SMALL), sticky="we"
        )
    if not incidents:
        create_readonly_text(frame, text="No active support incidents.", min_lines=1, max_lines=1).grid(
            row=2, column=0, pady=(theme.PADDING_SMALL, 0), sticky="we"
        )
        return frame
    row = 2
    for incident in incidents:
        if not isinstance(incident, dict):
            continue
        _render_incident(frame, surface, app=app, incident=incident, row=row)
        row += 1
    return frame


def _render_incident(parent, surface, *, app, incident: dict, row: int) -> None:
    card = ctk.CTkFrame(parent)
    card.grid(row=row, column=0, pady=(theme.PADDING_SMALL, 0), sticky="we")
    card.grid_columnconfigure(0, weight=1)
    incident_id = str(incident.get("incident_id") or "").strip()
    module_key = str(incident.get("module_key") or "").strip()
    action = str(incident.get("action") or "").strip()
    severity = str(incident.get("severity") or "error").strip()
    title = f"{severity.upper()} | {module_key}.{action}".strip(".")
    create_readonly_text(card, text=title, font=theme.font_header(), min_lines=1, max_lines=2).grid(
        row=0, column=0, padx=theme.PADDING, pady=(theme.PADDING, 2), sticky="we"
    )
    message = str(incident.get("message") or "").strip() or incident_id
    meta = (
        f"Incident {incident_id} | events: {incident.get('event_count', 0)} | "
        f"last seen: {incident.get('last_seen', '')}"
    )
    create_readonly_text(card, text=message, min_lines=1, max_lines=3).grid(
        row=1, column=0, padx=theme.PADDING, pady=(0, 2), sticky="we"
    )
    create_readonly_text(card, text=meta, font=theme.font_small(), text_color=theme.COLOR_MUTED, min_lines=1, max_lines=2).grid(
        row=2, column=0, padx=theme.PADDING, pady=(0, theme.PADDING_SMALL), sticky="we"
    )
    actions = ctk.CTkFrame(card, fg_color=card.cget("fg_color"))
    actions.grid(row=3, column=0, padx=theme.PADDING, pady=(0, theme.PADDING), sticky="w")
    button_state = getattr(app, "action_button_state", lambda _sid: "normal")(surface.surface_id)
    for index, link in enumerate(_incident_actions(incident_id)):
        ctk.CTkButton(
            actions,
            text=str(link["label"]),
            width=120,
            state=button_state,
            command=lambda sid=surface.surface_id, action_link=link: app.run_surface_action(sid, action_link),
        ).grid(row=0, column=index, padx=(0, theme.PADDING_SMALL), sticky="w")


def _incident_actions(incident_id: str) -> tuple[dict, ...]:
    contract_module = "mcp_server.edit_contract"
    return (
        {
            "label": "Assess",
            "action": "support_incident_workflow",
            "contract_module": contract_module,
            "fixed_payload": {
                "workflow_action": "assess",
                "incident_id": incident_id,
                "classification": "unknown",
                "confidence": "low",
            },
        },
        {
            "label": "Dismiss",
            "action": "support_incident_workflow",
            "contract_module": contract_module,
            "fixed_payload": {
                "workflow_action": "dismiss",
                "incident_id": incident_id,
                "reason": "dismissed_from_edit_suite",
            },
        },
    )
