"""Side-effect-free enrichment and estimation for interpreter outputs."""
from __future__ import annotations

import copy
import math
import re
from datetime import datetime, timezone
from typing import Any

from ..models.types import COST_PER_1K_TOKENS
from ..prompts.types import OUTPUT_TEMPLATE
from ..profile_policy import request_profile


def enrich_output(llm_result: dict[str, Any], request: dict[str, Any], provider_name: str, model: str) -> dict[str, Any]:
    llm_result.pop("relations", None)
    _deep_fill_defaults(llm_result, copy.deepcopy(OUTPUT_TEMPLATE))
    source = request.get("source", {}) or {}
    request_context = request.get("context", {}) or {}
    llm_result["schema_version"] = "1.0"
    processing = llm_result["processing"]
    processing["interpreter_profile"] = request_profile(request)
    processing["processed_at"] = datetime.now(timezone.utc).isoformat()
    processing["model"] = model
    processing["provider"] = provider_name
    processing["vision_used"] = True
    llm_result["source"] = {
        "file_name": str(source.get("file_name", "")),
        "file_path": str(source.get("file_path", "")),
        "file_ext": str(source.get("file_ext", source.get("format", ""))),
        "size_bytes": source.get("size_bytes", 0) or 0,
        "content_hash": str(source.get("content_hash", "")),
        "created_at": source.get("created_at"),
        "modified_at": source.get("modified_at"),
    }
    classification = llm_result["classification"]
    classification["is_scan"] = bool(source.get("is_scan", classification.get("is_scan", True)))
    page_count = request_context.get("document_page_count", source.get("page_count", classification.get("page_count", 1)))
    classification["page_count"] = int(page_count or 1)
    _merge_request_context(llm_result, request)
    normalize_model_free_text(llm_result)
    return llm_result


def estimate_cost(model: str, usage: dict[str, Any]) -> float | None:
    if not isinstance(usage, dict):
        return None
    input_tokens = _coerce_usage_token_count(usage.get("input_tokens", usage.get("prompt_tokens", 0)))
    output_tokens = _coerce_usage_token_count(usage.get("output_tokens", usage.get("completion_tokens", 0)))
    costs = COST_PER_1K_TOKENS.get(model)
    if not costs or not (input_tokens or output_tokens):
        return None
    return round(input_tokens / 1000 * costs[0] + output_tokens / 1000 * costs[1], 6)


def estimate_message_tokens(
    messages: list[dict[str, Any]],
    model: str,
    max_output_tokens: int,
    *,
    label: str,
) -> dict[str, Any]:
    total_chars = 0
    image_count = 0
    for message in messages:
        content = message.get("content")
        if isinstance(content, str):
            total_chars += len(content)
            continue
        for block in content or []:
            if block.get("type") == "text":
                total_chars += len(block.get("text", ""))
            elif block.get("type") == "input_image":
                image_count += 1
    est_input_tokens = total_chars // 3 + image_count * 850
    costs = COST_PER_1K_TOKENS.get(model)
    est_cost = None
    if costs:
        est_cost = round(est_input_tokens / 1000 * costs[0] + max_output_tokens / 1000 * costs[1], 4)
    return {
        "file": label,
        "mode": "vision",
        "est_input_tokens": est_input_tokens,
        "est_output_tokens": max_output_tokens,
        "est_total_tokens": est_input_tokens + max_output_tokens,
        "image_count": image_count,
        "model": model,
        "est_cost_usd": est_cost,
    }


def normalize_text(text: Any) -> str:
    if text is None:
        return ""
    normalized = str(text).replace("\r\n", "\n").replace("\r", "\n")
    lines = [re.sub(r"\s+", " ", line).strip() for line in normalized.split("\n")]
    return "\n".join(line for line in lines if line)


def normalize_model_free_text(llm_result: dict[str, Any]) -> None:
    content = llm_result.setdefault("content", {})
    content["free_text"] = normalize_text(content.get("free_text")) or None


def _deep_fill_defaults(target: dict[str, Any], defaults: dict[str, Any]) -> dict[str, Any]:
    for key, default_value in defaults.items():
        if key not in target:
            target[key] = copy.deepcopy(default_value)
        elif isinstance(default_value, dict) and isinstance(target.get(key), dict):
            _deep_fill_defaults(target[key], default_value)
    return target


def _merge_request_context(llm_result: dict[str, Any], request: dict[str, Any]) -> None:
    context = llm_result.setdefault("context", {})
    if not isinstance(context, dict):
        context = {}
        llm_result["context"] = context
    request_context = request.get("context", {}) if isinstance(request.get("context", {}), dict) else {}
    for key, value in request_context.items():
        if (key not in context or not _has_value(context.get(key))) and _has_value(value):
            context[key] = value
    for key in [key for key, value in context.items() if value in (None, "", [])]:
        del context[key]


def _coerce_usage_token_count(value: Any) -> int:
    if value is None or isinstance(value, bool):
        return 0
    if isinstance(value, int):
        return max(value, 0)
    if isinstance(value, float):
        return max(int(value), 0) if math.isfinite(value) else 0
    text = str(value).strip()
    if not text:
        return 0
    try:
        number = float(text)
    except ValueError:
        return 0
    return max(int(number), 0) if math.isfinite(number) else 0


def _has_value(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, dict)):
        return bool(value)
    return True
