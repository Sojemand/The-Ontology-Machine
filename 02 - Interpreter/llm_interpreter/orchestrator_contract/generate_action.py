"""Generic orchestrator-owned LLM generation action."""
from __future__ import annotations

from typing import Any
from uuid import uuid4

from ..profile_policy import payload_profile
from ..providers import ProviderError, RateLimitError
from ..providers.base import sanitize_error_text
from .workflow import error_response, _build_effective_config


def generate_llm(
    payload: dict,
    *,
    load_dotenv_fn,
    load_config_fn,
    parse_generate_llm_command_fn,
    create_provider_fn,
) -> dict:
    try:
        command = parse_generate_llm_command_fn(payload)
    except ValueError as exc:
        return error_response(str(exc))
    load_dotenv_fn()
    config = _build_effective_config(load_config_fn(), command.runtime_settings)
    config.interpreter_profile = payload_profile(payload)
    try:
        provider = create_provider_fn(
            config.model,
            timeout=config.timeout_seconds,
            base_url=config.api_base_url,
        )
        output_text = provider.generate(
            [dict(item) for item in command.messages],
            command.target_schema,
            command.max_output_tokens,
            config.api_thinking_effort,
        )
    except RateLimitError as exc:
        return _ok_response(_failure_payload("rate_limited", config.model, exc, retry_after=exc.retry_after))
    except ProviderError as exc:
        return _ok_response(_failure_payload(_provider_error_code(exc), config.model, exc))
    except Exception as exc:  # pragma: no cover - defensive owner boundary conversion
        return _ok_response(_failure_payload("provider_error", config.model, exc))
    return _ok_response(
        {
            "schema_version": "kernel.llm_provider_response.v1",
            "provider": str(getattr(provider, "provider_name", "interpreter_provider")),
            "model": str(getattr(provider, "_last_model", "") or config.model),
            "response_id": str(getattr(provider, "_last_response_id", "") or f"interpreter_generate_{uuid4().hex[:12]}"),
            "status": "complete",
            "output_text": output_text,
            "raw_provider_response_ref": {},
            "usage": _usage(provider),
            "finish_reason": "stop",
        }
    )


def _ok_response(llm_response: dict[str, Any]) -> dict:
    return {"status": "ok", "output_refs": {"llm_response": llm_response}}


def _usage(provider: object) -> dict[str, Any]:
    usage = getattr(provider, "_last_usage", {})
    return dict(usage) if isinstance(usage, dict) else {}


def _provider_error_code(exc: Exception) -> str:
    text = sanitize_error_text(str(exc)).casefold()
    auth_markers = ("vision_provider_api_key", "vision_provider_auth_mode", "vision_provider_oauth_access_token")
    if any(marker in text for marker in auth_markers) or "nicht gesetzt" in text:
        return "credentials_missing"
    return "provider_error"


def _failure_payload(status: str, model: str, exc: Exception, *, retry_after: float | None = None) -> dict[str, Any]:
    raw_ref: dict[str, Any] = {"error_code": status}
    if retry_after is not None:
        raw_ref["retry_after"] = retry_after
    return {
        "schema_version": "kernel.llm_provider_response.v1",
        "provider": "interpreter_provider",
        "model": model,
        "response_id": f"{status}_{uuid4().hex[:12]}",
        "status": status,
        "output_text": "",
        "raw_provider_response_ref": raw_ref,
        "usage": {},
        "finish_reason": None,
        "error_code": status,
        "error_message": sanitize_error_text(str(exc)),
    }


__all__ = ["generate_llm"]
