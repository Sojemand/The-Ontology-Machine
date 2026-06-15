"""HTTP provider calls for embedding APIs."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

from .provider_env import request_headers, resolved_base_url, resolved_provider_family


def get_embeddings(
    texts: list[str],
    model: str,
    api_key: str | None = None,
    *,
    base_url: str | None = None,
    provider_family: str | None = None,
) -> list[list[float]]:
    model_name = str(model or "").strip()
    if not model_name:
        raise ValueError("runtime_settings.model fehlt oder ist ungueltig.")
    family = str(provider_family or resolved_provider_family(base_url=base_url)).strip().lower() or "openai_chat"
    if family == "google_gemini":
        return _google_embeddings(texts, model_name, api_key=api_key, base_url=base_url)
    request = urllib.request.Request(
        f"{resolved_base_url(base_url)}/embeddings",
        data=json.dumps({"model": model_name, "input": texts}).encode(),
        headers=request_headers(api_key, provider_family=family),
    )
    return _sorted_embeddings(_read_json(request, timeout=60))


def check_api_available(
    api_key: str | None,
    *,
    model: str,
    base_url: str | None = None,
    provider_family: str | None = None,
) -> tuple[bool, str]:
    model_name = str(model or "").strip()
    if not model_name:
        raise ValueError("runtime_settings.model fehlt oder ist ungueltig.")
    family = str(provider_family or resolved_provider_family(base_url=base_url)).strip().lower() or "openai_chat"
    request = urllib.request.Request(
        f"{resolved_base_url(base_url)}/models",
        headers=request_headers(api_key, provider_family=family),
        method="GET",
    )
    try:
        data = _read_json(request, timeout=5)
        models = _model_ids(data, provider_family=family)
        if model_name not in models:
            return True, f"Verbunden - Modell {model_name} nicht in /models gelistet"
        return True, f"Verbunden - Modell: {model_name}"
    except urllib.error.HTTPError as exc:
        return False, f"HTTP {exc.code}"
    except urllib.error.URLError:
        return False, "Provider-API nicht erreichbar"
    except Exception as exc:  # pragma: no cover - defensive provider surface
        return False, f"Fehler: {exc}"


def _read_json(request: urllib.request.Request, *, timeout: int) -> dict[str, Any]:
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read())


def _sorted_embeddings(result: dict[str, Any]) -> list[list[float]]:
    embeddings = sorted(result["data"], key=lambda item: item["index"])
    return [item["embedding"] for item in embeddings]


def _model_ids(data: dict[str, Any], *, provider_family: str) -> list[str]:
    if provider_family == "google_gemini":
        return [
            str(item.get("name", ""))[7:] if str(item.get("name", "")).startswith("models/") else str(item.get("name", ""))
            for item in data.get("models", [])
            if isinstance(item, dict)
        ]
    return [str(item.get("id", "")) for item in data.get("data", []) if isinstance(item, dict)]


def _google_embeddings(
    texts: list[str],
    model_name: str,
    *,
    api_key: str | None,
    base_url: str | None,
) -> list[list[float]]:
    resolved_model = model_name if model_name.startswith("models/") else f"models/{model_name}"
    vectors: list[list[float]] = []
    for text in texts:
        request = urllib.request.Request(
            f"{resolved_base_url(base_url)}/{resolved_model}:embedContent",
            data=json.dumps({"model": resolved_model, "content": {"parts": [{"text": text}]}}).encode(),
            headers=request_headers(api_key, provider_family="google_gemini"),
        )
        payload = _read_json(request, timeout=60)
        embedding = payload.get("embedding", {})
        values = embedding.get("values", []) if isinstance(embedding, dict) else []
        if not isinstance(values, list):
            raise RuntimeError("Google Gemini Embeddings API lieferte keine gueltigen Vektoren.")
        vectors.append([float(value) for value in values])
    return vectors
