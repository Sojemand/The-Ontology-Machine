"""Provider boundary for orchestrator model catalog refreshes."""

from __future__ import annotations

import json
import urllib.parse
import urllib.error
import urllib.request
from typing import Any

from ..models import ProviderEndpointSettings, provider_definition


_ANTHROPIC_VERSION = "2023-06-01"

def list_model_ids(
    *,
    provider_settings: ProviderEndpointSettings,
    api_key: str | None = None,
    timeout: int = 15,
) -> tuple[str, ...]:
    strategy = provider_definition(provider_settings.normalized_provider_id()).model_catalog_strategy
    if strategy == "anthropic":
        return _list_anthropic_models(provider_settings.normalized_base_url(), api_key=api_key, timeout=timeout)
    if strategy == "google":
        return _list_google_models(provider_settings.normalized_base_url(), api_key=api_key, timeout=timeout)
    return _list_openai_models(provider_settings.normalized_base_url(), api_key=api_key, timeout=timeout)


def _list_openai_models(base_url: str, *, api_key: str | None, timeout: int) -> tuple[str, ...]:
    url = f"{base_url}/models"
    if not url.startswith(("http://", "https://")):
        raise RuntimeError("Provider base URL for the model catalog is invalid.")
    key = str(api_key or "").strip()
    headers = {}
    if key:
        headers["Authorization"] = f"Bearer {key}"
    request = urllib.request.Request(
        url,
        headers=headers,
        method="GET",
    )
    payload = _read_json(request, timeout=timeout)
    return _collect_model_ids(payload.get("data", []))


def _list_anthropic_models(base_url: str, *, api_key: str | None, timeout: int) -> tuple[str, ...]:
    key = str(api_key or "").strip()
    if not key:
        raise RuntimeError("Anthropic provider requires an API key for the model catalog.")
    request = urllib.request.Request(
        f"{base_url}/models",
        headers={
            "x-api-key": key,
            "anthropic-version": _ANTHROPIC_VERSION,
        },
        method="GET",
    )
    payload = _read_json(request, timeout=timeout)
    return _collect_model_ids(payload.get("data", []))


def _list_google_models(base_url: str, *, api_key: str | None, timeout: int) -> tuple[str, ...]:
    key = str(api_key or "").strip()
    if not key:
        raise RuntimeError("Google Gemini provider requires an API key for the model catalog.")
    models: list[str] = []
    seen: set[str] = set()
    page_token = ""
    while True:
        query = {"key": key}
        if page_token:
            query["pageToken"] = page_token
        request = urllib.request.Request(
            f"{base_url}/models?{urllib.parse.urlencode(query)}",
            method="GET",
        )
        payload = _read_json(request, timeout=timeout)
        for model in _collect_model_ids(payload.get("models", []), key_name="name"):
            normalized = model[7:] if model.startswith("models/") else model
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            models.append(normalized)
        page_token = str(payload.get("nextPageToken") or "").strip()
        if not page_token:
            return tuple(models)


def _collect_model_ids(raw_items: Any, *, key_name: str = "id") -> tuple[str, ...]:
    if not isinstance(raw_items, list):
        raise RuntimeError("Provider /models returned no valid data array.")
    models: list[str] = []
    seen: set[str] = set()
    for item in raw_items:
        if not isinstance(item, dict):
            continue
        model = str(item.get(key_name) or "").strip()
        if not model or model in seen:
            continue
        seen.add(model)
        models.append(model)
    return tuple(models)


def list_openai_model_ids(api_key: str, *, timeout: int = 15) -> tuple[str, ...]:
    return list_model_ids(
        provider_settings=ProviderEndpointSettings(provider_id="openai", base_url="https://api.openai.com/v1"),
        api_key=api_key,
        timeout=timeout,
    )


def _read_json(request: urllib.request.Request, *, timeout: int) -> dict[str, Any]:
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read())
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"Provider /models failed (HTTP {exc.code}): {detail[:200]}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Provider /models is not reachable: {exc.reason}") from exc
    except Exception as exc:  # pragma: no cover - defensive adapter guard
        raise RuntimeError(f"Provider /models could not be read: {exc}") from exc
