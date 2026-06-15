"""Host actions used by the Kernel LLM function port."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any
from uuid import uuid4

from .. import credentials
from ..bootstrap import ORCHESTRATOR_ROOT, resolve_module_runtime
from ..bootstrap.exceptions import ModuleRegistryError
from ..integrations import adapter as module_adapter
from ..integrations.types import ModuleContractError
from ..state import load_runtime_settings

PROFILE_NAME = "semantic_control_kernel_llm"
_SECRET_PATTERNS = (
    re.compile(r"\bsk-[A-Za-z0-9_-]+\b"),
    re.compile(r"\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9._-]+\.[A-Za-z0-9._-]+\b"),
)


def runtime_profile_action(*, root: Path = ORCHESTRATOR_ROOT) -> dict:
    state_dir = Path(root) / "state"
    runtime_settings = load_runtime_settings(state_dir)
    profile, diagnostics = _runtime_profile(state_dir, runtime_settings)
    return {
        "status": "ok",
        "output_refs": {"runtime_settings": {PROFILE_NAME: profile}},
        "diagnostics": diagnostics,
    }


def generate_action(command: dict[str, Any], *, root: Path = ORCHESTRATOR_ROOT) -> dict:
    state_dir = Path(root) / "state"
    request = command.get("llm_provider_request")
    if not isinstance(request, dict):
        return _ok_llm_response(_failure_response("invalid_request", "llm_provider_request is missing."))
    runtime_settings = load_runtime_settings(state_dir)
    interpreter_settings = runtime_settings.runtime_settings_for("interpreter") or {}
    context = _credential_context(state_dir)
    model = str(interpreter_settings.get("model") or request.get("model") or "")
    if context is None or not context.ready:
        message = getattr(context, "message", "") if context is not None else "Runtime credentials are unavailable."
        return _ok_llm_response(_failure_response("credentials_missing", message, model=model))
    try:
        spec = resolve_module_runtime("interpreter", required_actions=("generate_llm",))
        response = module_adapter.invoke_contract(
            spec,
            _interpreter_payload(request, interpreter_settings),
            timeout=_timeout_for(request),
            env_overlay=context.env_overlay,
        )
    except (ModuleRegistryError, ModuleContractError, OSError, TimeoutError) as exc:
        return _ok_llm_response(_failure_response("host_capability_missing", str(exc), model=model))
    if response.get("status") != "ok":
        return _ok_llm_response(_failure_response("provider_error", str(response.get("error") or response.get("reason") or "Interpreter LLM call failed."), model=model))
    output_refs = response.get("output_refs")
    llm_response = output_refs.get("llm_response") if isinstance(output_refs, dict) else None
    if not isinstance(llm_response, dict):
        return _ok_llm_response(_failure_response("provider_error", "Interpreter LLM call did not return llm_response.", model=model))
    return {"status": "ok", "output_refs": {"llm_response": dict(llm_response)}}


def _runtime_profile(state_dir: Path, runtime_settings) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    interpreter_settings = runtime_settings.runtime_settings_for("interpreter") or {}
    provider = runtime_settings.provider_settings_for("interpreter")
    diagnostics: list[dict[str, Any]] = []
    context = _credential_context(state_dir)
    host_capability_available = True
    try:
        resolve_module_runtime("interpreter", required_actions=("generate_llm",))
    except ModuleRegistryError as exc:
        host_capability_available = False
        diagnostics.append({"code": "interpreter_generate_llm_unavailable", "summary": str(exc)})
    if context is None:
        diagnostics.append({"code": "credentials_unavailable", "summary": "Interpreter credentials could not be resolved."})
    elif not context.ready:
        diagnostics.append({"code": "credentials_not_ready", "summary": context.message, "block_reasons": list(context.block_reasons)})
    return {
        "model": str(interpreter_settings.get("model") or ""),
        "max_output_tokens": int(interpreter_settings.get("max_output_tokens") or 1),
        "provider_family": provider.normalized_provider_family() if provider is not None else "",
        "credentials_available": bool(context is not None and context.ready),
        "host_capability_available": host_capability_available,
        "auth_mode": str(getattr(context, "auth_mode", "")),
        "credential_source": str(getattr(context, "source", "")),
    }, diagnostics


def _credential_context(state_dir: Path):
    try:
        return credentials.resolve_runtime_credentials(state_dir, "interpreter")
    except Exception:
        return None


def _interpreter_payload(request: dict[str, Any], runtime_settings: dict[str, Any]) -> dict[str, Any]:
    payload = {
        "action": "generate_llm",
        "runtime_settings": dict(runtime_settings),
        "messages": list(request.get("messages") or []),
        "max_output_tokens": int(request.get("max_output_tokens") or runtime_settings.get("max_output_tokens") or 1),
    }
    if isinstance(request.get("target_schema"), dict):
        payload["target_schema"] = dict(request["target_schema"])
    return payload


def _timeout_for(request: dict[str, Any]) -> int:
    value = request.get("timeout_seconds")
    if isinstance(value, int) and value > 0:
        return min(value + 30, 7200)
    return 7200


def _ok_llm_response(llm_response: dict[str, Any]) -> dict:
    return {"status": "ok", "output_refs": {"llm_response": llm_response}}


def _failure_response(status: str, message: str, *, model: str = "") -> dict[str, Any]:
    return {
        "schema_version": "kernel.llm_provider_response.v1",
        "provider": "orchestrator",
        "model": model,
        "response_id": f"{status}_{uuid4().hex[:12]}",
        "status": status,
        "output_text": "",
        "raw_provider_response_ref": {"error_code": status},
        "usage": {},
        "finish_reason": None,
        "error_code": status,
        "error_message": _safe_message(message or status),
    }


def _safe_message(message: str) -> str:
    text = str(message or "")
    for pattern in _SECRET_PATTERNS:
        text = pattern.sub("[REDACTED]", text)
    return text[:500]


__all__ = ["generate_action", "runtime_profile_action"]
