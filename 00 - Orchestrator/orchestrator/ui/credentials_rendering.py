"""Credential-specific rendering helpers for the Orchestrator UI."""

from __future__ import annotations

from ..credentials import CredentialsState, ResolvedCredentialProfile
from . import theme


def apply_credentials_view(app) -> None:
    state = getattr(app, "_credentials_state", CredentialsState())
    profile = getattr(app, "_credentials_profile", None)
    if profile is None:
        return
    _apply_effective_source_labels(app, profile)
    attention_messages = [
        profile.target_messages.get(target, "")
        for target in ("optimizer_ocr", "embeddings")
        if not profile.target_readiness.get(target, False)
    ]
    app._credentials_notice_label.configure(
        text=" ".join(message for message in attention_messages if message),
        text_color=theme.COLOR_WARNING if attention_messages else theme.COLOR_MUTED,
    )
    for target, widgets in app._credential_widgets.items():
        saved = profile.target_presence.get(target, False)
        widgets["presence"].configure(
            text="Saved for selected provider" if saved else "No key for selected provider",
            text_color=theme.COLOR_SUCCESS if saved else theme.COLOR_MUTED,
        )
        widgets["source"].configure(text=f"Active source: {profile.target_sources.get(target, '-')}")
        widgets["detail"].configure(text=profile.target_messages.get(target, ""))
        widgets["entry"].configure(state="normal")
        widgets["save"].configure(state="normal")
        widgets["delete"].configure(state="normal")
    connected = profile.oauth_session.status == "connected"
    errored = profile.oauth_session.status == "error"
    app._oauth_status_label.configure(
        text=f"Status: {'Connected' if connected else 'Error' if errored else 'Not connected'}",
        text_color=theme.COLOR_SUCCESS if connected else theme.COLOR_ERROR if errored else theme.COLOR_MUTED,
    )
    app._oauth_account_label.configure(text=profile.oauth_session.account_label or "No OAuth account stored")
    app._oauth_message_label.configure(text=profile.oauth_session.status_message)
    app._oauth_login_btn.configure(state="disabled" if connected else "normal")
    app._oauth_logout_btn.configure(state="normal" if connected or errored else "disabled")
    for capability in profile.capabilities:
        widgets = app._capability_widgets.get((capability.module_key, capability.operation))
        if widgets is None:
            continue
        widgets["status"].configure(text=_capability_text(capability), text_color=_capability_color(capability))
        widgets["detail"].configure(text=_capability_detail(capability))


def _apply_effective_source_labels(app, profile) -> None:
    oauth_connected = profile.oauth_session.status == "connected"
    provider_runtime_configured = any(
        "runtime_settings.json" in str(profile.target_sources.get(target, "") or "")
        for target in ("llm_shared", "optimizer_ocr")
    )
    app._credentials_mode_label.configure(
        text="OpenAI OAuth active" if oauth_connected else "Provider-configured" if provider_runtime_configured else "Shared API key fallback",
        text_color=theme.COLOR_SUCCESS if oauth_connected else theme.COLOR_MUTED,
    )
    app._credentials_mode_detail_label.configure(
        text=(
            "Active OAuth session available: Interpreter, Normalizer, and OpenAI Optimizer OCR use ephemeral OAuth runtime credentials."
            if oauth_connected
            else (
                "Interpreter, Normalizer, and Optimizer OCR use the providers configured in runtime_settings.json. Depending on the provider, an API key remains optional or required."
                if provider_runtime_configured
                else "No active OAuth session: Interpreter and Normalizer use the shared LLM API key; Optimizer OCR remains a separate credential target."
            )
        )
    )


def _capability_text(capability) -> str:
    if capability.ready:
        return "Ready"
    if capability.warning_only:
        return "Warning"
    if capability.supported:
        return "Not ready"
    return "Blocked"


def _capability_color(capability):
    if capability.ready:
        return theme.COLOR_SUCCESS
    if capability.warning_only:
        return theme.COLOR_WARNING
    if capability.supported:
        return theme.COLOR_WARNING
    return theme.COLOR_ERROR


def _capability_detail(capability) -> str:
    reasons = "; ".join(capability.block_reasons)
    if reasons:
        return f"{capability.source} | {reasons}"
    return capability.source
