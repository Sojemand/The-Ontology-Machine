from __future__ import annotations

from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any, Mapping

from semantic_control_kernel.debug.redaction import BEARER_RE, OAUTH_TOKEN_RE, OPENAI_KEY_RE
from semantic_control_kernel.repository.paths import StatePaths


RAW_INCLUDED_REF_KEYS = {
    "bindings",
    "command_line",
    "cookie",
    "credential",
    "document_payloads",
    "document_text",
    "embeddings",
    "environment",
    "messages",
    "normalized_json",
    "output_text",
    "prompt",
    "raw_exception_traceback",
    "raw_provider_response",
    "source_document_list",
    "stack_trace",
    "stacktrace",
    "stderr",
    "stdout",
    "structured_json",
    "traceback",
}

SECRET_INCLUDED_REF_KEY_FRAGMENTS = (
    "api_key",
    "apikey",
    "authorization",
    "bearer",
    "client_secret",
    "oauth",
    "password",
    "refresh_token",
    "secret",
    "session",
    "token",
    "vault",
)


def included_ref_payload(value: Mapping[str, Any] | str, paths: StatePaths) -> Mapping[str, Any] | str:
    normalized = _normalize_included_ref_value(value, paths)
    if not isinstance(normalized, (Mapping, str)):
        raise ValueError("Support bundle included_refs must contain refs, not raw payload objects.")
    return normalized


def _normalize_included_ref_value(value: Any, paths: StatePaths) -> Any:
    if isinstance(value, str):
        return _normalize_included_ref_string(value, paths)
    if isinstance(value, Mapping):
        normalized: dict[str, Any] = {}
        for key, child in value.items():
            key_text = str(key)
            lowered = key_text.casefold()
            if _is_raw_included_ref_key(lowered):
                raise ValueError(f"Support bundle included_refs cannot inline raw or secret payload field: {key_text}")
            normalized[key_text] = _normalize_included_ref_value(child, paths)
        return normalized
    if isinstance(value, list):
        return [_normalize_included_ref_value(item, paths) for item in value]
    if value is None or isinstance(value, (bool, int, float)):
        return value
    raise ValueError("Support bundle included_refs must contain JSON-safe ref values.")


def _normalize_included_ref_string(value: str, paths: StatePaths) -> str:
    text = value.strip()
    if not text:
        raise ValueError("Support bundle included_refs cannot contain empty refs.")
    if "\r" in text or "\n" in text:
        raise ValueError("Support bundle included_refs cannot contain multi-line payloads.")
    if OPENAI_KEY_RE.search(text) or BEARER_RE.search(text) or OAUTH_TOKEN_RE.search(text):
        raise ValueError("Support bundle included_refs cannot contain secret-like tokens.")
    if _looks_like_windows_absolute_path(text) or text.startswith(("/", "\\\\")):
        try:
            return paths.relative_to_state_root(Path(text))
        except Exception as exc:
            raise ValueError("Support bundle included_refs cannot escape the module state root.") from exc
    if text.startswith("artifact:"):
        _require_safe_relative_ref(text.removeprefix("artifact:"))
        return text
    _require_safe_relative_ref(text)
    return text


def _require_safe_relative_ref(value: str) -> None:
    ref_without_fragment = value.split("#", 1)[0]
    if "://" in ref_without_fragment:
        raise ValueError("Support bundle included_refs cannot contain URL payload refs.")
    for candidate in (PurePosixPath(ref_without_fragment), PureWindowsPath(ref_without_fragment)):
        if candidate.is_absolute() or ".." in candidate.parts:
            raise ValueError("Support bundle included_refs must be relative refs without parent traversal.")


def _looks_like_windows_absolute_path(value: str) -> bool:
    return len(value) >= 3 and value[1] == ":" and value[2] in {"\\", "/"} and value[0].isalpha()


def _is_raw_included_ref_key(lowered: str) -> bool:
    if lowered.endswith("_ref") or lowered.endswith("_refs") or lowered in {"artifact_path", "artifact_paths", "object_ref", "support_bundle_path"}:
        return False
    if lowered in RAW_INCLUDED_REF_KEYS:
        return True
    return any(fragment in lowered for fragment in SECRET_INCLUDED_REF_KEY_FRAGMENTS)
